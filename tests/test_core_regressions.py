"""`fundrives.lanzou.core` 的回归测试。

这些用例对应 codex 审计 farfarfun/todo-list#671 中核实为真实缺陷的几处行为，
每一条都做过反向验证（把实现改回修复前的写法，用例必须失败）：

1. 导入 `fundrives.lanzou.core` 不得发起任何网络请求
   （修复前模块顶层有 `executors.submit(check_domains)`）。
2. `check_domains()` 不得边遍历边 `remove` 候选域名（会跳过元素），
   也不得就地修改模块级 `available_domains`。
3. 所有域名都不可用时抛领域异常 `NoAvailableDomainError`，而不是裸 `Exception`。
4. `get_file_list()` / `get_folder_info_by_url()` 在响应为空或为 `None` 时
   不得无限重试同一页。
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from unittest import mock

import pytest

from fundrives.lanzou import core
from fundrives.lanzou.errors import LanZouError, NoAvailableDomainError

# ---------------------------------------------------------------- 导入期无副作用


def test_importing_core_makes_no_network_call():
    """`import fundrives.lanzou.core` 必须在完全禁网的进程里也能成功。

    修复前模块顶层有 `executors.submit(check_domains)`，导入即对 14 个蓝奏云
    域名发起真实 HTTP HEAD 请求。这里在子进程里把 `socket.socket` 换成直接抛
    异常的桩，再导入模块：只要导入期碰了网络，就会抛出 AssertionError。
    """
    script = textwrap.dedent(
        """
        import socket
        import sys

        class _Blocked(socket.socket):
            def __init__(self, *args, **kwargs):
                raise AssertionError("import 期间不允许创建 socket")

        socket.socket = _Blocked
        socket.create_connection = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("import 期间不允许建立连接")
        )

        import fundrives.lanzou.core as core

        assert core.LanZouCloud is not None
        print("OK")
        """
    )
    proc = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=120
    )
    assert proc.returncode == 0, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert "OK" in proc.stdout


# ------------------------------------------------------------------ check_domains


def _fake_head(status_map: dict[str, int]):
    """构造一个按域名返回不同状态码的 `requests.head` 替身。"""

    def _head(url, **kwargs):
        for domain, status in status_map.items():
            if domain in url:
                return mock.Mock(status_code=status)
        raise AssertionError(f"未预期的请求 url={url}")

    return _head


def test_check_domains_returns_every_alive_domain():
    """所有域名都返回 200 时，必须返回全部候选域名，一个都不能漏。"""
    candidates = list(core.available_domains)
    status_map = {d: 200 for d in candidates}

    with mock.patch.object(core.requests, "head", side_effect=_fake_head(status_map)):
        alive = core.check_domains(timeout=0.5)

    assert alive == candidates


def test_check_domains_does_not_skip_candidates_when_some_fail():
    """隔一个失败一个时，返回的必须正好是成功的那一半。

    修复前的实现是 `for domain in available_domains: available_domains.remove(domain)`，
    边遍历边删会跳过元素，结果既漏判可用域名、也漏删不可用域名。
    """
    candidates = list(core.available_domains)
    status_map = {d: (200 if i % 2 == 0 else 503) for i, d in enumerate(candidates)}
    expected = [d for i, d in enumerate(candidates) if i % 2 == 0]

    with mock.patch.object(core.requests, "head", side_effect=_fake_head(status_map)):
        alive = core.check_domains(timeout=0.5)

    assert alive == expected
    # 候选里一半不可用，但模块级列表不能被就地改掉
    assert core.available_domains == candidates


def test_check_domains_raises_domain_error_when_nothing_alive():
    """全部域名不可用时抛 `NoAvailableDomainError`，而不是裸 `Exception`。"""
    candidates = list(core.available_domains)
    status_map = {d: 503 for d in candidates}

    with mock.patch.object(core.requests, "head", side_effect=_fake_head(status_map)):
        with pytest.raises(NoAvailableDomainError) as exc_info:
            core.check_domains(timeout=0.5)

    assert isinstance(exc_info.value, LanZouError)
    assert str(len(candidates)) in str(exc_info.value)
    assert core.available_domains == candidates


def test_check_domains_treats_network_exception_as_unavailable():
    """单个域名抛网络异常时跳过它，不应让整个探测失败。"""
    candidates = list(core.available_domains)
    alive_domain = candidates[0]

    def _head(url, **kwargs):
        if alive_domain in url:
            return mock.Mock(status_code=200)
        raise core.requests.ConnectionError("boom")

    with mock.patch.object(core.requests, "head", side_effect=_head):
        alive = core.check_domains(timeout=0.5)

    assert alive == [alive_domain]


def test_refresh_available_domains_updates_module_state():
    """`refresh_available_domains()` 是显式刷新入口，应就地更新模块级列表。"""
    candidates = list(core.available_domains)
    keep = candidates[:2]
    status_map = {d: (200 if d in keep else 503) for d in candidates}

    try:
        with mock.patch.object(
            core.requests, "head", side_effect=_fake_head(status_map)
        ):
            alive = core.refresh_available_domains(timeout=0.5)
        assert alive == keep
        assert core.available_domains == keep
    finally:
        core.available_domains[:] = candidates


def test_refresh_available_domains_keeps_old_list_on_total_failure():
    """全部不可用时抛异常并保留原列表，不能把 available_domains 清空。"""
    candidates = list(core.available_domains)
    status_map = {d: 503 for d in candidates}

    with mock.patch.object(core.requests, "head", side_effect=_fake_head(status_map)):
        with pytest.raises(NoAvailableDomainError):
            core.refresh_available_domains(timeout=0.5)

    assert core.available_domains == candidates


# ------------------------------------------------------- 不得对同一页无限重试


def test_get_file_list_gives_up_when_network_always_fails():
    """`_post` 一直返回 None（所有域名不可用）时必须退出循环并返回空列表。

    修复前是 `if not resp: continue`，既不计数也不 sleep —— 直接变成占满 CPU
    的死循环，调用方永远不会返回。
    """
    drive = core.LanZouCloud()
    with (
        mock.patch.object(drive, "_post", return_value=None) as mocked_post,
        mock.patch.object(core.time, "sleep", return_value=None),
    ):
        result = drive.get_file_list(-1)

    assert len(result) == 0
    # 有上限：不可能无限次调用
    assert mocked_post.call_count == core._MAX_REFRESH_RETRY + 1


def test_get_file_list_parses_one_page():
    """正常路径：一页数据被解析成 File 条目，下一页返回 info==0 时结束分页。"""
    drive = core.LanZouCloud()
    first_page = mock.Mock()
    first_page.json.return_value = {
        "info": 1,
        "zt": 1,
        "text": [
            {
                "id": "12345",
                "name_all": "demo&amp;file.zip",
                "time": "2026-01-02",
                "size": "1,024 K",
                "downs": "7",
                "onof": "1",
                "is_des": "0",
            }
        ],
    }
    last_page = mock.Mock()
    last_page.json.return_value = {"info": 0, "zt": 1, "text": []}

    with mock.patch.object(drive, "_post", side_effect=[first_page, last_page]):
        result = drive.get_file_list(-1)

    assert len(result) == 1
    item = result[0]
    assert item.id == 12345
    assert item.name == "demo&file.zip"
    assert item.size == "1024 K"
    assert item.downs == 7
    assert item.has_pwd is True
    assert item.has_des is False


def test_get_folder_info_by_url_returns_network_error_on_empty_body():
    """分页接口返回空 body 时必须按网络错误返回，不能对同一页无限重试。

    修复前是 `if not post.text: logger.error(...); continue`。
    """
    drive = core.LanZouCloud()
    html = (
        "<html>'lx':'2', var abcdef = '1700000000'; "
        "var ghijkl = 'abcdefghij0123456789'; 'fid':'99',"
        '<div class="user-title">demo</div></html>'
    )
    first = mock.Mock()
    first.text = html
    empty = mock.Mock()
    empty.text = ""

    with (
        mock.patch.object(core, "is_file_url", return_value=False),
        mock.patch.object(core.requests, "get", return_value=first),
        mock.patch.object(drive, "_post", return_value=empty) as mocked_post,
    ):
        detail = drive.get_folder_info_by_url("https://demo.lanzoub.com/b0d8h93hi")

    assert detail.code == core.LanZouCloud.NETWORK_ERROR
    assert mocked_post.call_count == 1


def test_get_folder_info_by_url_handles_post_returning_none():
    """`_post` 返回 None 时必须返回 NETWORK_ERROR。

    修复前先访问 `post.text` 再判空，这里会抛 AttributeError 冒出调用栈。
    """
    drive = core.LanZouCloud()
    html = (
        "<html>'lx':'2', var abcdef = '1700000000'; "
        "var ghijkl = 'abcdefghij0123456789'; 'fid':'99',"
        '<div class="user-title">demo</div></html>'
    )
    first = mock.Mock()
    first.text = html

    with (
        mock.patch.object(core, "is_file_url", return_value=False),
        mock.patch.object(core.requests, "get", return_value=first),
        mock.patch.object(drive, "_post", return_value=None),
    ):
        detail = drive.get_folder_info_by_url("https://demo.lanzoub.com/b0d8h93hi")

    assert detail.code == core.LanZouCloud.NETWORK_ERROR


# ----------------------------------------------------------- delete 的正常/异常路径


def test_delete_returns_success_when_server_accepts():
    drive = core.LanZouCloud()
    resp = mock.Mock()
    resp.json.return_value = {"zt": 1}

    with mock.patch.object(drive, "_post", return_value=resp) as mocked_post:
        assert drive.delete(123, is_file=True) == core.LanZouCloud.SUCCESS

    sent_data = mocked_post.call_args.args[1]
    assert sent_data == {"task": 6, "file_id": 123}


def test_delete_folder_uses_folder_task():
    drive = core.LanZouCloud()
    resp = mock.Mock()
    resp.json.return_value = {"zt": 1}

    with mock.patch.object(drive, "_post", return_value=resp) as mocked_post:
        assert drive.delete(456, is_file=False) == core.LanZouCloud.SUCCESS

    assert mocked_post.call_args.args[1] == {"task": 3, "folder_id": 456}


def test_delete_returns_network_error_when_post_fails():
    drive = core.LanZouCloud()
    with mock.patch.object(drive, "_post", return_value=None):
        assert drive.delete(123) == core.LanZouCloud.NETWORK_ERROR


def test_delete_returns_failed_when_server_rejects():
    drive = core.LanZouCloud()
    resp = mock.Mock()
    resp.json.return_value = {"zt": 0}

    with mock.patch.object(drive, "_post", return_value=resp):
        assert drive.delete(123) == core.LanZouCloud.FAILED
