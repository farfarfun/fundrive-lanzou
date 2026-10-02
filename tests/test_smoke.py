"""fundrive-lanzou 轻量冒烟测试（smoke tests）。

范围：只确认包能否正常安装 / 导入，以及对外导出的核心驱动类 `LanZouCloud`
在不发起真实网络请求的情况下基本可用。不测试真实登录 / 上传 / 下载等需要真实
蓝奏云账号的业务逻辑。

按 NAMING.md 的约定，本仓库的导入名是共享命名空间 `fundrives`
（`fundrive-alipan` / `fundrive-baidu` / `fundrive-lanzou` / `fundrive-quark`
都发布到同一个 `fundrives` 顶层包下）。本仓库源码没有 import `fundrive` 主包，
所以这里不测试 `fundrive` 的导入，也没有为它新增依赖。

`fundrives.lanzou.__init__` 导出的 `LanZouCloud` 来自运行时依赖 `lanzou-api`
（导入名 `lanzou`）；仓库内 `core.py` 等模块是从同一上游 LanZouCloud-API 派生、
随本包一起分发的实现，来源与原始协议见 `THIRD_PARTY_NOTICE.md`。这两份实现并存
属于待收敛的历史状态（见 farfarfun/todo-list#671），但两者都会被安装到用户环境里，
因此 `tests/test_core_regressions.py` 对 `core.py` 的真实缺陷单独做了回归覆盖。
"""

from __future__ import annotations

import importlib
from unittest import mock

import requests


def test_import_fundrives_namespace():
    """fundrive-lanzou 按 NAMING.md 约定，通过共享命名空间 `fundrives` 导入。"""
    fundrives = importlib.import_module("fundrives")
    assert fundrives is not None


def test_import_fundrives_lanzou_and_public_api():
    """导入 fundrives.lanzou 子包，并确认对外暴露的驱动类/工具函数存在。

    该 import 链路依赖第三方包 `lanzou-api`（见上方模块 docstring 里
    关于依赖修复的说明），这里也间接验证了这个依赖修复是有效的。
    """
    lanzou_pkg = importlib.import_module("fundrives.lanzou")

    assert hasattr(lanzou_pkg, "LanZouCloud")
    assert hasattr(lanzou_pkg, "why_error")
    assert hasattr(lanzou_pkg, "version")
    assert isinstance(lanzou_pkg.version, str) and lanzou_pkg.version


def test_lanzou_cloud_can_be_constructed_without_network():
    """LanZouCloud() 无参构造，只是准备 requests.Session 和一些默认配置，
    不发起任何真实网络请求。"""
    from fundrives.lanzou import LanZouCloud

    drive = LanZouCloud()
    assert isinstance(drive._session, requests.Session)
    assert drive._cookies is None
    assert drive._host_url.startswith("https://")


def test_lanzou_cloud_login_with_mocked_network():
    """login() 内部会依次调用 self._get / self._post 发起真实 HTTP 请求，
    这里 mock 掉这两个方法，避免测试环境真的去连蓝奏云，只验证调用链路
    和返回值解析逻辑不会抛异常、且能按预期返回 SUCCESS。"""
    from fundrives.lanzou import LanZouCloud

    drive = LanZouCloud()

    fake_form_response = mock.Mock()
    fake_form_response.text = '<input type="hidden" name="formhash" value="abc123">'

    fake_login_response = mock.Mock()
    fake_login_response.json.return_value = {"info": "登录成功"}
    fake_login_response.cookies.get_dict.return_value = {"ylogin": "dummy"}

    with (
        mock.patch.object(drive, "_get", return_value=fake_form_response) as mocked_get,
        mock.patch.object(
            drive, "_post", return_value=fake_login_response
        ) as mocked_post,
    ):
        result = drive.login("dummy-user", "dummy-pass")

    assert result == LanZouCloud.SUCCESS
    mocked_get.assert_called_once()
    mocked_post.assert_called_once()


def test_lanzou_cloud_login_with_mocked_network_error():
    """_get 返回空（模拟网络不可达）时，login() 应该返回 NETWORK_ERROR
    而不是抛异常。"""
    from fundrives.lanzou import LanZouCloud

    drive = LanZouCloud()
    with mock.patch.object(drive, "_get", return_value=None):
        result = drive.login("dummy-user", "dummy-pass")

    assert result == LanZouCloud.NETWORK_ERROR


def test_lanzou_cloud_login_by_cookie_with_mocked_network():
    """login_by_cookie 同样只在 mock 掉 _get 之后做冒烟验证；没有真实
    蓝奏云账号，无法验证真实 cookie 是否有效，这里只验证在给定假 cookie
    的情况下调用链路不出错。"""
    from fundrives.lanzou import LanZouCloud

    drive = LanZouCloud()

    fake_response = mock.Mock()
    fake_response.text = "个人中心"

    with mock.patch.object(drive, "_get", return_value=fake_response) as mocked_get:
        result = drive.login_by_cookie({"ylogin": "dummy"})

    assert result == LanZouCloud.SUCCESS
    mocked_get.assert_called_once()


def test_why_error_helper():
    from fundrives.lanzou import LanZouCloud, why_error

    assert why_error(LanZouCloud.URL_INVALID) == "分享链接无效"
    assert why_error(LanZouCloud.NETWORK_ERROR) == "网络连接异常"
    assert "未知错误" in why_error(9999)


def test_import_all_shipped_submodules():
    """本包随 wheel 分发的每个子模块都要能被导入，且导入期不得有网络副作用。

    `core.py` 以前在模块顶层执行 `executors.submit(check_domains)`，import 即对
    14 个蓝奏云域名发起真实 HTTP HEAD 请求；现在已改成需显式调用的
    `refresh_available_domains()`，所以这里可以安全地把它一起纳入冒烟
    （禁网环境下的导入断言见 tests/test_core_regressions.py）。
    """
    for mod_name in (
        "fundrives.lanzou.models",
        "fundrives.lanzou.types",
        "fundrives.lanzou.utils",
        "fundrives.lanzou.parser",
        "fundrives.lanzou.extra",
        "fundrives.lanzou.errors",
        "fundrives.lanzou.core",
    ):
        mod = importlib.import_module(mod_name)
        assert mod is not None
