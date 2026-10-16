# 更新日志

版本号只写在 `VERSION`。每次发布前运行 `python scripts\bump_version.py`，它会在这里加一个新版本标题，再把「（待补充）」换成本次的改动。

## 0.1.0 — 2026-10-15

首个持续迭代版本（此前各次安装都沿用 0.1.0，没有单独编号）。主要能力：

- 打开并阅读 Word、PPT、Excel、Markdown、PDF、纯文本、JSON / YAML / XML、C / C++ 源码、SVG、常见图片和 `.bin`；没有 Office 也能用，可选 Office 高保真预览。
- 记事本级编辑：保留原编码与换行，原子保存，`Ctrl+S` / `Ctrl+Shift+S` / `Ctrl+N`，未保存提示。
- Markdown 编辑与预览无缝切换（约 5–15 ms），预览直接显示未保存内容。
- 查找、替换（`Ctrl+H`）、转到行（`Ctrl+J`），代码页底部状态栏，字号缩放与自动换行。
- `.bin` 十六进制查看：Byte / Word / DWord，ASCII 联动高亮，内存映射秒开大文件。
- 标题栏 `+` 菜单：新建文件、打开文件、Browser 标签、Terminal 标签（PowerShell / Command Prompt 真终端）。
- 每次双击开新窗口，共用一个后台进程，已运行时再打开约 1 s；标签可拖出成新窗口或拖进别的窗口，状态原样保留。
- 界面字体改为 Microsoft YaHei UI，去掉启动时的字体回退卡顿；冷启动打开 `.txt` 从 14.1 s 降到约 3–5 s。
