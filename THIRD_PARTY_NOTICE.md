# 第三方代码来源与协议

本仓库在 MIT 协议下发布（见 [LICENSE](LICENSE)），其中部分代码来自下列第三方项目。
按 SPEC §12.4 的要求，保留其原始版权与许可声明。

## LanZouCloud-API

- 上游项目：<https://github.com/zaxtyson/LanZouCloud-API>
- PyPI 包名：[`lanzou-api`](https://pypi.org/project/lanzou-api/)（导入名 `lanzou`）
- 原始协议：MIT（与本仓库的 MIT 兼容）
- 涉及的文件：
  - `src/fundrives/lanzou/core.py`
  - `src/fundrives/lanzou/parser.py`
  - `src/fundrives/lanzou/models.py`
  - `src/fundrives/lanzou/types.py`
  - `src/fundrives/lanzou/utils.py`
  - `src/fundrives/lanzou/extra.py`

`fundrives.lanzou` 对外导出的 `LanZouCloud` 直接来自运行时依赖 `lanzou-api`；上面
这些文件是从同一上游派生、随本仓库一起分发的实现，因此同样适用下面的许可声明。

### 原始许可证全文

```
MIT License

Copyright (c) 2019 zaxtyson

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
