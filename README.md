# fundrive-lanzou

蓝奏云网盘（LanZouCloud）Python API 封装，提供登录、文件/文件夹列表、
上传下载、分享与提取等常用能力，供 [fundrive](https://github.com/farfarfun/fundrive)
及其他项目以统一命名空间接入蓝奏云。

## 安装

```bash
pip install fundrive-lanzou
# 或
uv add fundrive-lanzou
```

## 快速开始

```python
from fundrives.lanzou import LanZouCloud, why_error

drive = LanZouCloud()

code = drive.login("your-username", "your-password")
if code != LanZouCloud.SUCCESS:
    raise RuntimeError(why_error(code))

# 列出根目录文件
for file in drive.get_file_list(-1):
    print(file.name, file.size)
```

## 主要能力

- 账号密码登录、Cookie 登录
- 文件/文件夹列表、搜索、重命名、移动、删除
- 上传、下载（含分享链接直链解析、提取码支持）
- 分享链接创建/查询、回收站管理

## 短链服务配置（可选）

`fundrives.lanzou.extra.get_short_url` 会依次尝试几个第三方短链服务。需要鉴权的两个
服务从环境变量读取令牌，未配置时自动跳过，改走无需鉴权的兜底服务：

```bash
export FUNDRIVE_LANZOU_DWZ_LC_TOKEN=...   # dwz.lc
export FUNDRIVE_LANZOU_ECX_CX_TOKEN=...   # ecx.cx
```

## 来源说明与第三方协议

对外暴露的核心驱动类 `LanZouCloud` 来自第三方包
[`lanzou-api`](https://pypi.org/project/lanzou-api/)（导入名同为 `lanzou`），
本仓库在此基础上提供 `fundrives.lanzou` 命名空间封装，便于与
`fundrive-alipan`/`fundrive-baidu`/`fundrive-quark` 等其他网盘驱动统一管理。

本仓库 `src/fundrives/lanzou/` 下的 `core.py`、`parser.py`、`models.py`、`types.py`、
`utils.py`、`extra.py` 同样派生自上游项目
[LanZouCloud-API](https://github.com/zaxtyson/LanZouCloud-API)，其原始协议为
**MIT，Copyright (c) 2019 zaxtyson**，与本仓库的 MIT 协议兼容。完整的来源清单与原始
许可证全文见 [THIRD_PARTY_NOTICE.md](THIRD_PARTY_NOTICE.md)。

---

## 关于 farfarfun

[farfarfun](https://github.com/farfarfun) 是一个专注于实用工具库的开源组织，
涵盖云存储、数据处理、AI、多媒体与开发工具链等方向。

- 🏠 组织主页：<https://github.com/farfarfun>
- 📦 PyPI：<https://pypi.org/user/niuliangtao/>
- 📧 联系：farfarfun@qq.com

本项目基于 [MIT](LICENSE) 协议开源。
