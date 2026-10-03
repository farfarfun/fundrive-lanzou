# CHANGELOG

本项目遵循[语义化版本](https://semver.org/lang/zh-CN/)，变更记录按版本倒序排列。

## [未发布]

### 修复

- 移除 `core.py` 的导入期网络副作用：原先模块顶层就 `executors.submit(check_domains)`，
  一 `import` 就并发打出 14 个 HEAD 请求；现在改为显式调用
  `check_domains()` / `refresh_available_domains()`
- 修复 `check_domains` 边遍历边删除 `available_domains` 的缺陷（会跳过候选域名），
  并把探测超时从 `0.1s` 放宽到可配置的 `5s`（0.1s 会把正常域名误判为不可用而剔除）
- 修复两处无限重试热循环：`get_folder_info_by_url` 在响应为空时 `continue` 不计数、
  `get_file_list` 在 `not resp` 时 `continue` 不计数，均会 100% CPU 空转且永不退出；
  现在统一受 `_MAX_REFRESH_RETRY` 约束，超限后按网络错误返回（`get_file_list` 之前
  只声明了 `retry` 变量但从未真正自增/判断上限，复核时发现仍会死循环，本次补上
  `retry += 1` 与上限判断）
- 修复两处 `None` 解引用：`get_folder_info_by_url` 在 `_post` 返回 `None` 时访问
  `post.text`、`get_file_info_by_url` 的错误日志里访问 `first_page.text`，都会抛
  `AttributeError` 而不是返回错误码（复核时发现判空条件写成了 `if not post.text`，
  `post is None` 时同样会先抛 `AttributeError`，本次改为 `if post is None or not
  post.text`）
- 修复短链 Token 跨服务泄露：`get_short_url` 原先 4 个服务共用同一个 `headers` dict，
  `Authorization: Token <dwz.lc token>` 会残留并被发给 tinyurl.com 和 gg.gg；
  现在带鉴权的请求各自构造独立请求头
- 日志脱敏：不再记录 `_post` 的请求 body（登录请求的 body 就是账号密码）、
  下载授权 `sign`（原先在 `parser.py` 里以 ERROR 级别打原文）、分享页整页 HTML、
  直链、短链服务响应正文、`k`/`t`/`lx` 一次性鉴权参数
- 修复 `get_rec_dir_list` 中循环变量 `time` 遮蔽模块级 `import time`（ruff F402）
- 把 `py.typed` 从 `src/fundrives/` 移到 `src/fundrives/lanzou/`：`fundrives` 是
  PEP 420 命名空间包，标记放在命名空间层既不符合 PEP 561，还会与其他
  `fundrive-*` 包装出同一个文件路径
- `uv.lock` 升级 urllib3 2.7.0 → 2.8.0（已知漏洞）
- `login_by_cookie` 的调试日志误用 stdlib logging 的 `%s` 占位符，farlog（loguru）
  不支持该语法，参数被静默丢弃；改为 `{}` 占位符

### 新增

- `src/fundrives/lanzou/errors.py`：`LanZouError` / `NoAvailableDomainError`，
  替换原先的裸 `raise Exception`
- `THIRD_PARTY_NOTICE.md`：恢复被误删的上游 MIT 许可全文与版权声明
  （LanZouCloud-API，Copyright (c) 2019 zaxtyson），并列明派生自上游的文件清单
- `tests/test_core_regressions.py`、`tests/test_logging_and_metadata.py`：
  28 条回归测试，覆盖导入期无网络、域名探测、重试上限、`None` 响应、日志脱敏、
  Token 不跨服务、版本号与 `pyproject.toml` 一致、`py.typed` 位置、第三方许可留存
- `tests/test_core_public_api.py`：24 条测试，为此前完全没有测试覆盖的公开 API
  （`move_file`、`get_share_info`、`set_passwd`、`upload_file`、`upload_dir`、
  `down_file_by_url`、`down_dir_by_url`）各补上正常路径、边界（缺失/空文件、
  超限大文件、非法 id）与失败路径（网络异常、服务端拒绝）
- `[tool.ruff]` / `[tool.ruff.lint]` 显式规则集，锁定 lint 基线

### 变更

- `__version__` 改为由 `importlib.metadata` 推导，不再硬编码；`version` 报告的是
  实际安装的 `lanzou-api` 版本（原先写死 `2.6.8`）
- 为 `login`/`delete`/`upload_file`/`check_domains` 等补充类型标注与中文文档字符串
- 删除 `core.py`/`utils.py`/`extra.py` 里残留的 `if __name__ == "__main__":` 调试入口
- `un_serialize`、`is_file_url`、`is_folder_url`、短链调用改用窄异常捕获，
  不再用 `except Exception` 吞掉编程错误
- README 补充短链服务环境变量说明，以及第三方来源与协议说明

## [1.2.75] - 2026-09-03

> 注：该版本只存在于 Git 历史，**未发布到 PyPI**（PyPI 上的最高版本是 1.2.73）。

### 修复

- 日志统一迁移到组织自有包 `farlog`，移除对 `funutil` 的直接依赖（`core.py`/`extra.py`/`parser.py`/`utils.py`）
- 移除 `extra.py` 中硬编码的第三方短链服务 Authorization token，改为从环境变量
  （`FUNDRIVE_LANZOU_DWZ_LC_TOKEN`/`FUNDRIVE_LANZOU_ECX_CX_TOKEN`）读取，未配置时自动
  跳过对应服务并走既有的无鉴权兜底方案
- 删除诊断性 `print` 输出，并对日志中出现的 cookie（`acw_sc__v2`）、提取码等敏感字段做脱敏处理

### 新增

- 补充 `CHANGELOG.md`
- 提交 `uv.lock` 保证可复现构建
- 为 `why_error`、`get_short_url` 补充完整类型标注
- 扩充 `tests/`，为公开 API 增加更多基于 mock 的正常路径与边界测试

### 变更

- `pyproject.toml` 补充 `[project] license = "MIT"` 与 `license-files`，移除冗余的 `[tool.setuptools] license-files = []`
- README 补充项目简介、安装命令、最小可运行示例，并追加组织介绍区块
- `.gitignore` 补充 `*.db`、`*.rar`、`.run/`、`logs/`、`.idea/`、`.vscode/`、`node_modules/` 忽略规则

## [1.2.74] 及更早版本

早期版本未系统记录变更，详见 Git 提交历史。
