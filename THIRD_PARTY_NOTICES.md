# 第三方组件许可说明

Reader 自身代码按 [MIT 许可](LICENSE) 发布。打包后的 `Reader.exe` 还包含下列第三方组件，它们各自遵循自己的许可证。

## Python 运行时依赖

| 组件 | 版本 | 许可证 | 项目地址 |
|---|---|---|---|
| PySide6 / PySide6_Essentials / PySide6_Addons（Qt for Python，含 Qt 6 与 Qt WebEngine / Chromium） | 6.11.2 | LGPL-3.0-only（亦可选 GPL-2.0 / GPL-3.0） | https://pyside.org |
| shiboken6 | 6.11.2 | LGPL-3.0-only（亦可选 GPL-2.0 / GPL-3.0） | https://pyside.org |
| python-docx | 1.2.0 | MIT | https://github.com/python-openxml/python-docx |
| python-pptx | 1.0.2 | MIT | https://github.com/scanny/python-pptx |
| openpyxl | 3.1.5 | MIT | https://openpyxl.readthedocs.io |
| et_xmlfile | 2.0.0 | MIT | https://foss.heptapod.net/openpyxl/et_xmlfile |
| markdown-it-py | 4.2.0 | MIT | https://github.com/executablebooks/markdown-it-py |
| mdurl | 0.1.2 | MIT | https://github.com/executablebooks/mdurl |
| lxml | 6.1.3 | BSD-3-Clause | https://lxml.de |
| Pillow | 12.3.0 | MIT-CMU | https://python-pillow.org |
| XlsxWriter | 3.2.9 | BSD-2-Clause | https://github.com/jmcnamara/XlsxWriter |
| typing_extensions | 4.16.0 | PSF-2.0 | https://github.com/python/typing_extensions |
| pywin32 | 312 | PSF | https://github.com/mhammond/pywin32 |
| pywinpty（含 winpty 与 Windows OpenConsole/ConPTY 组件） | 3.0.5 | MIT | https://github.com/andfoy/pywinpty |

### 关于 Qt / PySide6（LGPL-3.0）

- Reader 通过动态链接使用 Qt 与 PySide6，未修改其源代码；打包目录中的 Qt 动态库可以被用户自行替换为兼容版本。
- Qt 与 PySide6 的源代码可从 https://download.qt.io 和 https://code.qt.io 获取。
- Qt WebEngine 内含 Chromium 及其第三方组件，各自许可证见 Qt 文档 “Qt WebEngine Licensing”。

## 网页前端资源

Markdown 预览、PPTX 预览和终端界面使用的 JavaScript 组件及其许可证分别列在：

- `assets/md-viewer/THIRD_PARTY_NOTICES.txt`
- `assets/pptx-viewer/THIRD_PARTY_NOTICES.txt`
- `assets/terminal-viewer/THIRD_PARTY_NOTICES.txt`（含 xterm.js，MIT）
