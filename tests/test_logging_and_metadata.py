"""日志脱敏与包元信息的回归测试（codex 审计 farfarfun/todo-list#671）。

farlog 基于 loguru，pytest 自带的 `caplog` 抓不到，这里用
`loguru.logger.add(sink)` 自己挂一个 sink 收集日志行。
"""

from __future__ import annotations

import ast
import re
from importlib import metadata
from pathlib import Path
from unittest import mock

import pytest
import requests
from loguru import logger as loguru_logger

import fundrives.lanzou as lanzou_pkg
from fundrives.lanzou import extra
from fundrives.lanzou.parser import parse_sign

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def captured_logs():
    """收集本次测试期间所有 loguru 日志行。"""
    lines: list[str] = []
    sink_id = loguru_logger.add(lines.append, level="TRACE", format="{level}|{message}")
    try:
        yield lines
    finally:
        loguru_logger.remove(sink_id)


# ------------------------------------------------------------------ 日志不得泄露凭据

SIGN_VALUE = "SIGNsecret0123456789abcdefSECRET"


def test_parse_sign_does_not_log_the_sign(captured_logs):
    """`parse_sign` 解析出的 sign 是一次性下载授权凭据，不得写进日志。

    修复前 parser.py 里有两行 `logger.error("~~~~~~~ first " + ...)` /
    `("~~~~~~~ final " + sign)`，把 sign 原文打到 ERROR 级别。
    """
    html = f"<script>'sign':'{SIGN_VALUE}', 'x':1,</script>"

    assert parse_sign(html) == SIGN_VALUE

    joined = "\n".join(captured_logs)
    assert SIGN_VALUE not in joined, f"sign 泄露到日志: {joined!r}"


def test_get_file_info_by_url_does_not_log_sign_or_page_body(captured_logs):
    """无提取码分享页路径上，sign、分享 URL、整页 HTML 都不得进日志。"""
    from fundrives.lanzou import core

    drive = core.LanZouCloud()
    share_url = "https://demo.lanzoub.com/iSECRETshare"
    marker = "TOPSECRETPAGEMARKER"
    first_page = mock.Mock()
    first_page.text = (
        f'<html><!-- {marker} --><iframe class="x" src="/fn?a=1"></iframe>'
        f"<title>demo.zip - 蓝奏云</title></html>"
    )
    frame_page = mock.Mock()
    frame_page.text = f"<script>'sign':'{SIGN_VALUE}', 'x':1,</script>{marker}"

    with (
        mock.patch.object(drive, "_get", side_effect=[first_page, frame_page, None]),
        mock.patch.object(drive, "_post", return_value=None),
    ):
        detail = drive.get_file_info_by_url(share_url)

    assert detail.code == core.LanZouCloud.NETWORK_ERROR
    joined = "\n".join(captured_logs)
    assert SIGN_VALUE not in joined, f"sign 泄露到日志: {joined!r}"
    assert marker not in joined, f"页面正文泄露到日志: {joined!r}"


def test_post_failure_log_does_not_include_request_body(captured_logs):
    """`_post` 重试日志不得带 data —— 登录请求的 body 里就是账号密码。"""
    from fundrives.lanzou import core

    drive = core.LanZouCloud()
    secret = "my-super-secret-password"

    with mock.patch.object(
        drive._session, "post", side_effect=requests.ConnectionError("boom")
    ):
        assert drive._post("https://pan.lanzoub.com/x", {"pwd": secret}) is None

    joined = "\n".join(captured_logs)
    assert secret not in joined, f"请求 body 泄露到日志: {joined!r}"


