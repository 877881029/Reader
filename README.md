# Reader

Windows 桌面文档查看器，当前版本 **0.1.0**（功能仍在迭代，不是 1.0 完工版）。

## 能力

打开并预览：

| 格式 | 默认体验 |
|---|---|
| `.pptx` | 本地视觉预览（缩略图、翻页、缩放）；可切文本模式；可选 Office 高保真 |
| `.md` | 只读渲染（表格、代码、离线 Mermaid、`[[wikilink]]`）；`Ctrl+I` 编辑，`Ctrl+S` 保存，`Ctrl+T` 回渲染 |
| `.pdf` | Chromium 内置阅读器（只读） |
| `.json` / `.yaml` / `.yml` / `.xml` / `.c` / `.h` | 只读代码阅读（行号、语法高亮、可复制） |
| `.svg` | 只读图形预览（纸色适窗，Ctrl+滚轮缩放，不执行脚本） |
| `.png` / `.jpg` / `.jpeg` / `.gif` / `.webp` / `.bmp` | 只读图片预览（纸色适窗，Ctrl+滚轮缩放） |
| `.docx` / `.xlsx` | 内置 HTML 预览；可选 Office 高保真 |

窗口：记事本式标签、拖入文件、`Ctrl+O`、`Ctrl+F` 查找、设为当前用户默认打开方式、资源管理器「打开方式」、单实例、可新建窗口。

本机没有 Microsoft Office 也能用。点「Office 高保真」才需要已安装的 Word/PowerPoint/Excel。

**0.1.0 不做：** 翻译、左右对照、格式互转、macOS/Linux。

## 快速运行（同事）

需要 Windows 10/11 和 **Python 3.12+**。没有 Python 时先执行：

```text
winget install Python.Python.3.12
```

然后在仓库根目录：

```text
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup.ps1
```

脚本会创建 `.venv`、安装依赖并启动 Reader。首次启动会写桌面快捷方式和「打开方式」。

只装依赖不启动：

```text
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup.ps1 -SkipLaunch
```

开发者还要测试/冻结构建时加上 `-Dev`。

## 本地冻 exe（可选）

不要把 `dist/` 或 exe 提交进 git。本机若要打安装目录：

```text
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

产物在 `dist\Reader\Reader.exe`（约 600MB 的 onedir，含 Qt WebEngine）。需要 Node 18+。

## 文档

- 功能全解：`docs/Reader功能全解.md`
- 规格与进度：`docs/STATUS.md`
- 0.1.0 源码快照说明：`release/README.md`
