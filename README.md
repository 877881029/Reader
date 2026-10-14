# Reader

Windows 桌面文档查看器，当前版本 **0.1.0**（功能仍在迭代，不是 1.0 完工版）。

## 能力

打开并预览：

| 格式 | 默认体验 |
|---|---|
| `.pptx` | 本地视觉预览（缩略图、翻页、缩放）；可切文本模式；可选 Office 高保真 |
| `.md` | 只读渲染（表格、代码、离线 Mermaid、`[[wikilink]]`）；标题栏「编辑 \| 预览」或 `Ctrl+I` 编辑，`Ctrl+S` 保存，`Ctrl+T` 回渲染；编辑/预览无缝切换，预览实时显示未保存内容 |
| `.pdf` | Chromium 内置阅读器（只读） |
| `.json` / `.yaml` / `.yml` / `.xml` / `.c` / `.h` / `.cpp` / `.hpp` / `.cc` / `.cxx` / `.hh` / `.hxx` / `.inl` / `.ipp` | 记事本式编辑（行号、语法高亮、撤销/重做、`Ctrl+S` 保存） |
| `.txt` | 记事本式编辑（行号、无语法高亮、`Ctrl+S` 保存）；`Ctrl+N` 新建 |
| `.svg` | 只读图形预览（纸色适窗，Ctrl+滚轮缩放，不执行脚本） |
| `.png` / `.jpg` / `.jpeg` / `.gif` / `.webp` / `.bmp` | 只读图片预览（纸色适窗，Ctrl+滚轮缩放） |
| `.docx` / `.xlsx` | 内置 HTML 预览；可选 Office 高保真 |
| `.bin` | 十六进制查看：每行 16 字节，Byte / Word / DWord（小端）切换，右侧 ASCII，悬停两侧联动高亮；内存映射，GB 级文件也秒开 |

窗口：记事本式标签、标题栏 `+` 新建菜单（新建文件 / 打开文件 / Browser 标签内网页浏览 / Terminal 标签内真终端：PowerShell / Command Prompt，Copilot 浅色配色）、拖入文件、`Ctrl+O`、`Ctrl+F` 查找、`Ctrl+H` 替换、`Ctrl+J` 转到行、设为当前用户默认打开方式、资源管理器「打开方式」、单实例、可新建窗口。

Reader 启动时只注册为「打开方式」候选，不会清除已有文件默认应用，也不会自动打开 Windows 默认应用设置。需要更改默认应用时，请在 Windows 设置中手动选择。

文本/代码编辑保留原编码与换行：UTF-8（含 BOM）、UTF-16 BOM、GB18030 和 CRLF/LF 原样写回，原子替换防止写坏；无法无损识别编码的文件显示「只读」并拒绝保存。`Ctrl+Shift+S` 另存为，标签 `*` 提示未保存，关闭标签或窗口前询问「保存 / 不保存 / 取消」。

代码页底部是记事本式只读状态栏（`Ln 行, Col 列 | Size 字号 | Type 类型`）；`Ctrl+J` 转到行，`Ctrl+=` / `Ctrl+-` / `Ctrl+0` 或 `Ctrl+滚轮` 调字号（8–24pt），`Alt+Z` 切换自动换行；每个标签页各自保存这些状态。

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

发布门通过后，把这份构建装到固定位置并刷新桌面快捷方式与文件关联：

```text
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install_local.ps1
```

默认安装到 `%LOCALAPPDATA%\Programs\Reader`（运行中会拒绝覆盖），校验 exe 哈希后把桌面 `Reader.lnk` 和「Reader 文档」打开命令指向它。Reader 自身启动时也会把指向**旧版 Reader.exe** 的桌面快捷方式刷新为当前 exe，但不会改动指向其他程序的同名快捷方式。

提交到 `main` 或打开 pull request 时，Windows CI 会在 Python 3.12 和
Node.js 22 的干净环境中执行同一快速质量门；本地与远端使用同一验收入口。

## 文档

- 功能全解：`docs/Reader功能全解.md`
- 规格与进度：`docs/STATUS.md`
- 0.1.0 源码快照说明：`release/README.md`
