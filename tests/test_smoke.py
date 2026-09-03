"""fundrive-lanzou 轻量冒烟测试（smoke tests）。

范围：只确认包能否正常安装 / 导入，以及真正会被使用到的核心驱动类
`LanZouCloud` 在不发起真实网络请求的情况下基本可用。不追求覆盖率，
不测试真实登录 / 上传 / 下载等需要真实蓝奏云账号的业务逻辑。

按 NAMING.md 的约定，本仓库的导入名是共享命名空间 `fundrives`
（`fundrive-alipan` / `fundrive-baidu` / `fundrive-lanzou` / `fundrive-quark`
都发布到同一个 `fundrives` 顶层包下）。经检查，本仓库源码没有 import
`fundrive` 主包（既不是 `fundrive` 定义的驱动接口的实现类，也没有任何
`import fundrive` / `from fundrive import ...`），所以这里不测试
`fundrive` 的导入，也没有为它新增依赖。

关于依赖修复（详见仓库根目录 pyproject.toml 的改动）：
`src/fundrives/lanzou/__init__.py` 第一行是
    from lanzou.api.core import LanZouCloud
这里的 `lanzou` 指向 PyPI 上的第三方包 `lanzou-api`
(https://pypi.org/project/lanzou-api/，导入名恰好也叫 `lanzou`)，
版本号与 __init__.py 里硬编码的 `version = "2.6.8"` 完全一致。但
`lanzou-api` 之前没有出现在 pyproject.toml 的 `dependencies` 里，
全新环境下 `import fundrives.lanzou` 会直接
`ModuleNotFoundError: No module named 'lanzou'`。本次冒烟测试新增时，
已把 `lanzou-api>=2.6.8`（以及它间接需要、但本仓库源码里其它模块也
直接 import 的 `requests` / `requests-toolbelt`）补进 dependencies，
不涉及任何 src 下业务代码的改动。

另外发现但本次不修复的问题（仅记录，见下面 `test_...dead_vendored...`
用例前的注释）：`src/fundrives/lanzou/{core,models,types,utils,parser,extra}.py`
是一份看起来同源、但已经和上面提到的 `lanzou-api` 平行存在的"影子代码"，
并没有被 `src/fundrives/lanzou/__init__.py` 引用到（`__init__.py`
用的是外部包 `lanzou.api.core.LanZouCloud`，不是本地 `.core`），
是死代码；其中 `core.py` 顶层还有一行
`executors.submit(check_domains)`，import 这个模块本身就会另起一个
线程去对蓝奏云各个域名发起真实 HTTP HEAD 请求 —— 属于"导入即产生真实
网络副作用"，所以这里不 import/测试这份死代码里的 `core.py`
（避免测试环境真的发起网络请求），只对其中确认没有导入期副作用的
纯逻辑模块做一个轻量 import 冒烟。
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


def test_import_dead_vendored_pure_logic_modules():
    """src/fundrives/lanzou/{models,types,utils,parser,extra}.py 是没有被
    `fundrives.lanzou.__init__` 引用到的"影子代码"（见模块 docstring），
    但它们本身在 import 期间没有网络副作用，这里做一个最轻量的 import
    冒烟，确认这些文件至少语法/依赖上是可用的。

    注意：故意不 import 同目录下的 `core.py` —— 它的模块顶层有
    `executors.submit(check_domains)`，import 它会另起线程对蓝奏云
    发起真实 HTTP 请求，不适合在冒烟测试里触发（见模块 docstring）。
    """
    for mod_name in (
        "fundrives.lanzou.models",
        "fundrives.lanzou.types",
        "fundrives.lanzou.utils",
        "fundrives.lanzou.parser",
        "fundrives.lanzou.extra",
    ):
        mod = importlib.import_module(mod_name)
        assert mod is not None