def test_get_short_url_does_not_log_response_body(captured_logs):
    """短链服务响应正文不得整段写进日志，只记录状态与长度。"""
    body = '{"short": "https://x.cn/a", "secret_quota_token": "RESPONSEBODYSECRET"}'
    resp = mock.Mock(status_code=200, text=body)

    with (
        mock.patch.object(extra, "DWZ_LC_TOKEN", "tok-dwz"),
        mock.patch.object(extra, "ECX_CX_TOKEN", None),
        mock.patch.object(extra.requests, "post", return_value=resp),
    ):
        assert extra.get_short_url("https://example.com/x") == "https://x.cn/a"

    joined = "\n".join(captured_logs)
    assert "RESPONSEBODYSECRET" not in joined, f"响应正文泄露到日志: {joined!r}"


def test_get_short_url_does_not_leak_token_to_unauthenticated_services():
    """dwz.lc 的 Token 不得被带到后面的 tinyurl / gg.gg 请求里。

    修复前 4 个服务共用同一个 `headers` dict，
    `headers["Authorization"] = f"Token {DWZ_LC_TOKEN}"` 会一直残留，
    于是 dwz.lc 的令牌被原样发给了 tinyurl.com 和 gg.gg。
    """
    token = "TOKEN-MUST-NOT-LEAK"
    get_calls: list[dict] = []
    post_calls: list[dict] = []

    def _fake_post(url, **kwargs):
        post_calls.append({"url": url, "headers": kwargs.get("headers", {})})
        if "dwz.lc" in url:
            raise requests.ConnectionError("dwz down")
        return mock.Mock(status_code=200, text="https://gg.gg/abc")

    def _fake_get(url, **kwargs):
        get_calls.append({"url": url, "headers": kwargs.get("headers", {})})
        raise requests.ConnectionError("tinyurl down")

    with (
        mock.patch.object(extra, "DWZ_LC_TOKEN", token),
        mock.patch.object(extra, "ECX_CX_TOKEN", None),
        mock.patch.object(extra.requests, "post", side_effect=_fake_post),
        mock.patch.object(extra.requests, "get", side_effect=_fake_get),
    ):
        assert extra.get_short_url("https://example.com/x") == "https://gg.gg/abc"

    assert get_calls and post_calls
    for call in get_calls:
        assert "Authorization" not in call["headers"], (
            f"Token 泄露给 {call['url']}: {call['headers']}"
        )
    for call in post_calls:
        if "dwz.lc" in call["url"]:
            assert call["headers"]["Authorization"] == f"Token {token}"
        else:
            assert "Authorization" not in call["headers"], (
                f"Token 泄露给 {call['url']}: {call['headers']}"
            )


def test_get_short_url_propagates_unexpected_exception():
    """只兜住网络/解析类失败，不再用 `except Exception` 吞掉编程错误。"""

    class Boom(Exception):
        pass

    with (
        mock.patch.object(extra, "DWZ_LC_TOKEN", None),
        mock.patch.object(extra, "ECX_CX_TOKEN", None),
        mock.patch.object(extra.requests, "get", side_effect=Boom("bug")),
        mock.patch.object(extra.requests, "post", side_effect=Boom("bug")),
    ):
        with pytest.raises(Boom):
            extra.get_short_url("https://example.com/x")


# -------------------------------------------------------------------- 包元信息一致性


PYPROJECT_SRC = (REPO_ROOT / "pyproject.toml").read_text("utf-8")


def _declared_version() -> str:
    """从 pyproject.toml 取 `[project].version`。

    这里没有用 `tomllib`：它是 3.11 才进标准库的，而本包声明
    `requires-python >= 3.10`，测试本身必须能在声明的下限上跑起来。
    """
    match = re.search(r'^version\s*=\s*"([^"]+)"', PYPROJECT_SRC, re.MULTILINE)
    assert match, "pyproject.toml 里找不到顶层 version"
    return match.group(1)


def _declared_dependencies() -> list[str]:
    """从 pyproject.toml 取 `[project].dependencies`。"""
    match = re.search(
        r"^dependencies\s*=\s*(\[.*?\])", PYPROJECT_SRC, re.MULTILINE | re.DOTALL
    )
    assert match, "pyproject.toml 里找不到 dependencies"
    return ast.literal_eval(match.group(1))


