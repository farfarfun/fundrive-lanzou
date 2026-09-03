# CHANGELOG

本项目遵循[语义化版本](https://semver.org/lang/zh-CN/)，变更记录按版本倒序排列。

## [1.2.75] - 2026-09-03

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
