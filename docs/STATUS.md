# Reader 项目状态（AI 接手必读）

最后更新：2026-10-16。本页只放当前状态、每次更新必做和历史要点；每一步的详细证据在 git 提交记录和 `docs/superpowers/specs/`、`plans/` 里。

## 当前状态

- 版本：`VERSION` = 0.1.1（规则见下节）。
- 已安装：`%LOCALAPPDATA%\Programs\Reader\Reader.exe` 0.1.1，SHA256 `8FF1A89399F6C90A8647ED8BC8C3115A72FF115A1A5CC32D447372D59FD7B7EE`（2026-10-16，阶段 A），桌面快捷方式指向它。
- 技术：Python 3.12 + PySide6 6.11.2（依赖全部固定版本）；PyInstaller onedir；入口 `src/reader/launcher.py`（不导入 Qt，经命名管道把文件转给已运行的 Reader，否则启动完整应用）；每次打开一个新窗口，标签可在窗口间拖动；Markdown / PPTX / PDF / Office 预览走 Qt WebEngine，文本/代码/图片/`.bin` 是原生视图；终端为 ConPTY + xterm.js。
- 测试：Python 约 670 个 + 三个前端 vitest；`scripts\verify.ps1` 快速质量门，`-Release` 发布门（冻结构建 + GUI 冒烟，约 20–35 分钟，不要中途打断）。

## 每次更新必做

1. 用户确认目标 → 写规格（`specs/`）和计划（`plans/`）→ 更新本页 → 提交并推送。
2. 每个任务按 TDD：先写测试并看到失败（RED），再写最小实现（GREEN）；每次代码修改验证后立即更新本页、单独提交并推送 `origin/main`（账号 `877881029`）。
3. 发布：`python scripts\bump_version.py`（修订号加 1，必须在打包前，安装包才带新版本号）→ 把 `CHANGELOG.md` 新版本下的「（待补充）」换成本次改动 → `scripts\verify.ps1 -Release` 通过 → `scripts\install_local.ps1` 安装（Reader 正在运行时会拒绝覆盖，先请用户关闭）→ 本页记录版本与 SHA256 → 提交推送。
4. 规则原文：`AGENTS.md`、`docs/superpowers/process.md`、`.cursor/rules/git-progress-handoff.mdc`。

## 当前目标

**Reader 高级化（参照 Tasker 新功能筛选）**（已确认，执行中）

- 用户需求（2026-10-16）：Tasker 新增了退出保存、发布仓库、版本号、设置页、数据安全等功能，先筛选哪些适合 Reader，列出开发列表，确认后逐项开发；用户要求开发列表用中文，并追求「打开任何文件都最快」。
- 不适合 Reader（不做）：全局快速记录快捷键；日志摘要、到点提醒；删除进回收站（Reader 不删除用户文件）；每日全量数据备份（文档属于用户自己）；桌面快捷方式（已具备）。
- 实测依据（2026-10-16，本机其他程序占 CPU 约 90%）：Reader 常驻时打开文本/代码/JSON 0.45–0.65s，Markdown 每次 2.3–2.8s（每个新窗口都要新起 Chromium 渲染进程并加载页面）；`Reader.exe` 自身启动并转发约 0.5–0.9s；常驻内存约 620 MB（含 Chromium）。因此加入 C4、C5 两项提速。本机有 VS 2022 Professional（MSVC），C5 可行。
- 开发列表（按顺序；每项：规格 → TDD → 发布验证 → 安装 → 推送）：

| 编号 | 阶段 | 内容 | 规模 | 状态 |
|---|---|---|---|---|
| A1 | 基础 | 版本号统一：只写在 `VERSION`，脚本每次加 1，规则写进流程文档 | 小 | 已完成 |
| A2 | 基础 | 依赖固定为当前测试通过的版本 | 小 | 已完成 |
| A3 | 基础 | 更新日志 + 许可证（含第三方许可说明） | 小 | 已完成 |
| A4 | 基础 | 删除无用代码；精简 STATUS；README 按实际功能重写并加截图；仓库简介和标签 | 小 | 已完成 |
| A5 | 基础 | 文本/代码视图里的网址可 Ctrl+点击打开 | 小 | 已完成 |
| B1 | 数据安全 | 未保存修改和未命名草稿后台自动暂存，注销、关机或崩溃后下次启动恢复 | 大 | 待开始 |
| B2 | 数据安全 | Ctrl+Shift+T 重新打开刚关闭的标签 | 小 | 待开始 |
| B3 | 数据安全 | 保存前保留旧版本的历史副本，自动清理 | 中 | 待开始 |
| C1 | 设置 | 设置窗口：通用 / 快捷键 / 功能说明 / 数据 | 中 | 待开始 |
| C2 | 设置 | 快捷键可自定义，冲突提示，恢复默认 | 中 | 待开始 |
| C3 | 提速 | 关闭最后一个窗口后托盘常驻（可选），可选开机自启 | 中 | 待开始 |
| C4 | 提速 | 备用视图：后台预备 Markdown/网页视图，网页类文档也快速打开（先做原型验证） | 大 | 待开始 |
| C5 | 提速 | 极小原生启动器（C 编写，只负责转发），再省 0.5–0.9s | 中 | 待开始 |
| D1 | 发布 | GitHub 发布（保留最近 5 个）+ 一行命令安装/升级，PowerShell 5.1 实测 | 中 | 待开始 |

