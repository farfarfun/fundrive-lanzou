from lanzou.api.core import LanZouCloud

version = "2.6.8"


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


__all__ = ["LanZouCloud", "models", "types", "utils", "version", "why_error"]
