"""html 页面参数解析。

本模块源自第三方项目 LanZouCloud-API（MIT，Copyright (c) 2019 zaxtyson），
原始协议与版权声明见仓库根目录 `THIRD_PARTY_NOTICE.md`。
"""

import re


def parse_file_name(html: str) -> str:
    name = (
        re.search(r"<title>(.+?) - 蓝奏云</title>", html)
        or re.search(r'<div class="filethetext".+?>([^<>]+?)</div>', html)
        or re.search(r'<div style="font-size.+?>([^<>].+?)</div>', html)
        or re.search(r"var filename = '(.+?)';", html)
        or re.search(r'id="filenajax">(.+?)</div>', html)
        or re.search(r'<div class="b"><span>([^<>]+?)</span></div>', html)
    )

    return name.group(1).replace("*", "_") if name else "未匹配到文件名"


def parse_file_size(html: str) -> str:
    size = (
        re.search(r"大小.+?(\d[\d.,]+\s?[BKM]?)<", html)
        or re.search(r'class="n_filesize">[^<0-9]*([.0-9 MKBmkbGg]+)<', html)
        or re.search(r"大小：(.+?)</div>", html)
    )  # VIP 分享页面
    return size.group(1) if size else ""


def parse_time(html: str) -> str:
    time = re.search(r'class="n_file_infos">(.+?)</span>', html) or re.search(
        r">(\d+\s?[秒天分小][钟时]?前|[昨前]天\s?[\d:]+?|\d+\s?天前|\d{4}-\d\d-\d\d)<",
        html,
    )
    return time.group(1) if time else ""


def parse_desc(html: str) -> str:
    desc = re.search(r'class="n_box_des">(.*?)</div>', html) or re.search(
        r"文件描述.+?</span><br>\n?\s*(.*?)\s*</td>", html
    )
    return desc.group(1) if desc else ""


def parse_sign(html: str) -> str:
    """从分享页面 HTML 中提取下载请求所需的 `sign` 鉴权串。

    `sign` 是一次性下载授权凭据，**不会**被写入日志。

    :param html: 已去掉注释的分享页面 HTML。
    :return: 提取到的 `sign` 字符串。
    :raises IndexError: 页面结构变化，未能匹配到 `sign`。
    """
    # sign 放在变量后面前后各有一个干扰项
    sign = re.findall(r"'sign':(.+?),", html)
    if len(sign) > 1:
        sign = sign[1]
    else:
        sign = sign[0]
    if len(sign) < 20:  # 此时 sign 保存在变量里面, 变量名是 sign 匹配的字符
        sign = (
            re.findall(r"var sasign\s*=\s*'(.{10,}?)';", html)
            or re.findall(r"var skdklds\s*=\s*'(.{10,}?)';", html)
            or re.findall(rf"var {sign}\s*=\s*'(.+?)';", html)
        )[-1]
    return sign.replace("'", "")


def parse_form_hash(html: str) -> str:
    return re.findall(r'name="formhash" value="(.+?)"', html)[0]


def parse_folder_name(html: str) -> str:
    folder_name = (
        re.search(r"var.+?='(.+?)';\n.+document.title", html)
        or re.search(r'user-title">(.+?)</div>', html)
        or re.search(r'<div class="b">(.+?)<div', html)
    )  # 会员自定义
    return folder_name.group(1) if folder_name else ""


def parse_folder_id(html: str) -> str:
    return re.findall(r"'fid':'?(\d+)'?,", html)[0]


def parse_folder_time(html: str) -> str:
    folder_time = re.search(r'class="rets">([\d\-]+?)<a', html)  # 日期不全 %m-%d
    return folder_time.group(1) if folder_time else ""


def parse_folder_desc(html: str) -> str:
    folder_desc = (
        re.search(r'id="filename">(.+?)</span>', html, re.DOTALL)
        or re.search(r'<div class="user-radio-\d"></div>(.+?)</div>', html)
        or re.search(
            r'class="teta tetb">说</span>(.+?)</div><div class="d2">', html, re.DOTALL
        )
    )
    return folder_desc.group(1) if folder_desc else ""