- 阶段 A 规格：`docs/superpowers/specs/2026-10-16-foundations-design.md`；计划：`docs/superpowers/plans/2026-10-16-foundations.md`（5 任务）。版本规则：每次发布前修订号加 1（0.1.0 → 0.1.1 …）。
- A1 完成：新增 `scripts/version_tools.py`（解析、加 1、写 `VERSION` 与 README「当前版本」行、生成 Windows 版本资源）和 `scripts/bump_version.py`（默认修订号加 1，`--minor` / `--major` / `--set X.Y.Z`，格式不对时什么都不改并返回非 0）；`pyproject.toml` 改为 `dynamic = ["version"]` 从 `VERSION` 读取；`reader.spec` 打包时按 `VERSION` 生成 `build/version_info.txt`，删除仓库里的 `version_info.txt`；发布前运行脚本的规则写进 `AGENTS.md`、`process.md`、`.cursor/rules/git-progress-handoff.mdc`。原来写死 `0.1.0` 的测试改为读 `VERSION`。RED：`10 failed, 2 passed`；GREEN：版本/打包/卫生相关 `46 passed`。注意：`AGENTS.md` 第 4 条指向的 PPTX 规格已过时，A4 一并清理。
- A2 完成：`pyproject.toml` 运行与开发依赖全部改为 `==` 当前测试通过的版本（PySide6 6.11.2、python-docx 1.2.0、python-pptx 1.0.2、openpyxl 3.1.5、markdown-it-py 4.2.0、pywin32 312、pywinpty 3.0.5；pytest 9.1.1、pytest-qt 4.5.0、pytest-mock 3.15.1、Pillow 12.3.0、PyInstaller 6.22.3）。新测试断言每个依赖都是精确版本且与已安装版本一致。RED：`1 failed`（`PySide6>=6.7` 未固定）；GREEN：卫生/打包/版本 `46 passed`；`pip install -e ".[dev]" --dry-run` 无冲突。
- A3 完成：新增 `CHANGELOG.md`（0.1.0 汇总至今主要能力）、`LICENSE`（MIT，`Copyright (c) 2026 877881029`，与 Tasker 一致）、`THIRD_PARTY_NOTICES.md`（按已安装包元数据列出全部 Python 运行时依赖及许可证，说明 Qt/PySide6 为 LGPL-3.0、动态链接未修改，并指向三个前端资源的许可说明）；`reader.spec` 把 `LICENSE` 与 `THIRD_PARTY_NOTICES.md` 打进安装目录；`bump_version.py` 现在会在更新日志顶部插入「## 新版本 — 日期」和「（待补充）」。新测试：更新日志顶部版本 = `VERSION`；许可说明覆盖运行时依赖闭包里的每个包（按元数据动态计算）；打包包含两个文件；脚本插入条目。RED：`3 failed`；GREEN：版本/打包/卫生 `49 passed`。
- A4 第一步完成（删除无用代码）：删除 `shell/settings_claim.py` 及测试、`ext/`（翻译/转换/分屏空壳）及测试、根目录 4 个 `task-*-report.md`；同时删掉只为它服务的 `register_open_with(protected_claimer=)` 钩子及测试、`test_main_launch` 中依赖该模块的测试。新卫生测试断言这些路径不存在、源码不再引用。RED：`1 failed`；GREEN：全量 `667 passed, 1 skipped` + 该测试通过。`.superpowers/sdd/` 里的历史子任务报告未动。
- A4 第二步完成（README）：按实际功能重写 README（能打开什么、主要功能、按窗口动作逐项核对的快捷键表、安装运行、开发、文档、许可），加 4 张截图 `docs/images/{welcome,markdown,code,hex}.png`（示例文件放在公共文档目录，截图里不含个人路径，截完已删除）；`AGENTS.md` 第 4 条改为指向 STATUS。新测试 `tests/test_readme.py`：窗口每个快捷键都出现在 README（临时删掉 `F3` 时测试失败，已验证能防止文档漂移）；README 引用的图片都存在。
- A4 第三步完成（精简 STATUS）：本页从约 980 行精简为约 120 行：当前状态、每次更新必做、当前目标、历史要点（约 50 个已完成目标各一行并附规格文件）、环境与经验、接手检查清单；逐步证据留在 git 历史与规格/计划。新卫生测试断言前四节顺序且总行数 < 250。RED：`1 failed`；GREEN：卫生测试 `9 passed`。
- A4 完成：GitHub 仓库简介设为「Windows 桌面文档查看器：双击即读 Word / PPT / Excel / Markdown / PDF / 源码 / 图片 / 二进制，像记事本一样轻快，无需 Office」，标签 windows、document-viewer、markdown、pptx、docx、xlsx、pdf、hex-viewer、pyside6、qt（`gh repo view` 已核对）。
- A5 完成：新模块 `preview/link_click.py`：`url_at` / `url_spans` 只识别 http(s)，遇空白、引号、尖括号和中文标点即止，去掉结尾的英文标点，括号不成对才去掉（维基式 `Foo_(bar)` 保留）；`LinkClicker` 事件过滤器挂在 `CodeTextView` 和 `MarkdownTextView` 的编辑器上：按住 Ctrl 悬停在网址上显示手形和蓝色下划线（与当前行高亮共存），Ctrl+单击用默认浏览器打开（Markdown 只读状态下不会因此进入编辑），按下/松开 Ctrl 即时刷新；编辑器销毁后的迟到事件安全忽略。README 与功能全解加说明。RED：收集错误（模块不存在）；GREEN：`tests/test_link_click.py` `16 passed`，全量 `687 passed, 1 skipped`。阶段 A 代码全部完成，下一步：发布验证 → 升版本 0.1.1 → 安装。
- 发布 0.1.1：先运行 `bump_version.py`（0.1.0 → 0.1.1）并填写更新日志。第一次发布门在 `test_browser_page_address_enter_loads_local_file_and_reports_title` 超时（等网页标题 10s）：该测试新建隐私配置和 Chromium 渲染进程，单独运行实测 6.3–7.9s（本机其他程序占 CPU 约 82%），10s 余量不足，属环境负载导致的偶发失败而非功能问题；把这一处等待放宽到 30s（标题一到就返回）。
- 0.1.1 已发布（2026-10-16）：第二次发布门通过（Python `687 passed, 1 skipped`、前端 vitest、冻结构建、PTY 自检、全部 GUI smoke）；`Reader.exe` 文件版本 0.1.1，安装目录含 `LICENSE` 与 `THIRD_PARTY_NOTICES.md`。安装时发现 A4 的回归：`install_local.ps1` 内嵌 Python 仍传已删除的 `protected_claimer` 参数，注册失败（exe 已复制但关联与快捷方式未刷新）。补回归测试：把脚本里的内嵌 Python 按当前函数签名实际执行（用记录替身，不碰注册表）。RED：`TypeError: unexpected keyword argument 'protected_claimer'`；GREEN：打包/卫生 `37 passed`；修复只改安装脚本，未改 exe，直接安装已验证的构建：SHA256 `8FF1A89399F6C90A8647ED8BC8C3115A72FF115A1A5CC32D447372D59FD7B7EE`，桌面快捷方式已指向。安装版冒烟：冷启动 `.txt` 3.2–5.4s，已运行时再打开 1.5–1.6s（CPU 负载高），转发退出码 0。阶段 A 全部完成；规格与计划标为已实施。下一步：B1（未保存内容自动暂存与恢复）先写规格。
- B1 规格已定（2026-10-16，用户决定）：被注销/关机/崩溃打断后，下次启动像 Win11 记事本一样直接恢复未保存的标签，不询问；正常点 × 关闭仍询问「保存 / 不保存 / 取消」。规格：`docs/superpowers/specs/2026-10-16-draft-recovery-design.md`；计划：`docs/superpowers/plans/2026-10-16-draft-recovery.md`（5 任务）。
- B1 任务 1 完成：新模块 `reader/drafts.py`：`Draft`（文档编号、类型、路径、扩展名、标题、正文、编码/BOM/换行/是否无损、原文件修改时间与大小、暂存时间；`file_changed()` 判断原文件在暂存后是否被改或删）与 `DraftStore`（`<数据目录>\drafts\<编号>.json`，临时文件 + fsync + 原子替换；`load_all` 按时间排序并跳过损坏或版本不认识的文件且不删除；文档编号只允许字母数字 `_-`，防止路径穿越）。RED：收集错误；GREEN：`tests/test_drafts.py` `12 passed`（提交 `0ba19e5`）。
- B1 任务 2 完成：`MarkdownTextView` 与 `CodeTextView` 新增 `draft_state()`（类型、路径、扩展名、标题、正文、编码/BOM/换行/是否无损）与 `restore_draft(...)`（恢复后可编辑、标签带 `*`、路径与原编码换行保留，`Ctrl+S` 按原格式写回原文件；未命名草稿保留「未命名.md / 未命名.txt」标题）。RED：`6 failed`；GREEN：新测试 + 代码视图 + Markdown 文本视图 `41 passed`。
- B1 任务 3 完成：`MainWindow(drafts=DraftStore)`（默认不传则完全不暂存）。所有可编辑视图统一经 `_bind_editable_view` 绑定（顺带合并了三处重复的 Markdown 绑定代码）：文本变化且有未保存修改时加入待写集合，`DRAFT_SAVE_DELAY_MS`（1000ms）空闲后写入；窗口失去激活时立即写；保存成功、撤销回干净、关闭标签、正常关闭窗口时删除暂存；首次暂存时记录原文件修改时间与大小（保存后重置）。标签移到别的窗口前先把它的待写暂存写完，目标窗口重新绑定（文本变化槽与实时推送槽一样精确断开）。RED：`8 failed`；GREEN：`tests/test_window_drafts.py` `8 passed`，全量 `714 passed, 1 skipped`。

