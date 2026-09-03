"""针对 `fundrives.lanzou.extra.get_short_url` 的正常路径与边界测试。

覆盖点：
- 未配置第三方短链 token 时自动跳过对应服务，不应再硬编码尝试。
- 全部服务失败时返回空字符串，而不是抛异常。
"""

from __future__ import annotations

from unittest import mock

from fundrives.lanzou import extra


def test_get_short_url_skips_token_services_when_not_configured():
    """未设置 FUNDRIVE_LANZOU_*_TOKEN 环境变量时，不应向 dwz.lc / ecx.cx 发起请求。"""
    with (
        mock.patch.object(extra, "DWZ_LC_TOKEN", None),
        mock.patch.object(extra, "ECX_CX_TOKEN", None),
        mock.patch("fundrives.lanzou.extra.requests.post") as mocked_post,
        mock.patch(
            "fundrives.lanzou.extra.requests.get",
            return_value=mock.Mock(text="https://tinyurl.com/abc"),
        ),
    ):
        result = extra.get_short_url("https://example.com/very/long/path")

    mocked_post.assert_not_called()
    assert result == "https://tinyurl.com/abc"


def test_get_short_url_returns_empty_string_when_all_providers_fail():
    with (
        mock.patch.object(extra, "DWZ_LC_TOKEN", None),
        mock.patch.object(extra, "ECX_CX_TOKEN", None),
        mock.patch(
            "fundrives.lanzou.extra.requests.get", side_effect=Exception("network down")
        ),
        mock.patch(
            "fundrives.lanzou.extra.requests.post",
            side_effect=Exception("network down"),
        ),
    ):
        result = extra.get_short_url("https://example.com/x")

    assert result == ""
