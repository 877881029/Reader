# Reader

Windows 桌面文档查看器，当前版本 **0.1.0**（功能仍在迭代，不是 1.0 完工版）。

## 能力

打开并预览：

| 格式 | 默认体验 |
|---|---|
| `.pptx` | 本地视觉预览（缩略图、翻页、缩放）；可切文本模式；可选 Office 高保真 |
| `.md` | 只读渲染（表格、代码、离线 Mermaid、`[[wikilink]]`）；`Ctrl+I` 编辑，`Ctrl+S` 保存，`Ctrl+T` 回渲染 |
| `.pdf` | Chromium 内置阅读器（只读） |
| `.json` / `.yaml` / `.yml` / `.xml` / `.c` / `.h` / `.cpp` / `.hpp` / `.cc` / `.cxx` / `.hh` / `.hxx` / `.inl` / `.ipp` | 只读代码阅读（行号、语法高亮、可复制） |
| `.txt` | 只读文本阅读（行号、可复制，无语法高亮） |
| `.svg` | 只读图形预览（纸色适窗，Ctrl+滚轮缩放，不执行脚本） |
| `.png` / `.jpg` / `.jpeg` / `.gif` / `.webp` / `.bmp` | 只读图片预览（纸色适窗，Ctrl+滚轮缩放） |
| `.docx` / `.xlsx` | 内置 HTML 预览；可选 Office 高保真 |

窗口：记事本式标签、拖入文件、`Ctrl+O`、`Ctrl+F` 查找、设为当前用户默认打开方式、资源管理器「打开方式」、单实例、可新建窗口。

本机没有 Microsoft Office 也能用。点「Office 高保真」才需要已安装的 Word/PowerPoint/Excel。

**0.1.0 不做：** 翻译、左右对照、格式互转、macOS/Linux。

## 快速运行（同事）

需要 Windows 10/11、**Python 3.12+** 和 **Node.js 18+**（打冻结 exe 用）。没有 Python 时先执行：

```text
winget install Python.Python.3.12
```

然后在仓库根目录：

```text
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup.ps1
```

脚本会创建 `.venv`、安装依赖，并调用 `scripts\build_windows.ps1` 打出 `dist\Reader\Reader.exe`（约 600MB，含 Qt WebEngine），然后启动这份 exe。不要把 `dist/` 或 exe 提交进 git。

只装依赖、打 exe、不启动窗口：

```text
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup.ps1 -SkipLaunch
```

只要源码运行、不打 exe（不需要 Node）：

```text
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup.ps1 -SkipBuild
```

开发者还要测试时加上 `-Dev`。也可以单独再跑 `scripts\build_windows.ps1`。

## 开发验证

每次原子代码修改先按 TDD 完成聚焦测试，再运行统一快速质量门：

```text
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify.ps1
```

它先用锁定依赖运行并构建 PPTX/Markdown Web，再运行 Python 全量测试；
这样 Python 的供应链和 bundle manifest 检查也基于确定性构建产物。深路径
worktree 可通过 `-Python C:\短路径\python.exe` 或 `READER_PYTHON` 指定短路径
虚拟环境。

发布候选还必须运行冻结构建和 GUI smoke：

```text
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\verify.ps1 -Release
```

提交到 `main` 或打开 pull request 时，Windows CI 会在 Python 3.12 和
Node.js 22 的干净环境中执行同一快速质量门；本地与远端使用同一验收入口。

## 文档

- 功能全解：`docs/Reader功能全解.md`
- 规格与进度：`docs/STATUS.md`
- 0.1.0 源码快照说明：`release/README.md`