## 历史要点

由新到旧，括号内为规格文件（`docs/superpowers/specs/`）。

- 界面字体换成 Microsoft YaHei UI（`2026-10-15-ui-font-fast-start-design.md`）
- 快速打开 + 每次双击新窗口 + 标签可拖动（`2026-10-15-fast-launch-movable-tabs-design.md`）
- 同步远端更新
- Markdown 编辑/预览无缝切换（`2026-10-14-seamless-markdown-switch-design.md`）
- Markdown 切换延迟与欢迎页修复（`2026-10-14-markdown-switch-speed-design.md`）
- 终端 ghcp 修复（`2026-10-13-terminal-decrqm-fix-design.md`）
- 终端配色微调（`2026-10-13-terminal-theme-tuning-design.md`）
- 真终端（`2026-10-12-real-terminal-design.md`）
- Hex 视图对齐与自适应布局（`2026-10-12-hex-layout-design.md`）
- 代码页 Notepad 式底部状态栏 + Ctrl+J 转到行（`2026-10-12-status-bar-goto-design.md`）
- `.bin` 二进制（十六进制）查看器（`2026-10-12-binary-viewer-design.md`）
- PPTX 居中（`2026-10-12-pptx-centering-design.md`）
- 稳定本地安装 + 桌面快捷方式刷新（`2026-10-12-local-install-design.md`）
- 用户 2026-10-12 连续需求队列（`2026-10-12-browser-tab-design.md`、`2026-10-12-p2-find-replace-goto-design.md`、`2026-10-12-terminal-tab-design.md`、`2026-10-12-welcome-neutral-theme-design.md`）
- `+` 新建菜单与 Markdown 编辑/预览切换（`2026-10-12-new-tab-menu-design.md`）
- 记事本级文本编辑 P1（`2026-09-24-notepad-text-editing-design.md`）
- 三项连续 TDD 增量：Web 安全、C++ 后缀族、代码阅读体验（`2026-09-22-cpp-hpp-reading-design.md`、`2026-09-23-reader-hardening-and-code-reading-design.md`）
- 发布风险前置消除与自动验收基线（`2026-09-22-release-risk-burn-down-design.md`）
- TDD 与原子 Git 进度规则补强
- `.txt` 阅读 + 默认打开方式也是 Reader（`2026-09-21-txt-reading-design.md`）
- PPTX 表头文字看不见（`2026-08-25-pptx-visual-preview-design.md`）
- 冷启动 / 双击打开 / 打开与缩放黑闪（`2026-09-17-open-resize-snappiness-design.md`）
- setup.ps1 一次装好并冻结构建（`2026-09-11-setup-includes-freeze-design.md`）
- 编程语言阅读：`.c` / `.h`（`2026-09-11-c-header-reading-design.md`）
- 欢迎页路径查找可点进子目录（`2026-09-11-welcome-path-lookup-design.md`）
- 欢迎页右侧 Ctrl+F 路径查找（目录列出 / 文件打开）（`2026-09-11-welcome-path-lookup-design.md`）
- 图形页 Ctrl+滚轮缩放，并预览常见图片（`2026-09-11-graphic-zoom-images-design.md`）
- 打开 `.svg` 为图形预览，并把功能全解文档进 git（`2026-09-11-svg-reading-design.md`）
- 双击文档不再先闪欢迎页再关掉（`2026-09-10-startup-open-snappiness-design.md`）
- `.pdf` 默认打开方式也改成 Reader（`2026-09-10-default-app-associations-design.md`）
- 把文档默认打开方式切到 Reader（`2026-09-10-default-app-associations-design.md`）
- 文档 Ctrl+F 查找（记事本式）（`2026-09-10-document-find-design.md`）
- 代码文件阅读：JSON / YAML / XML + 行号（`2026-09-10-code-file-reading-design.md`）
- 启动空白等待 + 开文件闪一下 / 偶发卡住（`2026-09-10-startup-open-snappiness-design.md`）
- 纸色主题从欢迎页铺到打开的文件（`2026-09-10-paper-theme-documents-design.md`）
- 欢迎页最近文件卡片叠字
- 欢迎页视觉 + 任务栏改用蓝色 R（不再用窗口快照）（`2026-09-08-welcome-empty-launch-design.md`）
- 空启动欢迎页 + 任务栏蓝色 R（`2026-09-08-welcome-empty-launch-design.md`）
- 源码一键启动 + 0.1.0 说明（git 不含 exe）（`2026-09-08-source-setup-release-design.md`）
- 修复：原生 PDF 标签空白（`2026-09-07-pdf-reading-design.md`）
- 原生 PDF 阅读（Chrome 式 WebEngine）（`2026-09-07-pdf-reading-design.md`）
- Markdown 默认展示 + Ctrl+I/T 切换编辑（`2026-09-03-markdown-visual-default-design.md`）
- 冷启动首行空隙 + 任务栏图标（`2026-09-02-notepad-cold-open-icon-design.md`）
- 记事本间距与表面：+ 贴标签、柔和页色、窗口圆角、编辑区贴标题栏（`2026-09-02-notepad-spacing-surface-design.md`）
- 记事本标题栏表面：整条浅灰、选中标签与编辑区同白、按钮悬停变色（`2026-09-02-notepad-title-surface-design.md`）
- 记事本命中测试修复：按钮可点、可重复拖动、边框对准、灰标题/白内容（`2026-09-02-notepad-chrome-hittest-design.md`）
- 记事本式无缝表头：真正可拖动 + 标签/编辑区同色无分隔 + 隐藏状态栏（`2026-09-02-notepad-seamless-chrome-design.md`）
- Markdown 记事本编辑 + 表头拖动/高度/WebEngine 预热
- 热修：无边框标题栏导致白屏/拖放失效/任务栏异常
- 记事本式单行标题栏：去掉菜单/打开按钮，图标与标签同一行（`2026-09-01-notepad-titlebar-design.md`）
- Markdown 视觉预览：主题、离线 Mermaid、同目录双链开新标签（`2026-08-25-pptx-visual-preview-design.md`、`2026-08-28-markdown-visual-preview-design.md`）
- 更早（2026-08 至 09 初）：PPTX 本地视觉预览、Markdown 视觉预览（离线 Mermaid、双链）、记事本式单行标题栏与无缝表头、原生 PDF 阅读、单实例 IPC、首个冻结构建与 GUI 冒烟。

## 环境与经验

- 本机端点安全软件会拖慢每个新的 QtWebEngineProcess（约 1.2s）和新安装文件的首次启动（约 10s）；其他程序常占 40–90% CPU，计时请取多次交错运行的最小值。
- 测试里 `QTWEBENGINE_DISABLE_SANDBOX=1`（conftest 设置），冻结版仍用沙箱。
- 仓库文件换行混用 CRLF / LF，脚本改文件时保持原换行。
- 界面字体必须覆盖所显示的每个字符，样式表里只写一个字体（见 `2026-10-15-ui-font-fast-start-design.md`）。
- 不要改 `hit_test_local`、`begin_window_move`、`nativeEvent`。
- 资源管理器关联只注册「打开方式」候选，不改用户已选的默认应用、不打开 Windows 默认应用设置（远端 `abb2d6f` 的决定）。

## 接手检查清单

1. 读本页、`AGENTS.md` 和当前目标的规格/计划。
2. `git status` 与 `git log -15 --oneline`；有未推送提交先推送。
3. 改完更新本页「当前目标」，提交并推送。
