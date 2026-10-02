"""`fundrives.lanzou`：蓝奏云网盘 API 封装。

对外暴露的 `LanZouCloud` 来自第三方包 `lanzou-api`（导入名 `lanzou`）。
本包另外提供 `fundrives.lanzou.core` 等由 LanZouCloud-API 派生的实现模块，
来源与原始协议见仓库根目录 `THIRD_PARTY_NOTICE.md`。
"""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version

from lanzou.api.core import LanZouCloud

#: 本包自身的版本号，唯一来源是 `pyproject.toml` 的 `[project].version`，
#: 不在源码里硬编码，避免版本漂移。
try:
    __version__ = _dist_version("fundrive-lanzou")
except PackageNotFoundError:  # 源码树里未安装本包时的兜底
    __version__ = "0.0.0.dev0"

#: 实际提供 `LanZouCloud` 实现的第三方包 `lanzou-api` 的版本号。
#: 这里从已安装的发行包元数据读取，而不是写死字面量。
try:
    version = _dist_version("lanzou-api")
except PackageNotFoundError:  # pragma: no cover - 依赖缺失时 import 已经失败了
    version = "unknown"


def why_error(code: int) -> str:
    """将 `LanZouCloud` 返回的状态码转换为中文错误原因说明。

    :param code: `LanZouCloud` 各方法返回的状态码，例如
        `LanZouCloud.URL_INVALID`、`LanZouCloud.NETWORK_ERROR` 等。
    :return: 对应状态码的中文描述；未知状态码返回 `"未知错误 {code}"`。
    """
    if code == LanZouCloud.URL_INVALID:
        return "分享链接无效"
    elif code == LanZouCloud.LACK_PASSWORD:
        return "缺少提取码"
    elif code == LanZouCloud.PASSWORD_ERROR:
        return "提取码错误"
    elif code == LanZouCloud.FILE_CANCELLED:
        return "分享链接已失效"
    elif code == LanZouCloud.ZIP_ERROR:
        return "解压过程异常"
    elif code == LanZouCloud.NETWORK_ERROR:
        return "网络连接异常"
    elif code == LanZouCloud.CAPTCHA_ERROR:
        return "验证码错误"
    else:
        return f"未知错误 {code}"


__all__ = [
    "LanZouCloud",
    "__version__",
    "errors",
    "models",
    "types",
    "utils",
    "version",
    "why_error",
]
