"""第三方短链服务封装。

本模块源自第三方项目 LanZouCloud-API（MIT，Copyright (c) 2019 zaxtyson），
原始协议与版权声明见仓库根目录 `THIRD_PARTY_NOTICE.md`。
"""

import json
import os

import requests
from farlog import getLogger

from .utils import USER_AGENT

logger = getLogger("fundrive")
timeout = 2

# 第三方短链服务的访问令牌不应硬编码在代码中，改为从环境变量读取；
# 未配置时直接跳过对应服务，走后面的无鉴权兜底方案。
DWZ_LC_TOKEN = os.getenv("FUNDRIVE_LANZOU_DWZ_LC_TOKEN")
ECX_CX_TOKEN = os.getenv("FUNDRIVE_LANZOU_ECX_CX_TOKEN")

__all__ = ["get_short_url"]

# 调用第三方短链接口时可能遇到的失败类型：
# - requests.RequestException：网络层失败
# - json.JSONDecodeError（ValueError 子类）：响应不是合法 JSON
# - KeyError / TypeError：响应 JSON 结构与预期不符，取不到 `short` 字段
_SHORTEN_ERRORS = (requests.RequestException, ValueError, KeyError, TypeError)


def _post_shorten(api_url: str, url: str, token: str) -> str:
    """向需要 Token 鉴权的短链服务提交一次缩短请求。

    :param api_url: 短链服务的 API 地址。
    :param url: 待缩短的长链接。
    :param token: 该服务的访问令牌，仅放入请求头，不写日志。
    :return: 缩短后的短链接；失败时返回空字符串。
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Authorization": f"Token {token}",
    }
    try:
        resp = requests.post(
            api_url, json={"url": url}, headers=headers, timeout=timeout
        )
        # 只记录状态与长度：响应体可能带回鉴权/配额等敏感信息
        logger.debug(
            f"短链服务响应: api={api_url} status={resp.status_code} "
            f"length={len(resp.text)}"
        )
        rsp = json.loads(resp.text)
        if rsp:
            return rsp["short"]
    except _SHORTEN_ERRORS as e:
        logger.warning(
            f"短链服务调用失败: api={api_url} reason={type(e).__name__}: {e}"
        )
    return ""


def get_short_url(url: str) -> str:
    """把长链接转换成短链接。

    依次尝试：配置了 Token 的 dwz.lc、ecx.cx，然后是无需鉴权的 tinyurl、gg.gg。
    未配置 `FUNDRIVE_LANZOU_DWZ_LC_TOKEN` / `FUNDRIVE_LANZOU_ECX_CX_TOKEN` 时
    自动跳过对应服务。

    :param url: 待缩短的长链接。
    :return: 缩短后的短链接；所有服务都失败时返回空字符串。
    """
    headers = {"User-Agent": USER_AGENT}
    short_url = ""

    if DWZ_LC_TOKEN:
        # 10W次/天, https证书过期
        short_url = _post_shorten("https://www.dwz.lc/api/url/add", url, DWZ_LC_TOKEN)

    if not short_url and ECX_CX_TOKEN:
        # 10W次/天, https证书过期
        short_url = _post_shorten("https://www.ecx.cx/api/url/add", url, ECX_CX_TOKEN)

    if not short_url:
        try:
            # https, 国外,速度较慢
            resp = requests.get(
                f"https://tinyurl.com/api-create.php?url={url}",
                headers=headers,
                timeout=timeout,
            )
            if resp.text and len(resp.text) < 32:
                short_url = resp.text
        except requests.RequestException as e:
            logger.warning(
                f"短链服务调用失败: api=tinyurl reason={type(e).__name__}: {e}"
            )

    if not short_url:
        gg_headers = dict(headers)
        gg_headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        try:
            # 支持https, 国外,速度较慢
            resp = requests.post(
                "http://gg.gg/create",
                data={"long_url": url},
                headers=gg_headers,
                timeout=timeout,
            ).text
            if resp:
                short_url = resp
        except requests.RequestException as e:
            logger.warning(
                f"短链服务调用失败: api=gg.gg reason={type(e).__name__}: {e}"
            )

    return short_url