def test_package_version_matches_pyproject():
    """`__version__` 必须等于 `pyproject.toml` 里的 `[project].version`。

    这是版本漂移拦截：不是「断言是个非空字符串」，而是逐字符比对唯一来源。
    """
    declared = _declared_version()
    assert lanzou_pkg.__version__ == declared
    assert metadata.version("fundrive-lanzou") == declared


def test_no_hardcoded_version_literal_in_sources():
    """源码里不得再硬编码版本号字面量（原先 `__init__.py` 写死 version = "2.6.8"）。"""
    init_src = (REPO_ROOT / "src/fundrives/lanzou/__init__.py").read_text("utf-8")
    # 只看模块顶层（无缩进）的赋值；except 分支里的 dev 兜底值不算硬编码发布版本
    assert not re.search(r"^version\s*=\s*[\"']\d", init_src, re.MULTILINE)
    assert not re.search(r"^__version__\s*=\s*[\"']\d", init_src, re.MULTILINE)


def test_lanzou_api_version_reported_from_installed_metadata():
    """`version` 报告的是实际安装的 `lanzou-api` 版本，而不是写死的字面量。"""
    assert lanzou_pkg.version == metadata.version("lanzou-api")


def test_lanzou_api_is_a_declared_runtime_dependency():
    """`lanzou-api` 必须出现在运行时依赖里。

    PyPI 上的 1.2.73 没有声明它，导致干净环境下
    `import fundrives.lanzou` 直接 ModuleNotFoundError: No module named 'lanzou'。
    """
    declared = _declared_dependencies()
    assert any(
        d.split(">")[0].split("=")[0].strip() == "lanzou-api" for d in declared
    ), f"dependencies 里缺少 lanzou-api: {declared}"

    requires = metadata.requires("fundrive-lanzou") or []
    assert any(r.startswith("lanzou-api") for r in requires), (
        f"已安装发行包的 Requires-Dist 里缺少 lanzou-api: {requires}"
    )


def test_py_typed_marker_lives_in_the_importable_subpackage():
    """`fundrives` 是 PEP 420 命名空间包，py.typed 必须放在 `fundrives/lanzou/` 下。

    放在 `src/fundrives/` 既不符合 PEP 561（命名空间包本身没有归属者），
    还会与其他 fundrive-* 包装出同一个文件路径。
    """
    assert (REPO_ROOT / "src/fundrives/lanzou/py.typed").is_file()
    assert not (REPO_ROOT / "src/fundrives/py.typed").exists()
    assert not (REPO_ROOT / "src/fundrives/__init__.py").exists()


def test_third_party_notice_records_upstream_license():
    """第三方来源代码必须在仓库里保留上游来源与原始许可（SPEC §12.4）。"""
    notice = (REPO_ROOT / "THIRD_PARTY_NOTICE.md").read_text("utf-8")
    assert "zaxtyson" in notice
    assert "MIT" in notice
    assert "LanZouCloud-API" in notice
    for name in (
        "core.py",
        "parser.py",
        "models.py",
        "types.py",
        "utils.py",
        "extra.py",
    ):
        assert name in notice

    readme = (REPO_ROOT / "README.md").read_text("utf-8")
    assert "THIRD_PARTY_NOTICE.md" in readme
    assert "zaxtyson" in readme


def test_no_print_based_debug_entrypoint_in_library_code():
    """库代码里不得残留 `if __name__ == "__main__":` + print 的调试入口（SPEC §8.1）。"""
    offenders = []
    for path in (REPO_ROOT / "src/fundrives/lanzou").glob("*.py"):
        text = path.read_text("utf-8")
        if '__name__ == "__main__"' in text or re.search(r"^\s*print\(", text, re.M):
            offenders.append(path.name)
    assert offenders == [], f"库代码里仍有调试入口/print: {offenders}"
