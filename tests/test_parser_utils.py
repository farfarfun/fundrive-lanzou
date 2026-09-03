"""针对 `fundrives.lanzou.parser` / `fundrives.lanzou.utils` 中纯解析/
工具函数的正常路径与边界测试。

这些函数不发起网络请求，可以直接用构造好的 HTML 片段 / 字符串驱动，
用于覆盖 codex 审计中提到的“解析工具”测试缺口。
"""

from __future__ import annotations

import pytest

from fundrives.lanzou import why_error
from fundrives.lanzou.parser import (
    parse_desc,
    parse_file_name,
    parse_file_size,
    parse_folder_id,
    parse_form_hash,
    parse_time,
)
from fundrives.lanzou.utils import (
    convert_file_size_to_int,
    convert_file_size_to_str,
    is_file_url,
    is_folder_url,
    is_name_valid,
    name_format,
    remove_notes,
    time_format,
)


def test_parse_file_name_matches_title():
    html = "<title>my-file.zip - 蓝奏云</title>"
    assert parse_file_name(html) == "my-file.zip"


def test_parse_file_name_returns_placeholder_when_not_found():
    assert parse_file_name("<html></html>") == "未匹配到文件名"


def test_parse_file_size_extracts_value():
    html = '大小：<span class="n_filesize">12.34 M</span><'
    assert "12.34" in parse_file_size(html)


def test_parse_file_size_returns_empty_when_missing():
    assert parse_file_size("<html></html>") == ""


def test_parse_time_returns_empty_when_missing():
    assert parse_time("<html></html>") == ""


def test_parse_desc_extracts_description():
    html = '<div class="n_box_des">这是描述</div>'
    assert parse_desc(html) == "这是描述"


def test_parse_form_hash_extracts_value():
    html = '<input type="hidden" name="formhash" value="abc123">'
    assert parse_form_hash(html) == "abc123"


def test_parse_form_hash_raises_when_missing():
    with pytest.raises(IndexError):
        parse_form_hash("<html></html>")


def test_parse_folder_id_extracts_value():
    html = "function ff(){ fun_ex.ini_menu(1,'fid':'12345',data)}"
    assert parse_folder_id(html) == "12345"


def test_remove_notes_strips_html_comments():
    html = "<div>keep</div><!-- drop me -->"
    assert "drop me" not in remove_notes(html)


def test_name_format_strips_illegal_characters():
    assert name_format('a<b>c:d"e') == "abcde"


def test_convert_file_size_to_int_handles_units():
    assert convert_file_size_to_int("1M") == 1 << 20
    assert convert_file_size_to_int("1K") == 1 << 10
    assert convert_file_size_to_int("1G") == 1 << 30


def test_convert_file_size_to_int_returns_zero_for_unknown_unit():
    assert convert_file_size_to_int("unknown") == 0


def test_convert_file_size_to_str_roundtrip():
    assert convert_file_size_to_str(1 << 20) == "1.00 M"


def test_time_format_recognizes_relative_time():
    assert time_format("刚刚") == "刚刚"
    from datetime import datetime

    assert time_format("5 秒前") == datetime.today().strftime("%Y-%m-%d")


def test_is_name_valid_checks_suffix():
    assert is_name_valid("archive.zip") is True
    assert is_name_valid("script.py") is False


def test_is_file_url_rejects_non_lanzou_domain():
    assert is_file_url("https://example.com/foo") is False


def test_is_folder_url_rejects_non_lanzou_domain():
    assert is_folder_url("https://example.com/foo") is False


def test_why_error_helper_covers_all_known_codes():
    from fundrives.lanzou import LanZouCloud

    assert why_error(LanZouCloud.URL_INVALID) == "分享链接无效"
    assert why_error(LanZouCloud.LACK_PASSWORD) == "缺少提取码"
    assert why_error(LanZouCloud.PASSWORD_ERROR) == "提取码错误"
    assert why_error(LanZouCloud.FILE_CANCELLED) == "分享链接已失效"
    assert why_error(LanZouCloud.ZIP_ERROR) == "解压过程异常"
    assert why_error(LanZouCloud.CAPTCHA_ERROR) == "验证码错误"
    assert "未知错误" in why_error(-9999)
