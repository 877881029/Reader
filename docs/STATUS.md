# Reader 项目状态（AI 接手必读）

最后更新：2026-10-14
Git：Markdown 切换修复最终状态 `ec4c396` 已同步；本边界提交「无缝编辑/预览」规格与计划。

## 当前目标

**Reader 高级化（参照 Tasker 新功能筛选）**（已确认，执行中）

- 用户需求（2026-10-16）：Tasker 新增了退出保存、发布仓库、版本号、设置页、数据安全等功能，先筛选哪些适合 Reader，列出开发列表，确认后逐项开发；用户要求开发列表用中文，并追求「打开任何文件都最快」。
- 不适合 Reader（不做）：全局快速记录快捷键；日志摘要、到点提醒；删除进回收站（Reader 不删除用户文件）；每日全量数据备份（文档属于用户自己）；桌面快捷方式（已具备）。
- 实测依据（2026-10-16，本机其他程序占 CPU 约 90%）：Reader 常驻时打开文本/代码/JSON 0.45–0.65s，Markdown 每次 2.3–2.8s（每个新窗口都要新起 Chromium 渲染进程并加载页面）；`Reader.exe` 自身启动并转发约 0.5–0.9s；常驻内存约 620 MB（含 Chromium）。因此加入 C4、C5 两项提速。本机有 VS 2022 Professional（MSVC），C5 可行。
- 开发列表（按顺序；每项：规格 → TDD → 发布验证 → 安装 → 推送）：

| 编号 | 阶段 | 内容 | 规模 | 状态 |
|---|---|---|---|---|
| A1 | 基础 | 版本号统一：只写在 `VERSION`，脚本每次加 1，规则写进流程文档 | 小 | 已完成 |
| A2 | 基础 | 依赖固定为当前测试通过的版本 | 小 | 待开始 |
| A3 | 基础 | 更新日志 + 许可证（含第三方许可说明） | 小 | 待开始 |
| A4 | 基础 | 删除无用代码；精简 STATUS；README 按实际功能重写并加截图；仓库简介和标签 | 小 | 待开始 |
| A5 | 基础 | 文本/代码视图里的网址可 Ctrl+点击打开 | 小 | 待开始 |
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

## 上一目标：界面字体换成 Microsoft YaHei UI（已完成）

**界面字体换成 Microsoft YaHei UI，去掉首屏字体回退卡顿**（已完成）

- 用户决定（2026-10-15）：「换，越快越好」。
- 实测根因：某个字符在当前字体里没有字形时，Qt 会在 GUI 线程上遍历本机全部约 364 个字体家族找替代，每次 1.2–5.8s。界面主字体 Segoe UI 没有中文；标题栏关闭 `✕`、还原 `❐` 两个符号在 Segoe UI 和 YaHei UI 里都没有（单 `✕` 实测 5.8s）；浏览器刷新 `⟳` 也没有（首次开 Browser 标签同样卡）。字形覆盖用 Windows GDI `GetGlyphIndicesW` 判断（Qt 的 `inFontUcs4` 会把回退字体算进去，`QRawFont` 读 YaHei 字体集合会误报，都不能用）。
- 方案：应用字体改为 Microsoft YaHei UI（英文字形来自 Segoe UI）；欢迎页同栈；标题栏最小化/最大化/关闭与浏览器前进/后退/刷新按钮改用含这些符号的 Segoe UI Symbol（字形不变）；文档渲染、代码编辑器、Hex 视图字体不动。
- 规格：`docs/superpowers/specs/2026-10-15-ui-font-fast-start-design.md`；计划：`docs/superpowers/plans/2026-10-15-ui-font-fast-start.md`（2 任务）。
- Task 1 完成：`reader/theme.py` 新增 `UI_FONT_FAMILY`（Microsoft YaHei UI）、`UI_FONT_STACK`（只含这一个字体）、`SYMBOL_FONT_FAMILY`（Segoe UI Symbol）；`ReaderApp` 把应用字体设为 YaHei UI（字号不变）；欢迎页同字体，大标题 "Reader" 只留 Segoe UI Variable Display；标题栏三个窗口按钮与浏览器前进/后退/刷新按钮改用 Segoe UI Symbol。实测中的第二个发现：CSS `font-family` 列表里每多一个字体，Qt 首次使用时要建回退链约 1.8–2.5s（即使第一个字体已覆盖所有字），所以界面样式表只写一个字体。新测试 `tests/test_ui_font.py`：GDI 字形覆盖辅助函数自检；应用字体为 YaHei UI；新窗口（含最大化后的还原符号）与浏览器标签里每个标签、按钮、标签页、菜单项文字在其自身主字体中都有字形；所有控件只解析到一个字体家族。RED：`3 failed`，补单字体测试再 `1 failed`；GREEN：`5 passed`，全量 `660 passed, 1 skipped`。
- 实测（开发环境，本机其他程序占 CPU 约 81%，取多次交错运行的最小值）：窗口从创建到显示 4.0–6.5s → 1.8–2.7s；`.txt` 冷启动最小值 11.7s → 8.8s。Chromium 启动变慢 1.5s → 3.3–4s：Qt WebEngine 初始化要调用 `QFont.defaultFamily()`，第一次调用会让 Qt 填满回退字体表（单测 2–3.5s），以前这笔开销提前花在了 Segoe UI 的中文回退搜索上，所以 `.md`/`.pptx` 等网页类文档总时间基本不变（窗口+Chromium 合计最小值 5.45s → 5.28s），但窗口先出现；文本/代码/图片/`.bin` 的 Chromium 预热已推迟，整段开销移出首屏。另外最大化（`❐`）和首次打开 Browser（`⟳`）不再各卡一次回退搜索。
- 已发布（2026-10-15）：`verify.ps1 -Release` 一次通过（Python `660 passed, 1 skipped`、前端 vitest、冻结构建、PTY 自检、全部 GUI smoke）；`install_local.ps1` 安装，SHA256 `2D6F8BCB5E9A28E0DD7D57DA4367016862FECE245790321AA10F843D20DA4EBC`。已安装版实测（CPU 负载约 40%）：冷启动打开 `.txt` 2.8–4.7s（上一版 4.0–5.5s，最初 14.1s）；已运行时再双击 0.9–1.1s。规格与计划已标 Implemented。

## 上一目标：快速打开 + 每次双击新窗口 + 标签可拖动（已完成）

**快速打开 + 每次双击新窗口 + 标签可在窗口间拖动**（已完成）

- 用户需求：像记事本一样从资源管理器快速打开；功能页能像记事本一样把标签单独拉出成窗口。用户决定：每次双击打开新窗口，共用一个后台进程，标签可在窗口间拖动。
- 实测（已安装构建）：冷启动打开 `.txt` 14.1s；已运行时再双击 5.0s 才显示，转发用的临时进程仅导入模块就要 6–8s。根因：每次启动都经 `reader.preview.pipeline` 导入 python-docx / python-pptx / openpyxl（含 numpy），开发环境占总导入 3.9s 中的 2.7s，冻结版因杀软逐个扫描 DLL 更慢；转发进程在检查是否已有实例前就导入整套 GUI。
- 规格：`docs/superpowers/specs/2026-10-15-fast-launch-movable-tabs-design.md`；计划：`docs/superpowers/plans/2026-10-15-fast-launch-movable-tabs.md`（6 任务）。
- Task 1 完成：`formats/docx.py`、`pptx.py`、`xlsx.py` 把 `python-docx` / `python-pptx` / `openpyxl` 改为在 `to_html` 内按需导入。新测试 `tests/test_startup_imports.py` 在新子进程中断言导入 `reader.preview.pipeline` 与 `reader.shell.window` 后 `sys.modules` 里没有 docx/pptx/openpyxl/numpy。RED：`1 failed`；GREEN：相关测试 `105 passed, 1 skipped`。`reader.__main__` 累计导入时间从 3.9s 降到 1.95s。
- Task 2 完成：新入口 `src/reader/launcher.py`（`reader.spec` 与 `pyproject` 脚本改指向它）。不导入 Qt，用 ctypes 直接连命名管道 `\\.\pipe\<server_name>`，发送与 `ipc.py` 相同的帧（4 字节大端长度 + JSON 绝对路径），阻塞读 `ACK`（独立线程，15s 超时），并对服务端进程 `AllowSetForegroundWindow` 以便新窗口能到前台。结果三态：`delivered` → 退出 0；`no-server`（管道不存在或帧没写完，服务端不会处理）→ 启动完整应用；`failed`（帧已送达但没有 ACK）→ 退出 2，不重开，避免重复打开。带 `-` 的参数（如 `--pty-selftest`）直接走完整应用。实例名提取到无 Qt 的 `reader/instance_name.py`，`ipc.server_name()` 仍读本模块 `SERVER_NAME`（测试依赖它隔离）。RED：收集错误；GREEN：launcher+ipc+packaging `61 passed`（含子进程断言转发时 `PySide6` 未导入、无服务端 <1s 返回、服务端不 ACK 时 `failed`）。开发环境实测转发 0.51s（旧路径 1.94s）。
- Task 3 完成：`ReaderApp._on_ipc_paths` 改为每次启动开新窗口：先把批次里已在任一（未关闭）窗口打开的文件切到对应标签（新 `MainWindow.show_open_path`），其余文件在一个新窗口中打开（先 `open_paths` 再 `show`，不闪欢迎页）；空批次（直接启动 Reader）打开新的欢迎窗口；全部已打开时不开新窗口，只激活拥有者窗口。删除按"活动窗口/激活历史"路由的 `_ipc_target_window` 与激活历史（不再使用），相关旧测试改为新语义。RED：`6 failed`；GREEN：全量 `635 passed, 1 skipped`。
- Task 4 完成：`MainWindow.move_document_to(did, target, index)` 把整个标签页（同一 `page` 控件、同一 document id 与 `_Document` 状态）交给另一窗口。源窗口先解除所有绑定到自己的处理：Markdown 实时推送槽（`_adopt_markdown_editor` 现在把槽存在编辑器上以便精确断开，并重置 `readerLivePush`）、编辑器 `dirty_changed`/`path_changed`、浏览器 `title_changed`、视觉事件，停掉并删除属于源窗口的推送计时器；未完成的预览请求与 Office 检测在共用 executor 时直接转交目标窗口（不重算），否则取消并在目标重启。目标窗口 `_adopt_document` 插入标签（保留标题/图标/提示）并重新绑定。源窗口被移空则直接关闭（文档已移走，不弹保存提示）。`_mark_preview_ready` 改为刷新控件当前所属窗口。标签右键菜单「移到新窗口」（只剩一个标签时禁用）与「关闭标签」，`move_tab_to_new_window`。RED：`6 failed, 2 errors`；GREEN：新增 7 例全过，全量 `642 passed, 1 skipped`。真实 WebEngine 验证：cmd 终端移到新窗口后会话不中断，输入 `echo moved-terminal-ok` 正常回显；Markdown 预览移动后正常显示。
- Task 5 完成：新 `reader/shell/tab_drag.py` 的 `ReaderTabBar`（`ChromeTabWidget` 用 `setTabBar` 换上）：按住标签纵向拖出标签条超过 `DETACH_MARGIN`（24px）进入"拖出"状态，显示半透明标签幻影跟随指针（不抢焦点、不接收输入），松开时发出 `detach_finished(index, 全局坐标)`；小幅移动、普通点击、未按在标签上的移动都不触发。窗口 `_finish_tab_drag` 决定落点：落在另一个 Reader 窗口上 → 移入该窗口（落在其标签上则插到那个位置）并激活；落在空白处 → 撕出成新窗口，新窗口放在指针处（指针位于其第一个标签上）；窗口只有一个标签时落在空白处 → 整个窗口跟随移动，落在别的窗口上 → 合并并关闭原窗口。`_window_at` 用 `QApplication.widgetAt`（遵循真实层叠顺序，指针下是别的程序就算空白）。RED：`ModuleNotFoundError` / `6 failed`；GREEN：拖动相关 10 例全过（含经 `QWindow` 真实路由的按下-拖出-松开），全量 `652 passed, 1 skipped`。注：曾尝试用 SendInput 在桌面上做真实鼠标拖动验证，因 Reader 窗口被其他程序窗口遮挡，注入的鼠标事件落到了别的窗口上，已停止这种验证方式（共享桌面不安全），改用 QWindow 级测试。
- Task 6 完成：冷启动剖析（开发环境）：导入约 2.7s；首个窗口构造 4.5–5.2s，其中约 3–3.6s 是 Qt 首次排版文字时初始化字体库（本机 364 个字体家族，枚举约 1.25s；界面主字体 Segoe UI 没有中文字形，首次排中文时回退搜索约 1.2–1.9s），与字体名无关，DirectWrite/GDI 引擎差别不大；用后台线程预热字体无效（PySide 枚举字体时不释放 GIL，与导入互相阻塞，总时长不变）。WebEngine 预热（约 1.9s，阻塞 GUI 线程）原先在有文件参数时以 0ms 触发，排在 `.txt` 显示之前。改为 `ReaderApp.new_window(warm_for=files)`：要打开的文件需要 Chromium（不是代码/文本、图片、SVG、`.bin`）时才立即预热，否则推迟 `DEFERRED_WARMUP_MS`（2s），让原生视图先显示。RED：`3 failed`；GREEN：main_launch+window+warmup+packaging `249 passed`。另补一例回归测试：双击后直接拖动标签也能拖出（QTabBar 本就把双击当按下，不是修复）。开发环境：冷启动 `.txt` 6.5–9.8s（原 9.3–17.6s），已运行时再打开 1.0–1.7s（其中 0.75s 是开发版 Python 解释器启动）。
- 已发布（2026-10-15）：`verify.ps1 -Release` 一次通过（Python `655 passed, 1 skipped`、各前端 vitest、冻结构建、PTY 自检、全部 GUI smoke 含 IPC 两批转发）；`install_local.ps1` 安装到 `%LOCALAPPDATA%\Programs\Reader`，SHA256 `D6F16E12C1AD01350F0B820C6C6CD5F48F5BA1E0F5AA4B8D2137D235AF2A1365`。冻结版实测（按 `document-ready` 日志计时）：冷启动打开 `.txt` 4.0–5.5s（改前 14.1s；新安装后第一次因杀软扫描新文件约 10s）；Reader 已运行时再双击 0.9–1.5s（改前 5.0s），启动器退出码 0。规格与计划已标 Implemented。
- 可选后续：界面主字体 Segoe UI 没有中文字形，冷启动首次排中文要回退搜索约 1.2–1.9s；若主字体改为含中文的 Microsoft YaHei UI（其英文字形源自 Segoe UI）可省掉这段，但会轻微改变界面字形，需用户确认后再做。

## 上一目标：同步远端更新（已完成）

**同步远端更新（2026-10-15）**（已完成）

- 远端 `main` 新增 1 个提交 `abb2d6f`「fix(reader): stop opening default apps settings on startup」（2026-10-14 19:45，作者 877881029），本地快进合并。
- 内容：启动时不再延迟 2.5s 调用 `claim_protected_defaults` 打开 Windows「默认应用」设置；`register_open_with` 不再删除各扩展名的 `UserChoice` / `UserChoiceLatest`（即不再清掉用户已选的默认应用），只注册「打开方式」候选；README 补充说明；相关测试改为断言不清除、不调度。
- 验证：associate / main_launch / packaging / settings_claim `78 passed`。
- 已发布（2026-10-15）：`verify.ps1 -Release` 一次通过（Python `625 passed, 1 skipped`、PPTX/MD/Terminal Web、冻结构建、PTY 自检、全部 GUI smoke）；`install_local.ps1` 安装到 `%LOCALAPPDATA%\Programs\Reader`，SHA256 `706E9D355B24FC691E84402C207CA482AAA6515559D910EA78D67F92D60FCFE4`，桌面快捷方式指向该处。已安装版本包含 `abb2d6f`。
- 遗留：`src/reader/shell/settings_claim.py` 已无调用方（仅剩模块与其测试）。

## 上一目标：Markdown 编辑/预览无缝切换（已完成）

**Markdown 编辑/预览无缝切换（对标 VS Code / Cursor / Typora）**（已完成）

- 用户需求：编辑与预览切换要无缝快速；用户决定：预览直接显示编辑器当前内容，不强制保存，新建文件也不弹另存为。
- 方案：每个 Markdown 标签同时保留编辑器与预览两个组件，切换只换布局不重建；预览改为接收编辑器文本推送（`liveSource`/`liveSourceChanged`）原地重渲染，不再读盘/重载；编辑时 150ms 防抖后台推送；进入编辑模式 300ms 后后台预建预览。
- 规格：`docs/superpowers/specs/2026-10-14-seamless-markdown-switch-design.md`；计划：`docs/superpowers/plans/2026-10-14-seamless-markdown-switch.md`（4 任务）。
- Task 1 完成：md-viewer `main.ts` 支持实时源——桥接 `hasLiveSource` 为真时直接渲染 `liveSource`（不 fetch 文件，未保存/不存在的文件也能预览），并订阅 `liveSourceChanged` 原地重渲染（保留滚动位置；每次重渲染经 `startViewer` 再次 `viewerReady`；串行号丢弃过期渲染）。`MarkdownBridge` 类型增加三项可选字段。重建 `assets/md-viewer`（哈希分块重命名）。RED：vitest `2 failed`；GREEN：md-viewer `23 passed`、typecheck、md 资产+卫生 `14 passed`。
- Task 2 完成：`MarkdownBridge` 增加 `hasLiveSource`/`liveSource`（constant 属性，页面连接时读取）与 `liveSourceChanged(str)` 信号；`MarkdownVisualView.set_source_text(text)`（回退模式下直接用文本渲染回退 HTML）、`is_usable()`/`is_ready()`、`rendered` 信号（启动后每次重渲染完成）；移除上一轮的 `reload()`/`can_reload()`；`fmt_md.to_visual_text(text)`。真实 WebEngine 测试：不存在的未命名源路径直接渲染推送文本，二次推送同页原地重渲染并发 `rendered`。RED：`2 failed`；GREEN：md_webengine/formats_md/md_view `30 passed`。
- Task 2 补充：页面无论是否以实时源启动都订阅 `liveSourceChanged`（从文件打开、先读盘渲染的预览也能接收编辑器推送）。RED：vitest `1 failed`；GREEN：md-viewer `24 passed`，重建 bundle，md 资产+WebEngine `11 passed`。
- Task 3 完成：窗口每个 Markdown 标签保留编辑器与预览——切到预览时编辑器标记 `readerKeepOnRetire`，被替换时隐藏保留（`_retire_widget`）而非销毁；切回编辑重装同一编辑器（光标/撤销/滚动保留）并把预览 `_keep_current_preview` 隐藏保留；切到预览不再保存（删除 `_ensure_markdown_saved`），直接把编辑器文本 `set_source_text` 推给保留/新建的预览；已就绪组件 `_arm_preview_ready` 立即显示。编辑时 150ms 防抖后台推送（`_schedule_markdown_push`）；新建/文本打开/切回编辑后 300ms 后台预建预览（`_precreate_markdown_preview`，计时器以窗口为上下文，窗口销毁不再回调——测试中捕获的真实缺陷）。未命名稿预览源路径为 `%TEMP%\reader-untitled\<名>`；另存为改路径后旧预览销毁并重建。保留的编辑器仍是文档可编辑视图（`*`、Ctrl+S、关闭提示在预览模式可用），Ctrl+H 仅在编辑可见时生效；关标签/关窗口销毁保留组件。移除上轮 parked/reload 路径。按新规格改写 3 个旧测试（强制保存、取消另存为回退、编辑器销毁断言）。RED：`6 failed`；GREEN：window/md_view/md_webengine/md_text_view/find/welcome_lookup `229 passed`。
- 实测（真实窗口 + 真实 WebEngine，已预热）：新建文件编辑→预览 14ms、预览→编辑 7ms、刚输入后立即切预览 4ms，后续往返 4–5ms，欢迎页 0 次，单标签 1 个预览；打开已有文件后编辑再立即切预览，预览显示未保存内容、磁盘文件未改、标签 `*doc.md`（截图）。
- Task 4 完成：README / 功能全解（`Ctrl+T` 不再强制保存、无缝切换说明）；`verify.ps1 -Release` 一次通过（Python `625 passed, 1 skipped`、PTY 自检、全部 GUI smoke）；`install_local.ps1` 安装，SHA256 `B61E22FF6014FDC408E9EF2BA4AA4B89A95DFB2CC9EFE64106CD5DCF1D96F455`；规格/计划 Implemented。已知代价：每个处于编辑状态的 Markdown 标签会在后台多占一个 Chromium 渲染进程。

## 上一目标：Markdown 切换延迟与欢迎页修复（已完成）

**修复：新建 Markdown 编辑/预览切换延迟大且退回欢迎页**（已完成）

- 复现（真实窗口，从欢迎页 `+` 新建文件）：首次编辑→预览 3.6s，其中 1.7s–3.6s 显示欢迎页；预览→编辑 0.1s；再次编辑→预览 1.8s，其中 0.2s–1.8s 显示欢迎页。
- 根因 1（退回欢迎页）：`_install_document_content` 安装新 `MarkdownVisualView` 后立即销毁编辑器，而视觉页在页面就绪前保持隐藏；标签内无可见内容，且窗口由欢迎页起步（`_welcome_allowed`），`_refresh_content_stack` 回落到欢迎页。
- 根因 2（延迟）：每次切换都新建 `MarkdownVisualView`（新 QWebEngineView + profile → 新 Chromium 渲染进程）。实测本机新视图即便加载极小页面也需 1.2–1.4s（进程启动，CrowdStrike/Defender 扫描 `QtWebEngineProcess` 加剧），而复用已有视图重新加载 Markdown 仅 0.17–0.4s；首次切换另含 WebEngine 预热未完成的开销。
- 规格：`docs/superpowers/specs/2026-10-14-markdown-switch-speed-design.md`；计划：`docs/superpowers/plans/2026-10-14-markdown-switch-speed.md`（3 任务）。
- Task 1 完成（不再退回欢迎页）：`_install_document_content` 在新内容未就绪时保留当前可见内容（标记 `readerRetiring`，编辑器设只读），`_mark_preview_ready`（就绪与渲染失败回退都经过）再移除；之后的安装/关标签照常销毁。旧测试 `test_markdown_mode_switch_tracks_and_toggles_mode` 的假视图从不发 ready，按新规则改为发 ready 后断言。RED：内容栈为欢迎页 `1 failed`；GREEN：window/md_view/md_text_view/find/welcome_lookup `222 passed`。
- Task 2 完成（复用预览视图）：`MarkdownVisualView` 新增 `source_path()` / `can_reload()` / `reload()`（同一 page/渲染进程重新加载 bundle 并重新读取已保存文件，再次发 `ready`）；`_restore_markdown_text` 切到编辑时把已就绪的预览视图隐藏「停放」到 `_Document.parked_visual`（移出布局、事件已解绑，连同 `parked_result`）；`switch_current_tab_to_visual` 在保存后优先 `_reuse_parked_markdown_visual`（源路径一致且可 reload 才复用，否则销毁后走原流程）；关标签/关窗口经 `_dispose_document_content` 销毁停放视图。修复中发现：`_restore_markdown_text` 新装的编辑器由 Qt 排队显示，短时 `isVisible()` 为 False，故「保留旧内容」改以 `readerPreviewReady` 判断而非可见性。测试辅助 `current_content` 跳过 retiring 内容，3 个旧测试的假视图补发 ready。RED：真实 WebEngine `reload` 与窗口复用 `2 failed`；GREEN：window/md_webengine/md_view/md_text_view/find/welcome_lookup `228 passed`。
- 实测（真实窗口，从欢迎页新建）：首次预览 2.0s（已预热；每个标签首次需新渲染进程），之后 编辑→预览 0.3–0.6s（原 1.8s）、预览→编辑 ~45ms，全过程欢迎页 0 次，同一标签仅 1 个预览视图。
- Task 3 完成：`verify.ps1 -Release` 一次通过（Python `623 passed, 1 skipped`、PTY 自检、全部 GUI smoke）；`install_local.ps1` 安装，SHA256 `1037FF93DA18A369CE2CA8E2CE8516CF1E623CCE85B8F602A9040BDF5A8F00C9`；规格/计划 Implemented。剩余：每个标签首次预览仍需约 2s 启动渲染进程（可后续预建备用视图优化）。

## 上一目标：终端 ghcp 修复（已完成）

**修复：终端里 `ghcp`（Copilot CLI）不显示**（已完成）

- 现象：用户 PowerShell 配置文件中的 `ghcp` 函数（启动 Copilot CLI 1.0.96）在 Copilot 右侧终端可用，在 Reader 终端只显示空白。
- 排查：CLI 实际已启动，约 8.5KB 界面输出已到达 Reader；页面报 `Uncaught ReferenceError: i is not defined`，xterm 停止处理输出。逐条喂序列定位到 DECRQM `ESC[?2026$p`。根因：Vite（esbuild）二次压缩 xterm.js 6.0.0 已压缩代码时，把 `requestMode` 中 `let r;(…)(r||={})` 改写成 `(void 0||(i={}))`，严格模式下给未声明变量赋值抛错。xterm 上游源码无误。
- 规格：`docs/superpowers/specs/2026-10-13-terminal-decrqm-fix-design.md`；计划：`docs/superpowers/plans/2026-10-13-terminal-decrqm-fix.md`。
- 修复：`web/terminal-viewer/vite.config.ts` 设 `build.minify: false`（避免二次压缩已压缩的 xterm.js），重建 bundle（JS 337KB→425KB）。回归测试：真实 WebEngine 中写入 DECRQM（2026/1049/12）须经桥接收到 `ESC[?N;S$y` 应答、模拟 Copilot CLI 启动序列后进入 alternate 缓冲且无 JS 错误；静态守卫 bundle 不含 `void 0||(i={})`。RED：`2 failed`；GREEN：terminal_page+assets `11 passed`；实测 Reader 终端运行 `ghcp` 完整显示 Copilot CLI 界面（截图）。
- 发布：`verify.ps1 -Release` 一次通过（Python `617 passed, 1 skipped`、PTY 自检、全部 GUI smoke）；`install_local.ps1` 安装，SHA256 `BF9B32EA9213D4D7F68C888F341FAB823D8E1FBF613D4C0942F5469983A9931F`；规格/计划 Implemented。

## 上一目标：终端配色微调（已完成）

**终端配色微调（对齐 Copilot 终端截图取色）**（已完成，含 15px 字号追加）

- 用户反馈：终端字体与背景配色希望更好看；对比截图中 Copilot 终端底色 `#f6f2ee`、文字 `#3d2b5a`（深紫墨）、光标 `#2848a9`，字形高约 17px（Reader 约 20px，偏大偏重）。
- 规格：`docs/superpowers/specs/2026-10-13-terminal-theme-tuning-design.md`；计划：`docs/superpowers/plans/2026-10-13-terminal-theme-tuning.md`（2 任务）。
- Task 1 完成：主题改为截图取色——底/光标反色 `#f6f2ee`、文字 `#3d2b5a`、ANSI black 同文字色、光标 `#2848a9`、选区 `#ddd5ee`；字体 Cascadia Mono 12px、normal、行高 1.25；页面/视口与 Qt page 背景 `#f6f2ee`，内边距上 10px 左 16px。重建 bundle。RED：vitest `1 failed`、WebEngine 背景断言；GREEN：vitest `5 passed`，terminal_page+assets `9 passed`；新截图取色背景 `#f6f2ee`、文字 `#3d2b5a` 与 Copilot 一致。
- Task 2 完成：`verify.ps1 -Release`：Python `615 passed, 1 skipped`、Web、冻结构建、PTY 自检通过；GUI smoke 首次在 IPC 阶段报「Second launch did not forward and exit」（两批路径均已送达，机器负载高，pytest 耗时 243s 对比平时 165s），对同一构建单独重跑 `smoke_windows.ps1` 全部通过，判定为负载下的时序抖动（已知风险，若再现需放宽二次启动退出等待）。`install_local.ps1` 安装，SHA256 `830306E8152F10DAD2E83CA4D39B1FA2DF989F42C6CB81EF207F8572E9AEFE11`；规格/计划 Implemented。
- 追加：用户要求终端字号 15px；规格追加 Amendment；vitest 断言先 RED（`1 failed`）后 GREEN（`5 passed`），重建 bundle，terminal_page+assets `9 passed`，截图确认；发布门一次通过（Python `615 passed, 1 skipped`、PTY 自检、全部 GUI smoke），安装 SHA256 `5FA3FB4CFB0D66C2F1A61536FCCC95A51C56B0AEA42A866522ACA80852763612`。

## 上一目标：真终端（已完成）

**真终端：ConPTY + xterm.js，Command Prompt / PowerShell，Copilot 主题配色**（已完成）

- 用户需求：Terminal 能力与 Copilot 右侧终端一致，包含 Command 与 PowerShell；配色与 Copilot 一致。管理员模式经确认放弃（普通权限 Reader 无法在自身标签内承载提权 shell），只做普通权限。
- 预研：`pywinpty 3.0.5` 在本机 ConPTY 可用，中文往返正确；ConPTY 启动会发终端查询（`ESC[c`），由 xterm.js 自动应答。
- 规格：`docs/superpowers/specs/2026-10-12-real-terminal-design.md`；计划：`docs/superpowers/plans/2026-10-12-real-terminal.md`（5 任务）。
- Task 1 完成：`reader/terminal/pty_session.py`：`SHELL_PROFILES`（PowerShell → `System32\WindowsPowerShell\v1.0\powershell.exe -NoLogo`，命令提示符 → `System32\cmd.exe`，均绝对路径）；`PtySession(QObject)` 以真实行列 spawn ConPTY，守护线程阻塞读，经 Queued 内部信号回到主线程发 `output`/`exited`；`write`/`resize`/`shutdown`（强制结束，关闭后不再发信号）；`DA1_RESPONSE` 常量供测试/自检应答 ConPTY 设备属性查询。`pyproject.toml` 新增 `pywinpty==3.0.5`。RED：收集错误；GREEN：`6 passed`（cmd 中文、起始目录、`mode con` 尺寸、PowerShell 求值、exit/shutdown）。
- Task 2 完成：新增 `web/terminal-viewer`（Vite + TS，`@xterm/xterm 6.0.0`、`@xterm/addon-fit 0.11.0`，MIT）：`theme.ts` Copilot 浅色主题（底 `#fbf9f5`、字/光标 `#1f1d1a`、选区 `#e9e3d9`、GitHub Light ANSI 16 色、Cascadia Mono 13px）；`terminal.ts::startTerminal` 打开并 fit、`ready(cols,rows)`、按键/二进制输入→`bridge.input`、尺寸变化→`bridge.resize`、shell 输出→`term.write`；有选区时 `Ctrl+C`/`Ctrl+Shift+C` 复制（经 `bridge.copyText`），无选区 `Ctrl+C` 交给 shell 中断，`Ctrl+V` 交浏览器原生粘贴；ResizeObserver 自动 fit；幂等 dispose。构建到 `assets/terminal-viewer`（notices + manifest，`.gitattributes` 已覆盖 LF）。Python 资产测试 `test_terminal_web_assets.py` 与卫生测试（新增 terminal bundle 跟踪）。RED：vitest 收集失败、卫生 `1 failed`；GREEN：vitest `5 passed`、typecheck、资产+卫生 `10 passed`。
- Task 3 完成：`shell/terminal_page.py` 重写为 WebEngine 版：独立 off-the-record profile + `_BundleOnlyInterceptor`（仅 terminal bundle 与 `qrc/data/blob`）；`TerminalBridge`（QWebChannel）`ready/input/resize/copyText`→Python，`output`→JS；JS 就绪后按真实行列启动 `PtySession`；shell 退出写入灰色「[进程已退出，按 Enter 重新启动]」，之后回车同配置重启；`shutdown` 结束 shell 并释放 page/profile。`readerTerminalText` 改为合并软换行行（长路径提示符换行导致测试误判时发现）。窗口 `add_terminal_tab(profile="powershell")` 改用新类，标题取配置名。旧管道控制台及其测试移除。RED：收集错误、软换行 `1 failed`；GREEN：terminal_page+web assets `9 passed`，终端相关 window/pty `16 passed`；截图确认 Copilot 浅色主题与中文。
- Task 4 完成：`+` → Terminal 改为子菜单（`tabNewSubmenu`，样式同主菜单）：PowerShell（`actionTerminalPowerShell`）、命令提示符（`actionTerminalCmd`，新增 `command` 线框图标）；标签标题为配置名。终端标签为当前页时禁用 `Ctrl+O/F/H/J(G)/N` 与保存/另存为/Markdown 编辑预览动作，使这些按键直达 shell，切回文档页恢复。RED：`4 failed`；GREEN：window+title_chrome `181 passed`；截图确认子菜单与 PowerShell 语法着色。
- 用户调整：cmd 配置显示名由「命令提示符」改为「Command Prompt」（菜单项与标签标题），规格/计划同步。RED：`2 failed`；GREEN：终端相关 `5 passed`。
- Task 5（打包）完成：`reader.spec` 收集 `winpty` 动态库 + `*.exe`（OpenConsole/winpty-agent）并打包 `assets/terminal-viewer`；`build_windows.ps1` / `verify.ps1` 在 Markdown 之后构建 terminal-viewer，构建脚本校验源/冻结 terminal bundle 清单并检查冻结 `_internal\winpty\OpenConsole.exe`、`conpty.dll`；新增 `reader/terminal/selftest.py` 与 `Reader.exe --pty-selftest <file>`（在创建 QApplication 前分支，cmd 经 ConPTY 回显标记，写 JSON 结果）；冻结 smoke 先跑 PTY 自检阶段（无 try/finally，严格清理）并在通过摘要中加入 `PTY-ready shell=cmd.exe`。RED：packaging `6 failed` + selftest 收集错误；GREEN：packaging `28 passed`、selftest+main_launch `25 passed`。
- Task 5（发布）完成：README/功能全解 5.9 重写；首次发布门因剪贴板测试触碰系统剪贴板被他进程占用失败（`OpenClipboard Failed`），测试改用假剪贴板后重跑通过：Python `615 passed, 1 skipped`、PPTX/MD/Terminal Web、冻结构建、`Reader PTY selftest: ok`（冻结 exe 内 ConPTY 实测）及全部 GUI smoke；`install_local.ps1` 安装，SHA256 `2878F06037A0A94C2EC57CDB40A43F865B1370FD9AED0CEB57D7E2EF23255BC6`；规格/计划 Implemented。

## 上一目标：Hex 视图对齐与自适应布局（已完成）

**Hex 视图：高亮与鼠标对齐 + 按窗口宽度自适应字号/列宽**（已完成）

- 用户反馈：高亮与鼠标不在同一字节上；一行太窄、右侧大量空白，希望调节字号和列宽改善观感。
- 根因：列位置用 `QFontMetrics.horizontalAdvance`（取整像素），而整行文本按小数字宽绘制，误差随列累积。
- 规格：`docs/superpowers/specs/2026-10-12-hex-layout-design.md`；计划：`docs/superpowers/plans/2026-10-12-hex-layout.md`（3 任务）。
- Task 1 完成：字宽改用 `QFontMetricsF` 浮点值；偏移、每个 hex 单元、每个 ASCII 字符和表头都按各自浮点坐标单独绘制，命中测试与高亮矩形（新 `highlight_rects()`）共用同一几何；hex 区按最近单元中心命中（单元间隙归最近单元，无死区）；第 7/8 字节之间加 1 字符半行间隔（`hex_unit_layout`，文本格式化函数不变）。RED：渲染像素测试（高亮边缘不得切到字形、内部必须有字形墨迹）Byte/Word/DWord 3 例 + 间隙命中 + 往返共 `5 failed`；GREEN：`23 passed`。
- Task 2 完成：自动字号——按视口宽度与行字符数（偏移+3+hex+3+16）计算像素字号，限制 13–22px，因小字号 hinting 偏宽时逐级回退直到放得下；达到上限后整块水平居中；最小字号仍放不下时保留横向滚动。手动缩放：`Ctrl+滚轮`、`Ctrl+=`/`Ctrl++`、`Ctrl+-`（10–32px，退出自动），`Ctrl+0` 恢复自动；分组切换/加载/窗口缩放都会重新布局。RED：`4 failed`；GREEN：hex `27 passed`，hex+bin 窗口 `31 passed`；截图确认高亮正落在鼠标所在字节、行铺满宽度。
- Task 3 完成：功能全解 5.10 与快捷键表同步；`verify.ps1 -Release` 通过（Python `597 passed, 1 skipped`、PPTX/MD Web、冻结构建与全部 smoke，未中断）；`install_local.ps1` 安装，SHA256 `F735F537D9CB928D61D64A22C8B415F33682D01F1FA9412D9828559E2D515179`；规格/计划 Implemented。

## 上一目标：代码页 Notepad 式底部状态栏 + Ctrl+J 转到行（已完成）

**代码页 Notepad 式底部状态栏 + Ctrl+J 转到行**（已完成，含二进制查看器发布）

- 用户需求：把代码页顶部工具栏（行号框/跳转/换行/A-/A+）改为窗口下边界的只读状态栏，显示「Ln xx, Col xx | Size xx pt | Type json」，不可点击，对齐 Notepad；跳转行改 `Ctrl+J`，交互与 `Ctrl+F` 一致。
- 规格：`docs/superpowers/specs/2026-10-12-status-bar-goto-design.md`；计划：`docs/superpowers/plans/2026-10-12-status-bar-goto.md`（3 任务）。字号改 `Ctrl+滚轮`/`Ctrl+=`/`Ctrl+-`/`Ctrl+0`，换行 `Alt+Z`。
- 二进制查看器 Task 4（发布门 + 安装）并入本目标 Task 3 一起执行（发布门在用户插入新需求时中止，未产生结论）。
- Task 1 完成：`CodeTextView` 去掉顶部工具栏（行号框/跳转/换行/A-/A+），改为底部只读状态栏 `codeStatusBar`：`Ln x, Col y` | `Size n pt` | `Type JSON`（细竖线分隔，标签 NoFocus + NoTextInteraction，无任何按钮/输入框），lossy 文件右侧显示只读提示；类型名映射 JSON/YAML/XML/C/C++/C/C++ Header/C++ Header/Plain text。字号改由编辑器内 `Ctrl+=`/`Ctrl++`/`Ctrl+-`/`Ctrl+0` 与 `Ctrl+滚轮`（8–24pt，同步 gutter/tab/状态栏），换行 `Alt+Z`（在 `CodeEditor.keyPressEvent`/`wheelEvent` 处理，`QShortcut` 在窗口未激活时不触发）。代码页安装时页面布局边距归零，状态栏贴窗口下边界与左边界。RED：code_view `12 failed`、贴边测试 `1 failed`；GREEN：window+code_view+find `207 passed`；截图确认。
- Task 2 完成：新增 `shell/goto_bar.py::GotoLineBar`（`goToLineBar`，与查找条同位置同样式：输入框占位「转到行（1–N）」、提示 `goToLineMessage`、×）；`actionGoToLine` 快捷键 `Ctrl+J`（保留 `Ctrl+G` 别名），回车跳转（限幅）并关闭、非数字提示「无效行号」、Esc/× 关闭；与查找/替换条互斥；适用于所有纯文本页（代码/TXT、Markdown 编辑），其他页忽略。移除旧 `QInputDialog` 弹窗与 `goto_line_prompt`。RED：`4 failed`；GREEN：window+find+find_replace `186 passed`；截图确认。
- Task 3：README / 功能全解同步（状态栏、`Ctrl+J`、字号/换行快捷键；顺带补回 P1 文档里被 PowerShell 吃掉的 `Ctrl+S`/`Ctrl+N` 反引号）。`verify.ps1 -Release` 通过：Python `587 passed, 1 skipped`、PPTX/MD Web、冻结构建与全部 smoke；`dist\Reader\Reader.exe` SHA256 `4687B4380E9782A1A8D8A1AFE5C988205D3E8BE387E843FA1355ADECBF8F5027`。
- 事故与修复：中止上一轮发布门（rel5）时 vite 刚清空 `assets/pptx-viewer`，其后规格提交 `10c0e41`（`git add -A`）误删了 `THIRD_PARTY_NOTICES.txt` 与 `manifest.sha256`。本次发布门重新生成，内容与 `d77da16` 逐字节一致，已恢复入库；新增卫生测试要求两个 Web bundle 的 notices/manifest/index 均被 git 跟踪（未暂存时 RED `1 failed`，恢复后 GREEN `6 passed`）。规则：中断发布门后提交前必须先跑快速门或检查 `git status` 中 `assets/` 删除。
- 已用 `install_local.ps1` 安装到 `%LOCALAPPDATA%\Programs\Reader`（SHA256 `4687B438…8F5027`），桌面快捷方式与 `.bin` 关联指向该处。规格/计划（状态栏、二进制查看器）标记 Implemented。

## 上一目标：`.bin` 二进制（十六进制）查看器（已完成，随状态栏一并发布）

**`.bin` 二进制（十六进制）查看器**

- 用户需求：快速打开 bin，每行 16 字节，Byte / Word / DWord 切换，右侧 ASCII 列，鼠标悬停时 hex 单元与 ASCII 双向联动高亮；大文件要快（流式或其他方式）。
- 假设（已在规格写明）：「bit/word/DW」理解为 Byte/Word/DWord 分组，Word/DWord 以小端值显示；仅新增 `.bin` 扩展名。
- 方案：`mmap` 只读映射 + 只绘制可见行的 `QAbstractScrollArea`，打开不读全文件。
- 规格：`docs/superpowers/specs/2026-10-12-binary-viewer-design.md`；计划：`docs/superpowers/plans/2026-10-12-binary-viewer.md`（4 任务）。
- Task 1 完成：`preview/hex_view.py` 纯函数 `format_hex_row`（Byte/Word/DWord，小端，残缺单元高位补 `--`）、`hex_unit_spans`、`format_ascii_row`（0x20–0x7E 原样，其余 `.`）、`offset_width`（≥8 位，按最大偏移加宽）；`ByteSource` 只读 `mmap`（空文件不映射；映射失败回退 seek/read），`close()` 释放映射与句柄。RED：收集错误；GREEN：`12 passed`。
- Task 2 完成：`HexView`（工具栏 Byte/Word/DWord 分段按钮 + 悬停信息「偏移 / 值（十进制）」+ 文件大小；内部 `_HexArea(QAbstractScrollArea)` 只格式化并绘制可见行，滚动范围按行，横向按字符；表头显示列偏移，ASCII 列前分隔线）；悬停 hex 单元或 ASCII 字符时两侧高亮同一单元（按当前分组对齐，末尾残缺单元截断）；`shutdown()` 释放映射后文件可删除。实测 1 GiB：`load_path` 2 ms、首帧 0.3 s。测试夹具改用 NTFS 稀疏文件（Python `truncate` 在 Windows 会写零，耗时 11 s）。RED：收集错误；GREEN：`18 passed`（5.6 s）；截图确认 DWord 悬停联动高亮。
- Task 3 完成：`.bin` 加入 `SUPPORTED_EXTENSIONS`、关联 `EXTENSIONS`、打开对话框过滤器与欢迎页徽章 `BIN`；`PreviewResult` 新增 `kind="binary"` 与 `binary_path`；`formats/binary.py::to_preview` 不读文件；pipeline 在 Office/视觉分支前处理；预览 worker 跳过缓存；`_default_viewer` 构建 `HexView`，关闭标签经 `_dispose_widget → shutdown` 释放映射。`test_welcome_lookup` 原用 `.bin` 当「不支持」样例，改为 `.exe`。RED：`6 failed`；GREEN：全量 Python `578 passed, 1 skipped`。

## 上一目标：PPTX 居中（已完成）

**PPTX 打开即居中、去掉画布滚动条、保留缩放快捷键**（已完成）

- 用户反馈：PPTX 默认打开时幻灯片不在中间（偏右下、被裁），每次都要调整；要求去掉上下左右滚动条，保留放大缩小快捷键。
- 根因：`.viewer-shell__host` 以原尺寸参与布局、仅用 `transform: scale()` 视觉缩小（原点在中心），网格居中与 `overflow: auto` 按未缩放尺寸计算，导致偏移和滚动条；fit 也未扣除 16px 内边距。
- 规格：`docs/superpowers/specs/2026-10-12-pptx-centering-design.md`；计划：`docs/superpowers/plans/2026-10-12-pptx-centering.md`（3 任务）。
- Task 1 完成：新增 `.viewer-shell__canvas` 包裹层（绝对定位，宽高=缩放后尺寸，`left/top = (舞台 - 缩放尺寸)/2`），host 以左上角为原点缩放；舞台 `overflow: hidden`、去掉网格居中与内边距；fit 扣除 `STAGE_GUTTER=16` 两侧留白；非 fit 模式下尺寸变化也重新居中。两个旧 fit 断言按新留白更新。RED：vitest `4 failed, 31 passed`；GREEN：`35 passed`，typecheck 通过。
- Task 2 完成：`Ctrl+=`/`Ctrl++` 放大、`Ctrl+-` 缩小、`Ctrl+0` 适合窗口、`Ctrl+滚轮` 缩放，均 `preventDefault` 阻止 Chromium 页面缩放；幻灯片大于舞台时可鼠标拖动或滚轮（Shift+滚轮横向）平移，平移限制在留白边界内，适合窗口时归零；可平移时光标为抓手。RED：`3 failed, 35 passed`；GREEN：`38 passed`，typecheck 通过。
- Task 3 完成：重建 `assets/pptx-viewer` bundle（`d77da16`）；真实 WebEngine 用用户的 `presentation_en.pptx` 截图确认首屏居中、四周留边、无滚动条；`verify.ps1 -Release` 通过（Python `555 passed, 1 skipped`、PPTX/MD Web、冻结构建与全部 smoke）；`install_local.ps1` 已安装到 `%LOCALAPPDATA%\Programs\Reader`，SHA256 `70A73B72AEFD7B79F1C14A53E24EB3F18821A1EAF7D17C128EDC60E89A4F1C75`，桌面快捷方式指向该处。功能全解同步；规格/计划 Implemented。本目标完成。

## 上一目标：稳定本地安装 + 桌面快捷方式刷新（已完成）

**稳定本地安装 + 桌面快捷方式刷新**（已完成）

- 用户反馈：桌面没看到最新 Reader.exe。根因：`Reader.lnk` 仍指向主检出旧构建 `C:\Research\AgentDevelopor\READER\dist`（9/21），`create_desktop_shortcut` 从不覆盖已有快捷方式；新构建只在临时 worktree `dist`。
- 已先行处置：最新发布构建（SHA256 `40A71EB4…5D6C71`）镜像到 `%LOCALAPPDATA%\Programs\Reader`，文件关联与桌面 `Reader.lnk` 已改指向该处。
- 规格：`docs/superpowers/specs/2026-10-12-local-install-design.md`；计划：`docs/superpowers/plans/2026-10-12-local-install.md`（2 任务）。
- Task 1 完成：`create_desktop_shortcut` 在已有快捷方式时，仅当旧目标与新 exe 都名为 `Reader.exe` 且路径不同（大小写/规范化比较）才刷新；指向其他程序、同一路径、或 `python.exe -m reader` 开发启动均不改动。RED：`1 failed, 21 passed`；GREEN：associate+main_launch `45 passed`。
- Task 2 完成：`scripts/install_local.ps1`（纯 ASCII）：检测目标处 Reader 是否在运行、`robocopy /MIR`（≥8 失败）、源/装后 exe SHA256 一致校验、用 dev Python 调 `register_open_with` + `create_desktop_shortcut(overwrite=True)`。packaging 合同+解析测试 RED `2 failed` → GREEN `23 passed`。已在本机运行：桌面 `Reader.lnk` 与 `Reader.Document` 打开命令均指向 `%LOCALAPPDATA%\Programs\Reader\Reader.exe`，SHA256 `40A71EB4C59F8DC9EC46293BBB707E49D7D737BC70A45E3145E2936ACF5D6C71`。README 增加安装步骤；规格/计划 Implemented。本目标完成。
- 注意：主检出 `C:\Research\AgentDevelopor\READER\dist` 中旧版 exe 仍在（不在本 worktree 内，未改动）；以后发布流程为 `verify.ps1 -Release` → `install_local.ps1`。

## 上一目标：用户 2026-10-12 连续需求队列

**用户 2026-10-12 连续需求队列（按顺序执行，每项独立规格/计划/TDD/提交）— 全部完成**

1. 主页（欢迎页）改为 Copilot 式简约中性配色，布局不变 — 已完成（发布门留到队列末尾统一执行）。规格 `docs/superpowers/specs/2026-10-12-welcome-neutral-theme-design.md`，计划 `docs/superpowers/plans/2026-10-12-welcome-neutral-theme.md`。墨色 `#1f1d1a` 主按钮、细线边框次按钮、`#fbf9f5` 卡片 + `#e6dfd4` 细线、`#f0ebe3` 灰色徽章、墨色强调条、去掉蓝色水印 R、全部改 Segoe UI；去除全部 cobalt。RED：新调色板测试 `1 failed`；GREEN：window/welcome_lookup/find `173 passed`（`test_welcome_lookup` 旧 CARD/LINE 断言按新规格更新）。截图确认。
2. P2：查找替换（`Ctrl+H`）、跳转指定行（`Ctrl+G`）— 已完成。规格 `docs/superpowers/specs/2026-10-12-p2-find-replace-goto-design.md`，计划 `docs/superpowers/plans/2026-10-12-p2-find-replace-goto.md`（4 任务）。
   - Task 1 完成：`find_support.replace_current`（仅当选区等于查询时替换，随后查找下一处，绕回）与 `replace_all`（先收集全部匹配再倒序替换，单一撤销步，替换文本含查询也不死循环），只读编辑器拒绝。RED：收集错误；GREEN：find_replace+find `11 passed`。
   - Task 2 完成：`Ctrl+H`（`actionReplace`）仅对可写文本页（`_writable_text_editor`：可编辑视图且非只读）生效，查找条显示「替换为」输入框与「替换 / 全部替换」；`Ctrl+F` 回到纯查找隐藏替换行；全部替换结果显示「已替换 N 处 / 未找到」；替换文本回车即替换；修改走编辑器使标签变 `*`。RED：`4 failed`；GREEN：window+find+find_replace `176 passed`。
   - Task 3 完成：`Ctrl+G`（`actionGoToLine`）对任意纯文本页（含只读代码/TXT、Markdown 编辑）弹「转到行」（`QInputDialog.getInt`，默认当前行，范围 1..行数，可注入 `goto_line_prompt`），光标移到行首并居中；取消不动；欢迎页/非文本页不弹。RED：`4 failed`；GREEN：window+find+find_replace+code_view `199 passed`。
   - Task 4 完成：README（顺带修复上一轮重复的半句）与功能全解查找章节、快捷键表同步；规格与计划标记 Implemented。P2 完成。
3. `+` 菜单 Browser 实现 — 已完成（Task 3 文档同步，规格/计划 Implemented）。规格 `docs/superpowers/specs/2026-10-12-browser-tab-design.md`，计划 `docs/superpowers/plans/2026-10-12-browser-tab.md`（3 任务）。
   - Task 1 完成：`browser_page.normalize_address`：http/https/file 原样；无空格且像域名 → `https://`，`localhost[:port]` → `http://`；其他（含 `javascript:`/`data:`）一律转 Bing 搜索；空输入返回 None。RED：收集错误；GREEN：`13 passed`。
   - Task 2 完成：`BrowserPage`（`browserPage`）：后退/前进/刷新 + 地址栏「输入网址或搜索」，独立 off-the-record `QWebEngineProfile`（不落盘、不共享离线查看器 profile，无 WebChannel），关闭时换 inert page 再释放 page/profile；`MainWindow.add_browser_tab` 通过通用 `_add_tool_tab` 建标签「浏览器」，标题跟随网页标题（>32 字截断，tooltip 全称），不进最近文件、关闭不提示；`Ctrl+F` 走既有 WebEngine 查找。菜单 Browser 启用，Terminal 仍禁用。RED：`4 failed`；GREEN：browser_page+window `185 passed`；截图确认工具栏高度 42px。
4. `+` 菜单 Terminal 实现 — 已完成。规格 `docs/superpowers/specs/2026-10-12-terminal-tab-design.md`，计划 `docs/superpowers/plans/2026-10-12-terminal-tab.md`（3 任务）。
   - Task 1 完成（`7e67498`）：`TerminalPage`（`terminalPage`）：`%SystemRoot%` 下绝对路径 PowerShell 5.1 经 `QProcess`（合并 stdout/stderr）`-NoLogo -NoProfile -Command -`；启动切 UTF-8 输出；**每条命令以 Base64(UTF-8) 经 `Invoke-Expression` 送入**（实测 stdin 按 OEM 代码页解码会把中文命令弄乱；测试原先因本地回显行误通过，已收紧为整行匹配后 RED→GREEN）；每条命令后发隐藏标记行 `\x1e$PWD` 更新提示符并从输出剔除；`cls/clear` 本地清屏，↑/↓ 历史，「重启」同目录重启，退出显示「[进程已退出]」，`shutdown` kill 并等待。RED：收集错误、中文输入 `1 failed`；GREEN：`6 passed`；人工验证变量持久、错误输出、中文。
   - Task 2 完成：菜单 Terminal 启用（`add_terminal_tab`），标签「终端」，起始目录为当前标签真实文件所在文件夹，否则用户主目录；复用 `_add_tool_tab`；关闭不提示且 kill 进程。`+` 菜单四项全部可用。RED：`3 failed`；GREEN：`3 passed`，全量 Python `549 passed, 1 skipped`。
   - Task 3 完成：README / 功能全解新增 5.9 终端并去掉「即将推出」；规格与计划 Implemented。
5. 队列统一发布门：`verify.ps1 -Release` 通过（Python `549 passed, 1 skipped`、PPTX/MD Web、冻结构建、PPTX/MD/TXT/C++/IPC smoke）。`dist\Reader\Reader.exe` SHA256 `40A71EB4C59F8DC9EC46293BBB707E49D7D737BC70A45E3145E2936ACF5D6C71`。
6. 下一步建议：P3 编码选择与换行转换（状态栏显示并可切换 UTF-8/GB18030、CRLF/LF）、P2 剩余的 `Ctrl+滚轮/Ctrl+0` 缩放与底部状态栏；终端可升级 ConPTY 以支持颜色与全屏程序。

## 上一目标：`+` 新建菜单与 Markdown 编辑/预览切换（已完成）

**`+` 新建菜单（Copilot 式图标下拉）与 Markdown 编辑/预览切换按钮**（已完成）

- 用户需求：`+` 改为下拉：新建文件（默认 md，同现状）、打开文件（支持格式选择框）、Browser、Terminal（后两项仅占位不实现）；每项带图标；Markdown 增加可见的编辑/预览切换按钮。
- 规格：`docs/superpowers/specs/2026-10-12-new-tab-menu-design.md`
- 计划：`docs/superpowers/plans/2026-10-12-new-tab-menu.md`（3 个顺序 TDD 任务）
- Task 1 完成：`+` 弹出 `tabNewMenu`（圆角卡片色，`src/reader/shell/icons.py` 运行时绘制线框图标，无资源文件）：新建文件（`add_untitled_markdown_tab`，同原行为）、打开文件（`_open_dialog` 支持格式过滤）、分隔线、Browser / Terminal（禁用，提示「即将推出」）。`actionNewTab`/`add_blank_tab` 不变。RED：`4 failed`；GREEN：window+title_chrome `160 passed`。
- Task 2 完成：标题栏右侧（窗口按钮左）新增分段切换 `markdownModeSwitch`「编辑 | 预览」，仅 Markdown 标签可见；选中段由 `_refresh_preview_actions` 按 `document.mode` 同步；点击复用 `actionMarkdownEdit` / `actionMarkdownPreview`（与 Ctrl+I / Ctrl+T 同语义，保存被取消时回弹到原选中段）；按钮登记为交互 chrome，不触发拖动窗口。RED：`4 failed`；GREEN：window+title_chrome `164 passed`。
- Task 3 完成：README 与功能全解同步（标题栏新建菜单、编辑/预览切换）；规格与计划标记 Implemented。`verify.ps1 -Release` 通过：PPTX Web `33 passed`、Markdown Web `21 passed`、Python `511 passed, 1 skipped`、冻结构建与 PPTX/MD/TXT/C++/IPC smoke 全通过。`dist\Reader\Reader.exe` SHA256 `BE3C05B2C7BB7F1F63CB11EACD356BF72D0193551733E03670C74F567B165EC6`。
- 本目标全部完成。下一步建议：P2（替换 `Ctrl+H`、`Ctrl+G` 跳行、`Ctrl+滚轮/Ctrl+0` 缩放、底部状态栏），或实现 Browser / Terminal 菜单项。

## 上一目标：记事本级文本编辑 P1（已完成）

**记事本级文本编辑 P1：TXT / MD / JSON / YAML / XML / C/C++ 统一可编辑保存**（计划已提交，执行中）

- 背景：对标 Windows 记事本，Reader 阅读能力已超越，但 TXT/代码只读是最大差距；另缺新建/另存为/未保存保护/编码保留。
- 用户批准 P1，并要求兼顾 txt、md、json 等全部文本格式。
- 规格：`docs/superpowers/specs/2026-09-24-notepad-text-editing-design.md`
- 后续阶段：P2 替换/Ctrl+G/缩放/状态栏；P3 编码选择与换行转换；P4 大文件、打印、会话恢复、启动速度。
- 计划：`docs/superpowers/plans/2026-09-24-notepad-text-editing.md`（6 个顺序 TDD 任务）
- Task 1 完成：`src/reader/text_io.py` 无损读写（UTF-8 / UTF-8 BOM / UTF-16 LE/BE BOM / GB18030，CRLF/LF/CR，空文件默认 UTF-8 CRLF，无法无损解码标记 lossy 并拒绝写入，临时文件 + `os.replace` 原子写）。RED：模块缺失导致收集失败；GREEN：`tests/test_text_io.py` 14 passed。
- Task 2 完成：`CodeTextView.load_path` 经 `text_io` 加载即可编辑（记事本式无独立编辑模式），加载后无撤销历史且不脏；`dirty_changed`/`path_changed`、`*name` 标题、`save`/`save_as`（无后缀沿用原后缀，后缀变化重设高亮）/`load_untitled`；lossy 文件只读并显示「只读：无法无损识别编码」。`load_text` 仍为只读预览。`_default_viewer` 对真实文件走 `load_path`；`formats/code.py` 预览文本也经 `text_io` 解码（GB18030 不再乱码）。RED：`11 failed, 9 passed`；GREEN：code_view+text_io `33 passed`，window+find `141 passed`，全量 Python `481 passed, 1 skipped`。
- Task 3 完成：`MarkdownTextView` 经 `text_io` 加载/保存，保留 UTF-8 BOM、GB18030、CRLF；新建 Markdown 保持原有 UTF-8 LF；lossy Markdown 永不进入编辑且拒绝保存；撤销回保存点恢复干净状态，加载后无撤销历史。`formats/md.py` 渲染同样经 `text_io` 解码。RED：md_text_view `4 failed, 4 passed`，GB18030 渲染 `1 failed`；GREEN：md_text_view `8 passed`，formats_md `3 passed`，window+find+md `149 passed`，全量 Python `485 passed, 1 skipped`。
- Task 4 完成：窗口统一 `_editable_view`（Markdown 文本模式或 `CodeTextView`），`Ctrl+S` 保存、`Ctrl+Shift+S` 另存为（代码/文本带 txt/json/yaml/xml/C++/md/全部 过滤器，Markdown 仍强制 `.md`）、`Ctrl+N` 新建 UTF-8 CRLF `未命名.txt`；代码页安装后接入 `dirty_changed/path_changed`，标签实时 `*name`，另存为更新 `document.path` 与最近文件；lossy 文件保存提示「只读文件无法保存」且不改字节。RED：新增 7 个窗口测试 `7 failed`；GREEN：window `143 passed`，全量 Python `493 passed, 1 skipped`。
- 环境风险（2026-10-10 新出现，基线同样复现）：本机 Chromium 沙箱导致真实 WebEngine 测试进程以 `-536870873` 崩溃；`QTWEBENGINE_DISABLE_SANDBOX=1` 下全部通过。产品代码未改；Task 6 发布门需确认冻结 EXE 是否受影响。
- Task 5 完成：`_confirm_discard` 在关闭标签与关闭窗口前对脏页弹出「保存 / 不保存 / 取消」（`MainWindow.unsaved_prompt` 可注入，默认 `QMessageBox`）；取消或另存为被取消都会中止关闭（`event.ignore()`），干净页不提示；打开文件不再复用已编辑的未命名草稿页（原有数据丢失路径）。测试 conftest 自动把真实对话框替换为 "discard"，避免 teardown 弹模态框；独立测试覆盖默认对话框文案与关闭即取消。RED：`5 failed, 4 errors`；GREEN：window/md_text/code `179 passed`，全量 `502 passed, 1 skipped`（`QTWEBENGINE_DISABLE_SANDBOX=1`）。
- Task 6 完成：README 与功能全解已同步为可编辑文本/代码页、`Ctrl+S`/`Ctrl+Shift+S`/`Ctrl+N`、编码换行保留与未保存保护；规格与计划标记 Implemented。`verify.ps1 -Release` 通过（PPTX/MD Web、Python、冻结构建、PPTX/MD/TXT/C++/IPC smoke），另在**开启 Chromium 沙箱**下单独复跑冻结 smoke 通过，确认产品不受本机沙箱问题影响。`dist\Reader\Reader.exe` SHA256 `E49E6C71B111DCFBA7D4C762D1CCDBB86E10623994A163D542BA64EC67465B98`。
- 风险消除：测试 conftest 在创建 QApplication 前 `setdefault QTWEBENGINE_DISABLE_SANDBOX=1`（仅测试进程；冻结 smoke 仍验证带沙箱路径）。RED：hygiene `1 failed`；GREEN：无需手工环境变量，快速门 `503 passed, 1 skipped`，`Reader fast verification passed`。
- P1 记事本级文本编辑全部完成。下一步建议：P2（替换 `Ctrl+H`、`Ctrl+G` 跳行、`Ctrl+滚轮/Ctrl+0` 缩放、底部状态栏 行列/编码/换行/缩放）。

## 上一目标：三项连续 TDD 增量：Web 安全、C++ 后缀族、代码阅读体验（已完成）

- 用户已批准依次实现 Web 依赖安全升级、C++ 后缀族和代码阅读体验。
- 规格：`docs/superpowers/specs/2026-09-23-reader-hardening-and-code-reading-design.md`
- 计划：`docs/superpowers/plans/2026-09-23-reader-hardening-and-code-reading.md`（5 个顺序 TDD 任务）
- 当前阶段：Task 1–5 全部完成，规格与计划状态为 Implemented。
- Task 1 RED：先把两个资产合同改为精确要求 Vite `6.4.3` / Vitest `3.2.6`，得到 `4 failed, 10 passed, 1 skipped`；两个目标失败证明 manifest/lockfile 仍是旧版本，另外两个失败证明已提交 bundle manifest 与待重建字节不一致。
- Task 1 GREEN：PPTX 与 Markdown 两棵依赖树均升级到 Vite `6.4.3` / Vitest `3.2.6`，保留 Node 18+ 契约；两个构建后静态 bundle 和 SHA256 manifest 已确定性重建。Vite 6 还暴露 Windows checkout 下生成 HTML/JS/CSS 的 EOL 漂移，`.gitattributes` 已将 Web HTML 与生成资产固定为 LF，提交前 `git diff --check` 通过。
- Task 1 审计：两个依赖树现在均为 2 moderate / 0 high / 0 critical。剩余项是同一 `@vitest/mocker` advisory 的直接/传递报告，仅存在于不进入 frozen Reader 的测试工具链；完全清零要求升级到需要 Node 20 的 Vitest 新主版本，因此本阶段不执行破坏 Node 18 契约的 `npm audit fix --force`。
- Task 1 验证：PPTX Web `33 passed`、Markdown Web `21 passed`，两套 typecheck/build 通过，Web 资产合同 `14 passed, 1 skipped`；Python `448 passed, 1 skipped`，最终输出 `Reader fast verification passed`。首次完整快速门在既有 PPTX WebEngine 生命周期测试发生 Windows 原生 access violation；该用例在全新进程 `1 passed`，第二次完整快速门全绿，未形成稳定回归。
- Task 2 RED：参数化 `.cc/.cxx/.hh/.hxx/.inl/.ipp` 的语言映射、高亮、sniff、打开决策、pipeline、当前用户关联、欢迎页徽章和打开筛选，聚焦套件得到 `14 failed, 219 passed`，所有失败均由六个后缀尚未接线导致。
- Task 2 GREEN：六个后缀加入 `C_FAMILY_SUFFIXES`、全局支持集合、pipeline、C-family highlighter、Open With、欢迎页徽章和文件筛选；统一映射到既有 `kind="code"` / `CHighlighter` / `代码预览`，未加入仅含 `.pdf/.txt` 的 `PROTECTED_EXTENSIONS`。README 与功能全解已同步。
- Task 2 验证：聚焦 `233 passed`；统一快速门 PPTX Web `33 passed`、Markdown Web `21 passed`、Python `454 passed, 1 skipped`，最终输出 `Reader fast verification passed`。
- Task 3 RED：先扩展冻结脚本静态合同，要求 `sample.cc/.cxx/.hh/.hxx/.inl/.ipp` 六个新夹具和最终 ready 摘要，得到 `1 failed, 20 passed`，证明 frozen C++ 阶段仍只覆盖 `.cpp/.hpp`。
- Task 3 GREEN：同一隔离 Reader 进程现在打开全部八个 C++ 文件；每个文件均通过共享 `Get-CppRecord` 验证 canonical path、精确 extension、`kind="code"` 和 `代码预览`，并继续复用独立 namespace/profile/temp、失败诊断和严格清理。脚本保持纯 ASCII，所有 helper 仍为顶层，精确两批 IPC 不变。
- Task 3 验证：`tests/test_packaging.py` 为 `21 passed`，Windows PowerShell parser 无语法错误；真实 frozen build/smoke 保留到 Task 5 唯一 release gate 同次执行。
- Task 4 RED：新增命名工具栏控件、跳转/位置、wrap/字号和重新加载状态四组行为测试，先得到 `4 failed, 6 passed`，失败均因现有 `CodeTextView` 只有编辑器、没有阅读控制。
- Task 4 GREEN：代码页新增自有紧凑工具栏；1-based 行号 spin 与「跳转」将目标限制在合法 block 并移动到行首；右侧实时显示「行 N，列 M」；「换行」在 `NoWrap/WidgetWidth` 间切换；`A-/A+` 在 8–24pt 内调整 12pt 默认等宽字体，同时刷新 tab stop、gutter geometry 和绘制。每个 `CodeTextView` 独立持有阅读状态，全局隐藏状态栏保持不变。
- Task 4 验证：聚焦 `10 passed`；code/find/window 回归 `151 passed`；统一快速门 PPTX Web `33 passed`、Markdown Web `21 passed`、Python `458 passed, 1 skipped`，最终输出 `Reader fast verification passed`。README 与功能全解已同步。
- Task 5 最终 release gate：唯一入口 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\verify.ps1 -Release -Python C:\venvs\reader-076ca44a\Scripts\python.exe` 同次运行退出 0；PPTX Web `33 passed`、Markdown Web `21 passed`、Python `458 passed, 1 skipped`，最终输出 `Reader release verification passed`。
- Frozen 验收：PPTX 4 slides、Markdown ready、TXT `kind=code extension=.txt`，以及 `.cpp/.hpp/.cc/.cxx/.hh/.hxx/.inl/.ipp` 全部逐项报告 canonical path、`kind="code"`、精确 extension 和 `代码预览`；IPC 保持精确两批、每批两个文件。
- 最终 release candidate：`dist\Reader\Reader.exe` 7460250 bytes，SHA256 `dc2ab2f4958007198a98540f2f6e63b63c13ef31011880c81e5a63fc9668a574`。PPTX manifest SHA256 `2cad803774cd8d1400f230f0fc25d976b16fb84459fe9d98459d26df40fd41d1`，Markdown manifest SHA256 `19f31e1c86cdf7267bbea6003e88c20e435371e92221239c60a10ff4a2f63890`，源码与 frozen manifest 分别一致。
- 最终清理：Reader 进程 0、Reader QtWebEngine 进程 0、smoke 临时根 0。两个 Web 依赖树继续为 2 moderate / 0 high / 0 critical，残余仅为 Node 20 才能兼容清零的 dev-only `@vitest/mocker`。
- C++ 范围：`.cc/.cxx/.hh/.hxx/.inl/.ipp` 打通格式、pipeline、高亮、sniff、关联、UI、文档与 frozen smoke。
- 阅读体验：代码视图内工具栏提供行跳转、实时行列、wrap 和 8–24pt 字号；不启用隐藏的全局状态栏，不引入编辑、保存、编译或 LSP。
- 最新完成项仍为 `.cpp` / `.hpp` C++ 源码阅读；产品代码与冻结验收保持稳定。
- 2026-09-23 完成全仓能力图谱盘点：扫描 285 个文件（185 code / 93 document / 7 image），结构与语义图合计 6,467 nodes、17,904 edges、215 communities。
- 图谱主干确认 `MainWindow`（157 edges）和 `PreviewResult`（134 edges）是桌面壳、格式 pipeline、视觉预览、查找、缓存、IPC 与质量门之间的核心桥梁。
- 图谱完整性警告：501 条 dangling endpoint、170 条 self-loop、无向构图折叠 2,206 条同端点边；主要来自打包 Web bundle 与 AST/语义 ID 粒度差异，不影响产品发布基线，但不能把社区数量直接解释为产品模块数量。
- `graphify-out/` 是本地分析生成物，已加入忽略规则，不进入产品提交。

### 最近完成：`.cpp` / `.hpp` C++ 源码阅读

- 规格：`docs/superpowers/specs/2026-09-22-cpp-hpp-reading-design.md`
- 计划：`docs/superpowers/plans/2026-09-22-cpp-hpp-reading.md`（2 个 TDD 任务）
- 范围：复用现有 C/H 的只读 code view、行号、复制、C-family 高亮和 `代码预览`；打通 sniff、pipeline、打开对话框、欢迎页徽章、当前用户 Open With 和 frozen smoke。
- 非目标：编辑/保存、编译/LSP、第三方解析器、其他 C++ 后缀、UCPD Settings 申索；不得修改 `hit_test_local`、`begin_window_move` 或 `nativeEvent`。
- Task 1 RED：只新增测试后，聚焦套件 `10 failed, 217 passed`；失败精确覆盖语言映射、C-family highlighter、sniff、`decide_open`、pipeline、当前用户关联、打开对话框和欢迎页徽章。
- Task 1 GREEN：`.cpp` / `.hpp` 进入 `CODE_SUFFIXES` 和所有发现/打开/关联/UI 清单，映射到现有 `kind="code"`、`CHighlighter` 和 `代码预览`；README 与功能全解同步，`PROTECTED_EXTENSIONS` 保持仅 `.pdf` / `.txt`。
- Task 1 验证：聚焦 `232 passed`；统一快速门禁成功，PPTX Web `33 passed`、Markdown Web `21 passed`、Python `448 passed, 1 skipped`，最终输出 `Reader fast verification passed`。
- Task 2 RED：冻结 smoke 合同先 `1 failed, 20 passed`，证明 C++ 阶段缺失。首次 release gate 又由项目卫生合同发现规格状态漂移（`1 failed, 447 passed, 1 skipped`）；真实冻结运行随后暴露两个 PowerShell helper 被误嵌套。修复为顶层函数，并增加“禁止缩进函数定义”的结构回归。
- Task 2 GREEN：独立 C++ 隔离进程同时打开 `sample.cpp` / `sample.hpp`，分别要求 canonical path、`kind="code"`、扩展名和 `代码预览`；纳入进程树、namespace lock、profile、temp root、失败诊断和最终清理，原 PPTX / Markdown / TXT / 精确两批 IPC 合同不变。
- 最终 release gate：`powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\verify.ps1 -Release -Python C:\venvs\reader-076ca44a\Scripts\python.exe` 同次运行退出 0；PPTX Web `33 passed`、Markdown Web `21 passed`、Python `448 passed, 1 skipped`，`.cpp` / `.hpp` 均报告格式明确 ready，最终输出 `Reader release verification passed`。
- 最终 release candidate：`dist\Reader\Reader.exe` 6022816 bytes，SHA256 `098c5bac4e1f0616902990ecc726b6ea2bc6a5b43380d55c5d6b0ed932214a3b`；PPTX manifest SHA256 `09b1943863816023107701663d5be4683dfdf7726d14e5a253c4862ef0b662b9`；Markdown manifest SHA256 `cfe5c3ef1abff0be8110c895a9a74914b84e09b51a97c831866424432029a27e`，源码与 frozen manifests 一致。
- 最终清理：Reader 进程 0、smoke QtWebEngine 进程 0、smoke 临时根 0；Web build 生成扰动已恢复。
- 当前边界：功能与冻结验收完成，Task 2 `deb9736` 已推送。

## 下一步

记事本级编辑 P1：执行计划 Task 1–6。

## 上一目标（已完成）

**发布风险前置消除与自动验收基线**（已完成）

- 规格：`docs/superpowers/specs/2026-09-22-release-risk-burn-down-design.md`
- 计划：`docs/superpowers/plans/2026-09-22-release-risk-burn-down.md`（Task 1–5 已完成；Task 6 是下一功能的独立规格边界）
- 用户确认：把潜在风险和进度风险加入下一步方案，提前消灭，并按完整方案逐步开始开发。
- 审计发现：未跟踪 `logs/bvm/bvm.log` 污染工作区；多份已完成规格头部仍显示 Draft/awaiting/implementing；项目元数据落后；缺少统一快速质量门和远端 CI；冻结 smoke 尚未覆盖最新 `.txt` 能力；启动性能缺少稳定里程碑记录。
- 执行顺序：项目卫生与状态一致性 → 统一质量门 → 冻结 TXT 验收 → Windows CI → 完整 release candidate 验证 → 下一功能。
- Task 1 RED：`tests/test_project_hygiene.py` 初次运行 `3 failed`，分别复现 logs 未忽略、包描述过时、5 份规格状态误导。
- Task 1 GREEN：加入 `/logs/` 忽略；包描述更新为 Windows multi-format document viewer；5 份已完成规格状态归一；聚焦测试 `3 passed`。深层 worktree 安装 PySide6 触发 Windows 路径长度限制，验证环境改用会话专属短路径 venv，不修改系统策略。
- Task 2 RED：`tests/test_packaging.py -k verify_script` 首次失败，证明统一门禁脚本缺失。
- Task 2 真实执行依次暴露并消除三个风险：Python 早于 Web 构建导致供应链/manifest 检查失败；PPTX Vite 构建会删除第三方声明和 manifest；Windows PowerShell 5.1 不接受 `Write-Host (if ...)`。门禁改为 Web 锁定安装、测试、类型检查、构建，恢复 PPTX 声明并确定性生成 manifest，再执行 Python 全量测试；发布模式额外串联冻结构建和 GUI smoke。
- Task 2 GREEN：聚焦回归 `1 passed`；`scripts\verify.ps1 -Python C:\venvs\reader-076ca44a\Scripts\python.exe` 成功，PPTX Web `33 passed`、Markdown Web `21 passed`、Python `439 passed, 1 skipped`，最终输出 `Reader fast verification passed` 且退出码 0。
- 已知供应链风险：两个 Web 锁定依赖树当前均报告 4 个审计项（2 moderate、1 high、1 critical）；不使用破坏兼容性的 `npm audit fix --force`，后续单独规格化评估和升级。
- Task 3 RED：文档 ready helper、内容安装后 TXT 遥测、冻结 TXT 独立阶段共 `4 failed`，分别证明 helper、接线和 smoke 阶段均不存在。
- Task 3 GREEN：`append_document_ready` 在未配置环境变量时无副作用；启用 smoke 时记录 canonical path、`kind="code"`、`extension=".txt"`、`status="文本预览"`，且只在当前文档内容成功安装后发出。冻结 smoke 新增独立 TXT 进程、命名空间、profile、临时根、精确事件等待和严格清理，原 IPC 两批约束不变。
- Task 3 验证：聚焦 `4 passed`；相关 smoke/window/packaging `165 passed`；PowerShell 语法解析通过；统一快速门禁成功，PPTX Web `33 passed`、Markdown Web `21 passed`、Python `442 passed, 1 skipped`。
- Task 4 RED：新增 workflow 合同测试首次因 `.github/workflows/quality.yml` 不存在而失败。
- Task 4 GREEN：新增最小权限 Windows workflow；push 到 main、pull request 或手动触发时使用 Python 3.12、Node 22、pip/npm 缓存、并发取消和 30 分钟超时，安装 `.[dev]` 后调用统一快速门禁；README 明确本地/远端同入口。
- Task 4 验证：项目卫生 `4 passed`。首次统一门禁遇到既有 WebEngine 网络阻断图片完成状态抖动，失败用例单独复跑通过；随后完整门禁成功，PPTX Web `33 passed`、Markdown Web `21 passed`、Python `443 passed, 1 skipped`。
- Task 4 首次远端 run `35713005104`：干净 runner 再次稳定复现同一 WebEngine 竞态（拦截器已记录全部阻断请求，但 `<img>` 的 complete 状态尚未异步更新）；runner 同时警告 checkout/setup action 的 Node 20 runtime 已弃用。
- Task 4 远端修复：测试在确认全部 URL 被拦截后继续等待图片进入 `complete && naturalWidth === 0`，本地连续 3 次通过；actions 升级到 checkout v5、setup-python v6、setup-node v5，合同测试先 RED 后 `4 passed`。
- Task 4 远端 GREEN：修复提交 `8dfcc42` 的 Windows quality run `35713742029` 在干净 runner 上全步骤通过，耗时 5m04s。
- Task 5 第一次 RED：`verify.ps1 -Python` 未把解释器传给 `build_windows.ps1`，冻结构建误用深 worktree 内 `.venv`，PySide6 安装触发 Windows 长路径失败。构建脚本新增显式 `-Python`，门禁通过 `sys.executable` 解析并贯通短路径解释器；合同测试先 `2 failed` 后通过。
- Task 5 第二次 RED：冻结 build 成功后，Windows PowerShell 5.1 按 ANSI 读取无 BOM UTF-8 smoke 脚本，中文状态字面量损坏并导致解析失败。smoke 脚本恢复纯 ASCII，以 Unicode codepoint 构造 `文本预览`；永久断言 `script.isascii()`，PowerShell 5.1 实际解析通过。
- Task 5 最终 GREEN：风险修复 `22add51` 推送后，唯一 release 入口 `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\verify.ps1 -Release -Python C:\venvs\reader-076ca44a\Scripts\python.exe` 在同一次运行内退出 0；PPTX Web `33 passed`、Markdown Web `21 passed`、Python `443 passed, 1 skipped`，冻结 build 成功，PPTX 4 slides、Markdown ready、TXT `kind=code extension=.txt status=文本预览`、IPC 精确两批均通过，最终输出 `Reader release verification passed`。
- 最终 release candidate：`dist\Reader\Reader.exe` 6022752 bytes，SHA256 `f1dd689eb42bcc05bf663f94f5408c7a4416eab1d63bae98d64f8e5991d8c204`；PPTX manifest SHA256 `09b1943863816023107701663d5be4683dfdf7726d14e5a253c4862ef0b662b9`；Markdown manifest SHA256 `cfe5c3ef1abff0be8110c895a9a74914b84e09b51a97c831866424432029a27e`，两个源码 bundle 与 frozen bundle 均逐字节 manifest 一致。
- 最终清理：Reader 进程 0、smoke QtWebEngine 进程 0、smoke 临时根 0；Web 构建引起的 tracked bundle 扰动已恢复，风险修复后的 `HEAD...origin/main` 为 `0 / 0`。
- 当前边界：Task 5 完成；发布风险闭环结束，可以单独启动 `.cpp` / `.hpp` 阅读规格。

## 上一目标（已完成）

**TDD 与原子 Git 进度规则补强**（已完成）

- 用户确认：所有开发必须遵循 TDD；为避免 Agent 上下文污染，目标、进度和状态必须及时写入 git；每次代码修改都必须形成可回退提交，方便新 chat 从仓库快速接手。
- 实现：`.cursor/rules/git-progress-handoff.mdc` 强制 RED → GREEN → REFACTOR、缺陷先写回归测试、每次代码修改验证后立即更新 STATUS 并原子提交、提交后才能开始下一项修改；`docs/superpowers/process.md` 同步明确开发节奏、提交边界和新会话接手顺序。
- 边界解释：“每次代码修改”指一个可独立验证、可独立回退的最小行为变化，不按每次保存文件机械拆分；对应 RED 测试和 GREEN 实现可以放在同一个原子提交，但必须记录 RED/GREEN 证据。
- 验证：仅规则与流程文档修改，无产品代码，无需运行产品测试。

## 上一目标（已完成）

**`.txt` 阅读 + 默认打开方式也是 Reader**（已完成）

- 规格：`docs/superpowers/specs/2026-09-21-txt-reading-design.md`
- 计划：`docs/superpowers/plans/2026-09-21-txt-reading.md`（2 个任务均已完成）
- 用户确认：增加 txt 支持，并把当前用户 `.txt` 默认打开方式改成 Reader。
- 实现：`.txt` 走现有 `kind="code"` 只读页（行号、可选中复制、无 JSON 高亮，状态「文本预览」）；加入 sniff / 打开对话框 / 欢迎页徽章；`associate.EXTENSIONS` 含 `.txt`；UCPD 锁住时与 PDF 一样走 Settings 申索。未改 `hit_test_local` / `begin_window_move` / `nativeEvent`
- 验证：全量 `435 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5998285 bytes`，SHA256 `700b0adb5bef447c0e49d6e1b288afa43267a672312f0ccd55d633aaac178bc4`

## 上一目标（已完成）

**PPTX 表头文字看不见**（已完成）

- 规格补充：`docs/superpowers/specs/2026-08-25-pptx-visual-preview-design.md` §11
- 计划：`docs/superpowers/plans/2026-09-21-pptx-table-header-contrast.md`（2 个任务均已完成）
- 用户确认：同一张幻灯片在 Reader 里表头底色在、文字几乎看不见。
- 根因：`pptx-viewer@0.2.2` 把 `font-family: "Calibri"` 写进 HTML `style="..."`，双引号截断属性，白色/青色 `color` 未生效。
- 实现：postinstall 补丁改用单引号；合成夹具 `table-header-contrast.pptx` 断言表头 span 仍是白色。未改 `hit_test_local` / `begin_window_move` / `nativeEvent`
- 验证：vitest 33 passed；全量 `429 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5998001 bytes`，SHA256 `e6bccd5747df95793a60178c4a85e03506e5eaced3322842a4b70486a33bedc5`

## 下一步

用 Reader 再打开 `GAIT_AI_Skills_Roadshow_EN.pptx`，确认表头 Dimension / Manual path / This skill (measured) 可见

## 上一目标（已完成）

**冷启动 / 双击打开 / 打开与缩放黑闪**（已完成）

- 规格：`docs/superpowers/specs/2026-09-17-open-resize-snappiness-design.md`
- 计划：`docs/superpowers/plans/2026-09-17-open-resize-snappiness.md`（3 个任务均已完成）
- 用户确认：开机后第一次开 Reader 太慢；不先开 Reader、用它打开文件会先闪欢迎页；开新文件或改窗口大小会偶发等待或整框变黑。一并优化。
- 实现：文件 argv 立刻预热且 `show` 前开路径；空启动预热 50ms；PDF Settings 申索延后 2.5s；视觉/WebEngine 未 ready 前不离开欢迎页（文件启动保持纸色标签）；PPTX `to_visual` 不再抽文本，回退时再提取；resize 合并 `_stretch_pane`。未改 `hit_test_local` / `begin_window_move` / `nativeEvent`
- 验证：全量 `429 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5998001 bytes`，SHA256 `1f6c3bb225e9de220c667eb69c72b1b5309fa8968f402612e93772143274d0ad`

## 下一步

重启后再空开一次 Reader；关掉后用资源管理器双击文件，确认不再先闪欢迎页；开新文件和拖窗口边看等待与黑闪是否减轻

## 上一目标（已完成）

**setup.ps1 一次装好并冻结构建**（已完成）

- 规格：`docs/superpowers/specs/2026-09-11-setup-includes-freeze-design.md`
- 计划：`docs/superpowers/plans/2026-09-11-setup-includes-freeze.md`（1 个任务已完成）
- 用户确认：把 `scripts\build_windows.ps1` 的构建放进 `setup.ps1`，一次性构造好。
- 实现：`setup.ps1` 在 pip 之后调用现有 `build_windows.ps1`；打出 exe 后启动 `dist\Reader\Reader.exe`；`-SkipBuild` 只跑源码；`-SkipLaunch` 仍不弹窗。未改 `hit_test_local` / `begin_window_move` / `nativeEvent`
- 验证：全量 `419 passed, 1 skipped`；未重打 exe（产品二进制未改）

## 下一步

同事 clone 后跑 `scripts\setup.ps1`（需 Node 18+）一次得到冻结 exe；只要源码则加 `-SkipBuild`

## 上一目标（已完成）

**编程语言阅读：`.c` / `.h`**

- 规格：`docs/superpowers/specs/2026-09-11-c-header-reading-design.md`
- 计划：`docs/superpowers/plans/2026-09-11-c-header-reading.md`（2 个任务均已完成）
- 用户确认：为 Reader 增加编程语言阅读支持，先加 `.h` 和 `.c`。
- 实现：`.c` / `.h` 走现有 `kind="code"` 只读页；共享 `CHighlighter`；行号、可选中复制；加入 sniff / 打开对话框 / 默认打开方式。未改 `hit_test_local` / `begin_window_move` / `nativeEvent`
- 验证：全量 `419 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5996580 bytes`，SHA256 `2f6e91a1aa11e31c29bd0eaeec197e33da24313ecf53c0dca69bfddceb6cd556`

## 下一步

用户双击 `.c` / `.h` 看行号与高亮是否够用；需要 `.cpp` 或其他语言再开规格

## 上一目标（已完成）

**欢迎页路径查找可点进子目录**

- 规格：`docs/superpowers/specs/2026-09-11-welcome-path-lookup-design.md`
- 计划：`docs/superpowers/plans/2026-09-11-welcome-path-lookup.md`（Task 3 已完成）
- 用户确认：列表里也要有目录；点目录就把查找框路径递进一层，继续陈列新目录内容。
- 实现：一层列出非隐藏子目录（徽章 `DIR`）再列出 `SUPPORTED_EXTENSIONS`；点击目录更新路径框并 relist，不打开标签。点文件仍打开。未改 `hit_test_local` / `begin_window_move` / `nativeEvent`
- 验证：全量 `415 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5995093 bytes`，SHA256 `d4b90a1f6fae2de42a815d7ef0824db4facac1ef9e470441c341dccb18c133c1`

## 下一步

用户在欢迎页 Ctrl+F 进目录，点子目录确认路径框递进并列出下一层

## 上一目标（已完成）

**欢迎页右侧 Ctrl+F 路径查找（目录列出 / 文件打开）**

- 规格：`docs/superpowers/specs/2026-09-11-welcome-path-lookup-design.md`
- 计划：`docs/superpowers/plans/2026-09-11-welcome-path-lookup.md`（2 个任务均已完成）
- 用户确认：在「最近打开」那一行加隐藏查找框；Ctrl+F 打开；输入目录回车列出该目录文件（卡片同最近打开）；输入文件回车即打开。只改右侧，左侧和色调不动。
- 实现：欢迎页 Ctrl+F 只显示右侧路径框，不弹出窗口查找条；目录列出 `SUPPORTED_EXTENSIONS`；Esc 回到最近打开。未改 `hit_test_local` / `begin_window_move` / `nativeEvent`
- 验证：全量 `414 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5994438 bytes`，SHA256 `cc2182f5a9e9a0579a18d516d6990421d5376c54c23b81bde6c15cd24c6627e2`

## 下一步

用户在欢迎页按 Ctrl+F，试目录列出和文件打开

## 上一目标（已完成）

**图形页 Ctrl+滚轮缩放，并预览常见图片**

- 规格：`docs/superpowers/specs/2026-09-11-graphic-zoom-images-design.md`
- 计划：`docs/superpowers/plans/2026-09-11-graphic-zoom-images.md`（2 个任务均已完成）
- 用户确认：缩放不要明面控件，只用 Ctrl+滚轮放大缩小；同时能预览图片。先做出来再改。
- 实现：SVG/图片共用 `GraphicView` 纸色画布；无按钮/滑条/百分比；`Ctrl+滚轮` 对准光标缩放；放大后可拖动；`.png` `.jpg` `.jpeg` `.gif` `.webp` `.bmp` 开标签。未改 `hit_test_local` / `begin_window_move` / `nativeEvent`
- 验证：全量 `409 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5991896 bytes`，SHA256 `6ccdf2e1c652dc99a59e9f8d5a9076ddf516530b4ecdbff4b62f678d06fc8bdf`

## 下一步

用户打开 `.svg` / `.png` 用 Ctrl+滚轮试缩放；需要 TIFF/HEIC 或可见缩放读数再开规格

## 上一目标（已完成）

**打开 `.svg` 为图形预览，并把功能全解文档进 git**

- 规格：`docs/superpowers/specs/2026-09-11-svg-reading-design.md`
- 计划：`docs/superpowers/plans/2026-09-11-svg-reading.md`（2 个任务均已完成）
- 用户确认：上一轮代码已在远端；把最新功能 md 同步到远端；增加支持 SVG。先做出来再改。
- 实现：`.svg` 走 `QSvgRenderer` 纸色适窗图形页（不执行脚本）；`associate.EXTENSIONS` 含 `.svg`；功能说明写入 `docs/Reader功能全解.md`（桌面副本已覆盖）。未改 `hit_test_local` / `begin_window_move` / `nativeEvent`
- 验证：全量 `396 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5985902 bytes`，SHA256 `095774d5793779fcb851d86b038fb44ee27bf0d887439652ba2d12330e5839ab`

## 下一步

用户双击 `.svg` 看图形预览是否够用；需要缩放按钮或其它图片格式再开规格

## 上一目标（已完成）

**双击文档不再先闪欢迎页再关掉**

- 规格：`docs/superpowers/specs/2026-09-10-startup-open-snappiness-design.md`（补 argv 冷启动）
- 计划：`docs/superpowers/plans/2026-09-10-startup-open-snappiness.md`（Task 4 已完成）
- 用户确认：双击桌面 `.md` 会先出 Reader 欢迎页，然后关掉，再出文件标签。要纠正。
- 根因：`new_window()` 先 `show()` 欢迎页；`open_paths` 时标签只有「正在加载…」，内容栈故意留在欢迎页；Markdown 视觉预览好了才切到 tabs，看起来像关窗再开。
- 实现：带文件启动时先隐藏创建窗口、`open_paths`、再 `show()`；尚未展示过欢迎页时 loading 也走 tabs 栈。从欢迎页打开文件仍等真实预览再切走。未改 `hit_test_local` / `begin_window_move` / `nativeEvent`
- 验证：全量 `389 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5982837 bytes`，SHA256 `d529b24cd17641c0daaf41cd063c3a1933e5142e86bed878147bed3eb553bb28`

## 下一步

用户关掉 Reader 后双击桌面 `Reader功能全解.md`，确认不再先闪欢迎页

## 上一目标（已完成）

**`.pdf` 默认打开方式也改成 Reader**

- 规格：`docs/superpowers/specs/2026-09-10-default-app-associations-design.md`
- 计划：`docs/superpowers/plans/2026-09-10-default-app-associations.md`（3 个任务均已完成）
- 用户确认：不要停在「设置里手动改 PDF」。UCPD 锁死 `.pdf` 的 UserChoice，程序不能静默改注册表。
- 实现：`register_open_with` 之后，若 AssocQueryString 显示 `.pdf` 还不是 Reader，则打开 `ms-settings:defaultapps?registeredAppUser=Reader`，Invoke `.pdf` 行，让 SystemSettings 写入带 Hash 的 UserChoice，然后关掉设置。已经是 Reader 则不弹窗。不伪造 Hash，不关 UCPD。
- 本机当前：所有 Reader 后缀（含 `.pdf`）AssocQueryString 友好名都是 Reader；`.pdf` UserChoice `ProgId=Reader.Document`
- 未改 `hit_test_local` / `begin_window_move` / `nativeEvent`
- 验证：全量 `386 passed, 1 skipped`；`tests/test_settings_claim.py` 3 passed；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5982568 bytes`，SHA256 `5ce54edd908fff4c9ab6dd5f9407e38b3de7f395f50057f465163dd6b67c8ed8`

## 下一步

用户双击 `.pdf` 确认进 Reader 而不是 Acrobat；其它文档类型继续用 Reader

## 上一目标（已完成）

**把文档默认打开方式切到 Reader**

- 规格：`docs/superpowers/specs/2026-09-10-default-app-associations-design.md`
- 计划：`docs/superpowers/plans/2026-09-10-default-app-associations.md`（Task 1–2 已完成）
- 用户确认：电脑里文档类文件现在默认用 Word，要改成 Reader。先做出来再改。
- 实现：启动时 `register_open_with` 把 HKCU `Classes\<ext>` 设为 `Reader.Document`，写入 Default Apps Capabilities，清掉可删的 `UserChoice`，并把 `FileExts` 的 OpenWithList 指到 `Reader.exe`。
- 未改 `hit_test_local` / `begin_window_move` / `nativeEvent`
- 验证：当时全量 `382 passed, 1 skipped`；docx/md/pptx/xlsx/json/yaml/yml/xml = Reader；`.pdf` 当时仍被 UCPD 锁在 Acrobat（已由当前目标接手）
- 最终 `dist/Reader/Reader.exe`：`5978879 bytes`，SHA256 `19cc012cd1e70620c05be8724f2a40caf4fbd5cca5ef80d819db8485b186d59a`

## 上一目标（已完成）

**文档 Ctrl+F 查找（记事本式）**

- 规格：`docs/superpowers/specs/2026-09-10-document-find-design.md`
- 计划：`docs/superpowers/plans/2026-09-10-document-find.md`（2 个任务均已完成）
- 用户确认：对文档类文件增加 Ctrl+F，像记事本一样。先做出来再改。
- 实现：标题栏下查找条；`Ctrl+F` 打开，Enter / F3 下一个，Shift+Enter / Shift+F3 上一个，Esc 关闭；区分大小写；绕回；`未找到`。纯文本走 `QPlainTextEdit.find`，HTML/MD 视觉/PPTX/PDF 走 `QWebEnginePage.findText`。欢迎页不响应。未改 `hit_test_local` / `begin_window_move` / `nativeEvent`
- 验证：`tests/test_find.py` 5 passed；全量 382 项中 WebEngine 抖动用例复跑通过（`381 passed, 1 skipped` + 复跑 1 passed）；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5977995 bytes`，SHA256 `5cb9d34a6b41fddb887ccda676f96264fca22e4062760b4c1e4c2251cf6d74bc`

## 下一步

用户打开 `.md` / `.docx` / `.pptx` / `.pdf` / `.json`，按 Ctrl+F 试查找；需要替换（Ctrl+H）再开规格

## 上一目标（已完成）

**代码文件阅读：JSON / YAML / XML + 行号**

- 规格：`docs/superpowers/specs/2026-09-10-code-file-reading-design.md`
- 计划：`docs/superpowers/plans/2026-09-10-code-file-reading.md`（2 个任务均已完成）
- 用户确认：先支持 yaml/json/xml/yml；左侧 VS Code 式行号；有语法高亮更好。只读阅读。
- 实现：`.json` / `.yaml` / `.yml` / `.xml` 走 `kind="code"`；`CodeTextView` 只读、左侧行号、不折行；`QSyntaxHighlighter` 轻量上色；不走预览缓存；Office/视觉模式不适用
- 未改 `hit_test_local` / `begin_window_move` / `nativeEvent`
- 验证：全量 `377 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5969940 bytes`，SHA256 `01af84aa7e571e97d12b1415d47c8517a9869e761ed3a0b77662d08a3c48bcbb`

## 下一步

用户从桌面图标打开 `.json` / `.yaml` / `.yml` / `.xml`，看行号与高亮是否够用；需要更多语言再开规格

## 上一目标（已完成）

**启动空白等待 + 开文件闪一下 / 偶发卡住**

- 规格：`docs/superpowers/specs/2026-09-10-startup-open-snappiness-design.md`
- 计划：`docs/superpowers/plans/2026-09-10-startup-open-snappiness.md`
- 用户确认：桌面图标 3–4s 才出界面；开新文件像窗口关了再开；偶发渲染很久。先做出来再改。
- 根因：`show()` 之后、`exec()` 之前同步写注册表/快捷方式，首帧无法绘制；WebEngine 预热立刻 `processEvents` 且预热完就拆掉 Chromium；开文件时欢迎页被换成空的「正在加载…」，再创建第一个 `QWebEngineView` 会闪原生 HWND
- 修复：壳集成延后到事件循环；`AA_ShareOpenGLContexts`；构造时 `winId()` 就设图标；隐藏的 WebEngine 视图保活；欢迎页等到真正预览内容再切走。未改 `hit_test_local` / `begin_window_move` / `nativeEvent`
- 验证：全量 `364 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5958790 bytes`，SHA256 `02e12690097591f7483e81bb8880485e5a8f576376eb3f4998f7db449f08ea29`

## 下一步

用户从桌面图标冷启动，再从欢迎页打开 `.md` / `.pptx` 看空白等待和闪一下是否还在

## 背景

Reader 是 Windows 桌面文档查看器（PySide6）。v1 已支持 `.docx` / `.pptx` / `.xlsx` / `.md` / `.txt` / `.pdf` / `.json` / `.yaml` / `.yml` / `.xml` / `.c` / `.h` / `.svg` / `.png` / `.jpg` / `.jpeg` / `.gif` / `.webp` / `.bmp`，标签页、内置预览优先、可选 Office COM 高保真、单实例 IPC、PyInstaller onedir `dist/Reader/Reader.exe`、透明蓝色 R 图标。

内置 PPTX 默认已切换为本地 WebEngine 视觉渲染；`python-pptx` 文本 HTML 保留为手动模式和视觉失败回退。

## 上一目标（已完成）

**纸色主题从欢迎页铺到打开的文件**

- 规格：`docs/superpowers/specs/2026-09-10-paper-theme-documents-design.md`
- 计划：`docs/superpowers/plans/2026-09-10-paper-theme-documents.md`
- 用户确认：欢迎页主题色拓展到打开后的各类文件；不要冷白/记事本灰跳变
- Token：`src/reader/theme.py`（PAPER `#f4efe6`、CHROME `#ebe4d8`、COBALT `#2563eb`）接到窗口根、标题栏、MD 编辑器、HTML 回退、md/pptx 视觉壳；幻灯片画布与 PDF 页内容保持原稿
- 未改 `hit_test_local` / `begin_window_move` / `nativeEvent`
- 验证：全量 `363 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5957381 bytes`，SHA256 `59f010fc5284da8d1da8ed0ba8b140de3b1140addd811d5f7a32b52dc8183590`

## 下一步

用户打开 `.md` / `.docx` / `.pptx` / `.xlsx` / `.pdf`，看是否还从欢迎页跳到冷白或深色壳

## 上一目标（已完成）

**欢迎页最近文件卡片叠字**

- 用户截图：徽章/文件名/路径互相覆盖（`visual-document.md` 的 `vi` 露在 MD 徽章旁）
- 根因：`QListWidgetItem` 仍写入文件名，列表会再画一遍 item 文本，叠在自定义行控件上
- 修复：item 不再设文本，文件名只画在行控件里；长路径中间省略
- 验证：全量 `359 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 未改 `hit_test_local` / `begin_window_move` / `nativeEvent`
- 最终 `dist/Reader/Reader.exe`：`5955800 bytes`，SHA256 `24222257bddd0d7e349ab05fb4e94cb76a334a4e16de4d9d8339fbc4ab339b19`

## 下一步

用户再看最近打开卡片是否还叠字

## 上一目标（已完成）

**欢迎页视觉 + 任务栏改用蓝色 R（不再用窗口快照）**

- 规格补记：`docs/superpowers/specs/2026-09-08-welcome-empty-launch-design.md` §6
- 用户确认：左右分栏保留；欢迎页要更有产品感；任务栏小图标仍是窗口缩略图
- 根因：HWND 已 `WM_SETICON`，Explorer/DWM 仍用空白欢迎页 live snapshot 当任务栏按钮
- 修复：`DWMWA_FORCE_ICONIC_REPRESENTATION` + 窗口 `AppUserModelID` / `RelaunchIconResource`；欢迎页纸感背景、实心「打开文件」、最近文件卡片；未改拖动/窗控
- 验证：全量 `359 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5955143 bytes`，SHA256 `a963180c703718808b03c94690fe7d39355944c46959f20ba0b03f24a4ec1c89`

## 下一步

用户再试桌面图标：欢迎页质感与任务栏蓝色 R

## 上一目标（已完成）

**空启动欢迎页 + 任务栏蓝色 R**

- 规格：`docs/superpowers/specs/2026-09-08-welcome-empty-launch-design.md`
- 计划：`docs/superpowers/plans/2026-09-08-welcome-empty-launch.md`（1 个任务已完成）
- 用户确认：方案 A；先做出来再改细节
- 空启动不再自动建 `未命名.md`；零标签显示欢迎页（Reader + `0.1.0`、打开/新建、最近文件）；`+` 仍建草稿
- 最近文件：`%LOCALAPPDATA%\Reader\recent.json`（测试用 `READER_DATA_DIR`）；成功打开才记，最多 12 条，缺失路径会清掉
- 显示后下一拍重设 `WM_SETICON`；快捷方式图标用 `reader.ico`，并写 `AppUserModelID`
- 验证：全量 `357 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 未改 `hit_test_local` / `begin_window_move` / `nativeEvent`
- 最终 `dist/Reader/Reader.exe`：`5950863 bytes`，SHA256 `56bcdb7de5b0fe959ed2baddd7486540a5b6719078cb7d3676f224d091842580`

## 下一步

用户试用桌面图标后的欢迎页文案/布局；任务栏若仍不是蓝色 R 再补一拍

## 上一目标（已完成）

**源码一键启动 + 0.1.0 说明（git 不含 exe）**

- 规格：`docs/superpowers/specs/2026-09-08-source-setup-release-design.md`
- 计划：`docs/superpowers/plans/2026-09-08-source-setup-release.md`（2 个任务均已完成）
- 用户确认：版本 `0.1.0`；git 只进脚本和文档；clone 后 `scripts/setup.ps1` 装依赖并启动；不提交 zip/bin/exe
- `VERSION` 为 `0.1.0`；`scripts/setup.ps1` 建 `.venv`、`pip install -e .`、启动 `-m reader`
- README / `release/README.md` 写明能力和源码快照政策
- 未改拖动 / 窗控

## 上一目标（已完成）

**修复：原生 PDF 标签空白**

- 规格仍为：`docs/superpowers/specs/2026-09-07-pdf-reading-design.md`
- 现象：打开 `.pdf` 后标签有文件名，内容区全白
- 根因：默认 `QWebEngineView` 的 `PluginsEnabled=False`；Chromium 把 `application/pdf` 当成下载，页面留空
- 修复：仅 PDF 视图打开 `PluginsEnabled` + `PdfViewerEnabled`；HTML 预览保持插件关闭
- 验证：全量 `343 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；用用户 PDF 复现 `loadFinished=True` 且出现内置 `<embed type="application/pdf">`
- 未改 `hit_test_local` / `begin_window_move` / `nativeEvent`
- 最终 `dist/Reader/Reader.exe`：`5922601 bytes`，SHA256 `933df5ba9236eb0b1621efc09643e070a2288d250704c8e783af5723c8cab70c`

## 上一目标（已完成）

**原生 PDF 阅读（Chrome 式 WebEngine）**

- 规格：`docs/superpowers/specs/2026-09-07-pdf-reading-design.md`
- 计划：`docs/superpowers/plans/2026-09-07-pdf-reading.md`（3 个任务均已完成）
- 用户确认：`.pdf` 只读标签；Chromium 内置查看器；不拷贝用户原文件；Office 导出 PDF 仍 pin；不绑 Ctrl+I/T；不改拖动/窗控
- Task 1：`.pdf` 进入 sniff / pipeline / Open With；`formats.pdf.to_preview` 指向源路径
- Task 2：仅当 `pdf_path` 就是打开的源文件时跳过 pin/cache；打开对话框含 `*.pdf`
- Task 3：全量 `341 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 附带：`.gitattributes` 将 hashed bundle 文本固定为 LF，构建脚本以 LF 写 `manifest.sha256`，避免 Windows `core.autocrlf` 把 NOTICE 转成 CRLF 后 SHA256 对不上
- 未改 `hit_test_local` / `begin_window_move` / `nativeEvent`
- 最终 `dist/Reader/Reader.exe`：`5922423 bytes`，SHA256 `b684a34266263df1b8501eaa3a9426075229c5a7486fc34746e7295b1b258b4e`
- source/frozen md-viewer manifest SHA256 均为 `1a24cacca58fbeca8d002919080c2b1a23d065abfea6e51354cce385b10c30c3`；pptx 均为 `857bf20210931b26208edf4b639480c2c46c49821ad8269880c30913086834db`

## 上一目标（已完成）

**Markdown 默认展示 + Ctrl+I/T 切换编辑**

- 规格：`docs/superpowers/specs/2026-09-03-markdown-visual-default-design.md`
- 计划：`docs/superpowers/plans/2026-09-03-markdown-visual-default.md`（3 个任务均已完成）
- 用户确认：打开已有 `.md` 只读渲染；新建可编辑；Ctrl+I 进入编辑；Ctrl+T 回渲染（未保存则先强制保存）；不改拖动/窗控
- 修复：去掉 `.md` 文本短路径；`Ctrl+I` / `Ctrl+T` 为 Markdown 专用 `ApplicationShortcut`；Ctrl+T 先强制保存
- 验证：全量 `334 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5921624 bytes`，SHA256 `d2794cec1186ce3e67fae1d88054abe86360a2cb22906b1acacc8bbba87aa31d`

## 上一目标（已完成）

**冷启动首行空隙 + 任务栏图标**

- 规格：`docs/superpowers/specs/2026-09-02-notepad-cold-open-icon-design.md`
- 计划：`docs/superpowers/plans/2026-09-02-notepad-cold-open-icon.md`（2 个任务均已完成）
- 用户确认：直接打开第一行上方仍有空隙（放大再缩小后消失）；任务栏小图标是窗口缩略图而不是蓝色 R
- 根因：`SWP_FRAMECHANGED` 之后 `QTabWidget` 把内容栈推回 `y≈30`；补边框样式后 HWND 未再 `WM_SETICON`
- 修复：`LayoutRequest` / frame restore 后再 stretch pane；补边框后 `WM_SETICON` 重设蓝色 R
- 未改拖动 / 窗控命中测试
- 验证：全量 `330 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5921120 bytes`，SHA256 `08e3437583d69c5117c5d59f4c86bbe0c2345c7b1216f6c999ab6c297d81aad3`

## 上一目标（已完成）

**记事本间距与表面：+ 贴标签、柔和页色、窗口圆角、编辑区贴标题栏**

- 规格：`docs/superpowers/specs/2026-09-02-notepad-spacing-surface-design.md`
- 计划：`docs/superpowers/plans/2026-09-02-notepad-spacing-surface.md`（2 个任务均已完成）
- 未改拖动 / 窗控命中测试
- 验证：全量 `329 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5919448 bytes`，SHA256 `43db18c096d3ad841dd1998c353878cc577c15dadff734dde4f4a8be6cb72769`

## 上一目标（已完成）

**记事本标题栏表面：整条浅灰、选中标签与编辑区同白、按钮悬停变色**

- 规格：`docs/superpowers/specs/2026-09-02-notepad-title-surface-design.md`
- 计划：`docs/superpowers/plans/2026-09-02-notepad-title-surface.md`（2 个任务均已完成）
- 未改命中测试 / `startSystemMove` / 窗控点击
- 验证：全量 `328 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5917666 bytes`，SHA256 `126da20aa2a4ccebbb90dd7a93e8651b5842b6ed8545472961d61c94b0820174`

## 上一目标（已完成）

**记事本命中测试修复：按钮可点、可重复拖动、边框对准、灰标题/白内容**

- 规格：`docs/superpowers/specs/2026-09-02-notepad-chrome-hittest-design.md`
- 计划：`docs/superpowers/plans/2026-09-02-notepad-chrome-hittest.md`（3 个 TDD 任务均已完成）
- 根因：把 Qt 按钮映射成 `HTMINBUTTON/HTCAPTION` 后系统点到不存在的非客户区；`startSystemMove` 只能拖一次；`lParam` 未走 `ScreenToClient`
- 验证：全量 `327 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5917525 bytes`，SHA256 `98d37371d34a4e7f75539fc945134b3ea305c7761dfb50fc945522acb4c9968a`

## 上一目标（已完成）

**记事本式无缝表头：真正可拖动 + 标签/编辑区同色无分隔 + 隐藏状态栏**

- 规格：`docs/superpowers/specs/2026-09-02-notepad-seamless-chrome-design.md`
- 计划：`docs/superpowers/plans/2026-09-02-notepad-seamless-chrome.md`（3 个 TDD 任务均已完成）
- 根因：无边框窗口的 `WM_NCHITTEST` 被 Qt 吞掉；改为 caption/图标 `startSystemMove()`，Win32 `WM_NCLBUTTONDOWN` 兜底
- 验证：聚焦 chrome 测试通过；全量 `325 passed, 1 skipped`（packaging 文案断言已对齐）；frozen smoke PPTX/MD/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5917281 bytes`，SHA256 `4094bd713c892c40877a3d8209a9eb0b91cc58c75c9e4eedc9bd6d75f2424eda`

## 上一目标（已完成）

**Markdown 记事本编辑 + 表头拖动/高度/WebEngine 预热**

## 上一目标（已完成）

**Markdown 记事本编辑 + 表头拖动/高度/WebEngine 预热**

- 规格：`docs/superpowers/specs/2026-09-01-markdown-edit-chrome-design.md`（方案 A）
- 计划：`docs/superpowers/plans/2026-09-01-markdown-edit-chrome.md`（5 个 TDD 任务均已完成）
- 验证：全量 `321 passed, 1 skipped`；frozen smoke PPTX/Markdown 视觉（`READER_SMOKE_MD_VISUAL`）/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5914744 bytes`，SHA256 `8954aa8f8842db783d3dab1f9c1de31b0f7f4568eafc7a4717785cafd4cd3afd`

## 上一目标（已完成）

**热修：无边框标题栏导致白屏/拖放失效/任务栏异常**

- 根因：纯 `FramelessWindowHint` 去掉 `WS_CAPTION|THICKFRAME|MIN/MAX`，任务栏无法正常最小化/还原；空窗口无拖放提示
- 修复：`showEvent` 补回 Win32 边框样式；空窗口显示 `emptyWindowHint`；内容栈/标签接受拖放
- 验证：窗口/标题栏 `107 passed`；全量 `315 passed, 3 skipped`；frozen smoke PPTX/Markdown/IPC 通过；桌面快捷方式已刷新
- 最终 `dist/Reader/Reader.exe`：`5906378 bytes`，SHA256 `f30e82086ad05f0b7d7b506278c6478419f43ead7768dbd1d0eb671a86ae9d45`

## 上一目标（已完成）

**记事本式单行标题栏：去掉菜单/打开按钮，图标与标签同一行**

- 规格：`docs/superpowers/specs/2026-09-01-notepad-titlebar-design.md`（已实现）
- 计划：`docs/superpowers/plans/2026-09-01-notepad-titlebar.md`（5 个 TDD 任务均已完成）
- 方案：无边框窗口 + `TitleChrome` 单行（图标 | 标签 | + | 拖拽区 | 窗控）+ `WM_NCHITTEST`

## 上一目标（已完成）

**Markdown 视觉预览：主题、离线 Mermaid、同目录双链开新标签**

- 规格：`docs/superpowers/specs/2026-08-28-markdown-visual-preview-design.md`（用户已批准）
- 计划：`docs/superpowers/plans/2026-08-28-markdown-visual-preview.md`（8 个 TDD 任务均已完成）
- 方案：专用 `MarkdownVisualView` + 本地 Vite bundle（`markdown-it` + 官方 `mermaid`）；Python HTML 仅作启动失败回退
- 首期：浅色技术文档主题、完整官方 Mermaid 离线渲染、`[[wikilink]]` 在 Reader 中打开同目录 `.md`
- 禁止文档出站网络；`file:` 仅允许源目录与 viewer bundle
- PPTX 视觉预览保持不变

- 规格：`docs/superpowers/specs/2026-08-25-pptx-visual-preview-design.md`（已批准）
- 计划：`docs/superpowers/plans/2026-08-25-pptx-visual-preview.md`（已完成并通过计划审查，9 个 TDD 任务）
- 兼容修复计划：`docs/superpowers/plans/2026-08-26-pptx-relationship-compatibility.md`（用户批准方案 A）
- 方案：`QWebEngineView` + 本地许可兼容 Web 渲染器；左缩略图、右单页、缩放翻页
- 首版：静态高保真（背景/图片/文本/形状/表格/基础图表）；不做动画/视频/宏
- 禁止复制 `astx-jp.vscode-pptx-viewer` 专有代码
- 文本抽取保留为回退；Office 高保真仍可选

## 已完成

- UX 与打包：窗口 1200×800、空白标签、多开、builtin-first、Office 切换、图标、关联、onedir、IPC、冻结 smoke
- 规格/计划：`docs/superpowers/specs/2026-08-24-reader-ux-packaging-design.md`、`docs/superpowers/plans/2026-08-24-reader-ux-packaging.md`
- 桌面快捷方式已指向 `dist/Reader/Reader.exe`（用户可再要求刷新）
- PPTX Visual Preview Task 1：完成确定性 Web scaffold 与许可基线（`web/pptx-viewer`、锁定 `pptx-viewer@0.2.2`、唯一 runtime 传递依赖 `fflate`〔lock 解析 `0.8.3`〕、`THIRD_PARTY_NOTICES.txt`、输出到 `assets/pptx-viewer/`）
- PPTX Visual Preview Task 2：完成 Viewer 交互基线（`state.ts` + `viewer.ts`），覆盖 empty deck reject、navigation clamp、按钮/键盘/缩略图导航、25%-400% zoom 夹紧、fit 比例计算、0 尺寸安全处理与 `ResizeObserver` 触发重算；新增状态与 DOM 交互测试并通过
- PPTX Visual Preview Task 2（Important 审查修复）：完成多实例焦点隔离与 root 级键盘事件治理；`root.tabIndex=0`、点击控件/缩略图自动 focus、同 root 重复挂载自动 destroy 旧 controller，消除旧闭包监听泄漏风险
- PPTX Visual Preview Task 3：接入 `pptx-viewer@0.2.2` 官方 `loadPresentation` / `renderSlideToElement` / `getThumbnails` 生命周期，保留 master/layout 继承；真实四页 fixture 覆盖图片、表格、图表与缺失字体
- PPTX Visual Preview Task 3：导出 `ViewerBridge` 并完成 Qt WebChannel 启动、`file:` URL 限制、ready/error/slideChanged 上报、单页错误隔离、empty deck 整体错误与幂等 `presentation.cleanup()`；真实离线 bundle 已生成到 `assets/pptx-viewer/`
- PPTX Visual Preview Task 3（Important 审查修复）：`startViewer` 支持 `AbortSignal` 取消加载与挂载后销毁；`main.ts` 保留 controller 所有权并暴露 `window.readerPptxDispose()`，同时处理 pagehide/beforeunload
- PPTX Visual Preview Task 3（Important 审查修复）：`createViewer` 初始化失败会原子移除 listeners、disconnect observer、清除 root ownership 并 rethrow；销毁后 public render 明确报 disposed，double destroy/abort 幂等
- PPTX Visual Preview Task 3 验证：Web 23 tests、TypeScript typecheck/build、Python Web 资源 4 tests、Python 全量 203 tests 全部通过；未改 Python 产品链路
- PPTX Visual Preview Task 4：完成 `PreviewMode` 扩展（`builtin/visual/text/office`）与 `.pptx` 默认 `visual`；`fmt_pptx.to_visual()` 返回 `kind="pptx"` 并携带 `fallback_html`（复用 `to_html`）
- PPTX Visual Preview Task 4：`text` 模式显式返回 HTML（`内置预览（文本模式）`）；`office` 在 `.pptx` 不可用时回退到 visual（不触发 COM 导出）
- PPTX Visual Preview Task 4：建立缓存契约——visual 跳过 cache `get/put` 且不复用旧 builtin HTML/PDF 缓存，text 使用独立 `text` strategy，`PreviewCache.put` 对 `kind="pptx"` 维持拒绝
- PPTX Visual Preview Task 4：保留 worker 完整 `try/_pin_pdf/emit` 控制流；迁移 4 个 builtin `.pptx` FakeCache PDF 用例到 `.docx`（含 reentrancy），避免视觉模式引入误回归
- PPTX Visual Preview Task 4 验证：`tests/test_formats_pptx.py tests/test_pipeline.py tests/test_cache.py tests/test_window.py -v` 共 `100 passed`
- PPTX Visual Preview Task 4（Important 修复）：`to_visual` 异常回退改为固定安全文案，不再暴露异常细节/绝对路径/HTML 片段；`python -m pytest -v` 全量 `208 passed`
- PPTX Visual Preview Task 5：新增 `PptxVisualView` 显式 `start()` 生命周期；构造阶段仅建立互相隔离的 off-the-record profile/page/channel/bridge，不自动 load，15 秒超时且 bundle URL 不携带 source query
- PPTX Visual Preview Task 5：profile 由 QApplication 生命周期资源守卫持有而非 view；显式 shutdown、closeEvent 和遗漏 shutdown 的 destroyed cleanup 均按 interceptor → channel → page → profile 安全释放
- PPTX Visual Preview Task 5：请求拦截器仅放行 `file/qrc/data/blob`，以锁保护 blocked URL 快照且不从 Chromium 线程发 Qt Signal；显式 helper 保证 profile 安装/卸载 interceptor
- PPTX Visual Preview Task 5：显式注册 QtWebChannel qrc 并在 `DocumentCreation/MainWorld` 注入 `qwebchannel.js`；bridge 提供一次 FullyEncoded 的 `sourceUrl`、`testFailSlide` 及 ready/error/slide relay
- PPTX Visual Preview Task 5（Important）：fallback 前断开 load、停止加载、清 scripts、解绑 channel/bridge、关闭 JavaScript，使用空 base URL；超大 fallback 改用固定安全文本，qrc 缺失改为 view 子 QTimer，ready/未启动/销毁后的失败事件不再误触发 fallback
- PPTX Visual Preview Task 5（Important）：删除 shutdown 中假同步 `runJavaScript(readerPptxDispose)`；依赖 pagehide/beforeunload 与 JS context 销毁释放 renderer，换 inert page 后再 unparent/deleteLater，重复 shutdown 幂等
- PPTX Visual Preview Task 5 验证：聚焦 `tests/test_pptx_view.py -v` 为 `16 passed`；Python 全量 `224 passed`；IDE lint 与 `git diff --check` 通过；未接入 MainWindow（留给 Task 6）
- PPTX Visual Preview Task 6：默认 viewer factory 对 `kind="pptx"` 创建 `PptxVisualView`；所有文档内容替换统一经 `_install_document_content`，先绑定 ready/slide/render-failed 事件再 `start()`，所有内容销毁统一经 `_dispose_widget` 调用 `shutdown()` 后 `deleteLater()`
- PPTX Visual Preview Task 6：新增 PPTX 专用“文本模式/视觉模式”动作；手动文本使用独立 `text` 缓存，Office 切回恢复最近 builtin visual/text，Office 失败保留当前内容并回到 `builtin_mode`
- PPTX Visual Preview Task 6：视觉整体失败由 view 内部展示 fallback，窗口状态精确为 `内置预览（视觉渲染失败）` 且保持 visual；ready/slide/failure 事件均受 document identity、generation、widget、mode 与 closing guard 保护
- PPTX Visual Preview Task 6：切换 Office、切换文本/视觉、关闭标签和关闭窗口均显式销毁 visual；补齐 worker 完成、Office 共存/失败、手动模式、缓存、重入与迟到事件测试
- PPTX Visual Preview Task 6 验证：RED 聚焦 `10 failed, 1 passed`（缺失功能符合预期）；窗口完整 `77 passed`（后续补测后为 80 项）；Python 全量 `237 passed`；IDE lint 与 `git diff --check` 通过
- PPTX Visual Preview Task 6（Important）：`_Document` 显式持有 visual signal/slot 连接；restart、rebind、content disposal 均先断开旧连接，反复 Office 失败恢复不再线性堆积 stale generation handler
- PPTX Visual Preview Task 6（Important）：`_install_document_content` 在同步 `start()` 后重新校验 closing、document identity、generation 与 layout ownership；同步关闭 tab/window 会返回失败、清理 output artifact，且不会写 artifact 状态或启动幽灵 Office availability probe
- PPTX Visual Preview Task 6（Important）验证：RED 聚焦 `3 failed, 1 passed, 1 error`（连接存储缺失、同步关闭后仍探测 Office，window 测试 teardown 随后修正）；GREEN 聚焦 `4 passed`、窗口 `83 passed`、Python 全量 `240 passed`；IDE lint 与 `git diff --check` 通过
- PPTX Visual Preview Task 6 按本次用户指令只提交、不推送；本地提交将领先 `origin/main`
- PPTX Visual Preview Task 7：真实四页 fixture 现由 `scripts/generate_pptx_visual_fixture.py` 字节级确定性生成；固定外层 PPTX 与嵌入图表 XLSX 的 ZIP 元数据和 core 时间，兼容回归 fixture SHA256 为 `3ba6deda14de119b0de8751d5258461ea91f900634d7558c741ace3def96e8d4`
- PPTX Visual Preview Task 7：新增真实 QWebEngine 集成覆盖主题背景、PNG `<image>`、`foreignObject table`、基础 chart 结构、缺失字体、四缩略图/首选中、六键导航、缩略图点击、zoom/fit 和 stage resize
- PPTX Visual Preview Task 7：真实 Chromium 请求验证 HTTP/HTTPS/WS/WSS 全由 `OfflineRequestInterceptor` 记录并阻断；测试仅临时绕过第一层 local-content remote policy 以直接验证第二层，产品默认仍保持 remote access 关闭
- PPTX Visual Preview Task 7：constructor-only `test_fail_slide` 经 WebChannel 注入且不进入 query；单页故障显示占位后可继续渲染其他页，无整 deck fallback
- PPTX Visual Preview Task 7：真实 `MainWindow` 默认工厂加载四页并在关闭时释放 off-the-record profile；缺失 bundle/`QtWebEngineProcess.exe` 或进程启动失败显式 skip，注册 `webengine` marker
- PPTX Visual Preview Task 7 验证：RED `2 failed, 2 passed`（generator 不支持输出/不确定、DOM 元素类型探针缺失）；GREEN 聚焦 `20 passed`；npm `23 passed`；Python 全量 `244 passed`；npm typecheck/build、IDE lint 与 `git diff --check` 通过
- PPTX Visual Preview Task 7 按本次用户指令只提交、不推送、不修改 git config
- PPTX Visual Preview Task 7（Important 审查修复）：zoom/fit 改为解析百分比并校验 `+10`、25%–400% 范围及 transform；真实 host 同时断言 `Inherited title` 与 `#14305A` 背景 paint；网络注入前 snapshot 必须为空，注入后规范化集合必须精确等于 HTTP/HTTPS/WS/WSS 四项
- PPTX Visual Preview Task 7（Important 审查修复）：所有直接 `PptxVisualView` 用例统一由 context manager 在 `finally` shutdown 并等待 profile invalid；真实 `MainWindow` 同样保证异常路径清理
- PPTX Visual Preview Task 7（Minor 审查修复）：fixture/generator/hash 测试移出 `webengine` marker，钉死背景 RGB、`MSO_SHAPE_TYPE.PICTURE` 与 SHA256；Vitest 补充 `data-element-types` 精确断言
- PPTX Visual Preview Task 7（审查验证）：RED `1 failed, 2 passed`，原生 `qtbot.keyClick(QWebEngineView, Right)` 因 WebEngine 焦点桥接 10 秒无事件，按允许的 Minor 留项撤回；其余强化断言直接验证通过。聚焦连续两轮均 `20 passed`；Python 全量 `244 passed`；npm `23 passed`；typecheck/build 与 IDE lint 通过
- PPTX Visual Preview Task 7（审查修复）按本次用户指令创建新提交，不 amend、不 push、不修改 git config
- PPTX Visual Preview Task 8：`reader.spec` 收集完整 `assets/pptx-viewer`（bundle、notice、manifest）并显式收集 `PySide6.QtWebChannel` 隐式模块
- PPTX Visual Preview Task 8：Windows 构建在 Python/PyInstaller 前验证 Node.js 18+ 与 `npm.cmd`，通过 `cmd /d /s /c call` + `Start-Process -Wait -PassThru` 保留原生退出码；含空格 npm 路径与退出码 23 的模拟证明失败时不清理 dist、不运行 PyInstaller
- PPTX Visual Preview Task 8：生产构建依次执行 `npm ci`、包含 typecheck 的 `npm run build`，生成 ordinal 排序的 `manifest.sha256` 并在源 bundle 与 frozen bundle 两次验 hash
- PPTX Visual Preview Task 8：最终 clean build 成功，确认 `dist/Reader/_internal/assets/pptx-viewer/{index.html,manifest.sha256,THIRD_PARTY_NOTICES.txt}`、bundle assets 与 `PySide6/QtWebChannel.pyd` 存在；源/frozen manifest 文件 SHA256 均为 `f6f32aa6416717bb47aebcd4f365cc976dd01c24d86a8e768a12b70042fc2633`
- PPTX Visual Preview Task 8 验证：RED 初始 `4 failed, 13 passed`，另以含空格 npm 路径及 Windows PowerShell `.NET` API 兼容性测试复现两项真实构建问题；GREEN 聚焦 `19 passed`，Python 全量 `251 passed`，最终 `build_windows.ps1` exit 0，IDE lint 与 `git diff --check` 通过
- PPTX Visual Preview Task 8 按本次用户指令只提交、不推送、不修改 git config
- PPTX Visual Preview Task 8（Important）：构建先解析 `npm.cmd`，优先验证其同目录 `node.exe`，仅在不存在时回退 PATH `node.exe`；版本失败消息和正常选择日志均包含实际 Node 路径，避免验证与 npm 执行使用不同安装
- PPTX Visual Preview Task 8（Important/Minor）：source/frozen manifest 共用严格的 SHA256 行格式与空行 guard；测试锁定 Vite `outDir`/`emptyOutDir: true`，显式 opt-in 真实 npm build 证明 stale asset 被删除且自动恢复 bundle，普通 pytest 不调用 npm
- PPTX Visual Preview Task 8（审查验证）：RED `3 failed, 17 passed`；显式 npm 聚焦 `20 passed`；普通全量 `251 passed, 1 skipped`；clean `build_windows.ps1` exit 0 并记录使用 `C:\Program Files\nodejs\node.exe`；同时将既有 Office availability 测试等待条件收紧到最终 tooltip，消除双 queued signal 竞态
- PPTX Visual Preview Task 8（审查修复）按本次用户指令创建新提交，不 amend、不 push、不修改 git config
- PPTX Visual Preview Task 9：新增 `READER_SMOKE_VISUAL_LOG` 可选 JSONL telemetry；`append_visual_ready()` 写入 path/kind/slides/status 后显式 flush + `os.fsync`，默认禁用且无文件副作用
- PPTX Visual Preview Task 9：窗口仅在 document identity、generation、widget、visual mode、layout ownership 与 closing guards 全部通过后记录 ready；关闭 tab 后的迟到 ready 不更新状态也不落盘
- PPTX Visual Preview Task 9：`smoke_windows.ps1` 严格拆分 Phase A/Phase B；Phase A 独立 frozen Reader + 真实四页 fixture + 独立 60 秒 deadline，验证 `visual-ready slides=4` 且无 `renderer-failure`，完整停止 Reader/QtWebEngine 树并删除 visual profile/namespace 后，Phase B 才创建全新 `$ipcPrimary` 执行原有两批 IPC
- PPTX Visual Preview Task 9：AMD/D3D 常驻驱动会长期锁定被重定向 `LOCALAPPDATA` 下的 shader cache；Phase A 因此只复用主机系统 GPU cache 路径，同时继续隔离 Reader/Chromium `USERPROFILE`、`APPDATA`、显式 Chromium user-data-dir、TEMP 与 IPC namespace；Phase B 保持完整 profile 隔离
- PPTX Visual Preview Task 9 验证：RED 聚焦 `5 failed, 3 passed`；GREEN 聚焦 `8 passed`；Web `23 passed`；Python 全量 `255 passed, 1 skipped`；npm typecheck/build、IDE lint、clean PyInstaller build 均通过
- PPTX Visual Preview Task 9 frozen smoke：Phase A 收到真实 fixture `ready/slides=4`，Phase B 精确收到两批各 2 文件 IPC；结束后 `ReaderProcesses=0`、visual/ipc 隔离根均不存在
- PPTX Visual Preview 最终依赖/产物：`pptx-viewer 0.2.2`、lock 解析 `fflate 0.8.3`、Node `22.22.0`、npm `11.15.0`、PySide6 `6.11.2`、PyInstaller `6.22.2`；bundle manifest SHA256 `f6f32aa6416717bb47aebcd4f365cc976dd01c24d86a8e768a12b70042fc2633`
- 最终 `dist/Reader/Reader.exe`：`5884468 bytes`，SHA256 `1a40cb1760499c44d73283895a83752ae0dd4fc84aa96e2412f97dfd9eac0219`；桌面 `Reader.lnk` 已刷新并验证 target/workdir/icon 均指向该 exe
- PPTX Visual Preview Task 9 按本次用户指令只提交、不 push、不修改 git config
- PPTX 最终审查修复：默认打开 `.pptx` 不再探测/调用 Office COM，只有用户点击“Office 高保真”后才在独立 availability pool 检测；unknown 时 action 可点击、pending 时禁用、available 结果继续 Office 请求
- PPTX 最终审查修复：文本模式或 Office 请求失败时恢复请求前的同一 widget、mode/status 与 visual signal 连接；关闭、取消、迟到 worker/availability/visual 事件均由 identity/generation/ownership guards 隔离
- PPTX 最终审查修复：WebEngine `file:` 请求仅允许 source 精确 canonical 文件和 bundle canonical realpath 根；使用 Windows `normcase(realpath)`，阻断 sibling、parent、`..`、symlink escape 与任意其他 file
- PPTX 最终审查 Web/UI：保留中文 toolbar 与居中 letterbox；真实 bundle 加载完成后 blocked 初始快照为空，网络探针仍精确阻断 HTTP/HTTPS/WS/WSS
- 最终审查验证：`tests/test_pptx_view.py` 17 passed；`tests/test_window.py` 92 passed；真实 `tests/test_pptx_webengine.py` 连续两轮均 3 passed；Web 24 passed；npm typecheck/build 通过；Python 全量 `263 passed, 1 skipped`
- 最终审查 clean build/smoke：`scripts/build_windows.ps1` exit 0；Phase A `visual-ready slides=4`，Phase B 两批各 2 文件 IPC 精确到达；source/frozen manifest SHA256 均为 `6e66ec6221fa109fc36cc3f0dadf027828defdfaeeb9ed335c0f914a5ca8949b`
- 最终审查 `dist/Reader/Reader.exe`：`5885743 bytes`，SHA256 `cc016b2f99bc3543f8a175060ec71e9cbfd039d6829002fc3342ab343bcf963e`；桌面 `Reader.lnk` 已覆盖刷新并验证 target/workdir/icon 均指向新 exe
- PPTX 最终整分支复审：三项 Important（默认打开零 COM、失败恢复原 widget/mode、`file:` 路径级 allowlist）均已关闭；复审结论 `Approved`，无 Critical/Important
- 最终独立验证修复：fixture ZIP 规范化由 DEFLATE 改为 STORE，消除 Python 3.12 标准 zlib 与 Python 3.14 zlib-ng 间的压缩字节差异；两种受支持解释器生成结果现共享上述 SHA256
- 最终独立验证：Web `24 passed`、项目 Python `263 passed, 1 skipped`、clean build exit 0、frozen Phase A `slides=4`、Phase B 两批 IPC 均通过；manifest SHA256 `6e66ec6221fa109fc36cc3f0dadf027828defdfaeeb9ed335c0f914a5ca8949b`
- PPTX 关系兼容 Task 1：公开四页 fixture 将 presentation 直接 `slide` 关系稳定置于 `slideMaster` 之前，复现真实 deck 的合法 OOXML 顺序；Python fixture 回归 `1 passed`
- PPTX 关系兼容 Task 1 RED：未打补丁的 `pptx-viewer@0.2.2` 在该顺序下 `slideLayouts.size === 0`，聚焦 Web 回归为 `1 failed, 13 passed`，失败点与 `canis_handover.pptx` 一致
- PPTX 关系兼容 Task 2：新增固定版本 fail-fast `postinstall` 补丁；`getByType()` 先以 `hn(i)` 取得终端类型，再做精确 `Map.get`，彻底区分 `slide`、`slideLayout` 与 `slideMaster`
- PPTX 关系兼容 Task 2：补丁脚本覆盖替换、幂等、源码漂移和已安装 ESM 四项回归；`npm ci` 会自动应用，依赖版本不是 `0.2.2` 或期望片段不唯一时直接失败
- PPTX 关系兼容 Task 2：上游 MIT notice 保留并记录 Reader 本地修改；source/bundle notice 字节一致，clean build bundle manifest SHA256 为 `1f165ff62ea65b671d164b738fdd0f9ec599527149333400d69c0633d967e8fb`
- PPTX 关系兼容 Task 2 GREEN：Web `28 passed`、typecheck/build 通过；fixture/web-assets/packaging 聚焦 `20 passed, 1 skipped`
- PPTX 关系兼容 Task 3：公开 adversarial fixture 在真实 QWebEngine 中继续显示 `Inherited title`、图片、表格、图表与背景，聚焦 WebEngine `3 passed`
- PPTX 关系兼容真实 deck 验收：本机 `canis_handover.pptx` 上报 `ready=7`、`error=None`；第一页 SVG 包含 `CANIS handover`、`Lina` 及 master 层 `AMD General`，不再空白
- PPTX 关系兼容最终验证：Web `28 passed`、typecheck 通过；Python 全量 `263 passed, 1 skipped`；独立审查结论 `Approve`，无 Critical/Important
- PPTX 关系兼容 clean build/smoke：`build_windows.ps1` exit 0；Phase A `visual-ready slides=4`，Phase B 两批各 2 文件 IPC 精确到达；source/frozen manifest SHA256 均为 `1f165ff62ea65b671d164b738fdd0f9ec599527149333400d69c0633d967e8fb`
- 最终 `dist/Reader/Reader.exe`：`5885743 bytes`，SHA256 `c707de0bec0b5353ac0da629748804f5e08847091c5484eaa5f3add2a8932a3c`；桌面 `Reader.lnk` 已刷新并验证 target/workdir/icon
- Markdown Visual Preview Task 1：建立 `web/md-viewer` 确定性离线 scaffold（runtime 仅 `markdown-it`/`mermaid`，全部依赖 `--save-exact`），新增 `notices/test/typecheck/build` 脚本、本地 bootstrap `index.html` 与占位 `main.ts`
- Markdown Visual Preview Task 1：新增完整供应链与产物测试 `tests/test_md_web_assets.py`，记录 RED（3 failed，缺少 scaffold/asset）并达成 GREEN（3 passed）
- Markdown Visual Preview Task 1：`generate-notices.mjs` 通过 license-checker 扫描 production dependency tree，按 `name@version` 排序并逐包强制读取 `licenseFile`（缺失/空文本 fail-fast），生成确定性 `THIRD_PARTY_NOTICES.txt` 并同步到 `assets/md-viewer/`
- Markdown Visual Preview Task 1：完成 `assets/md-viewer/manifest.sha256` 确定性生成（按相对路径排序、SHA256 双空格格式），并加入 `web/md-viewer/node_modules/` ignore；PPTX 资产与行为未改动
- Markdown Visual Preview Task 1（审查修复）：dev toolchain 回退到 Node 18 兼容 exact pin（`vite@5.4.19`、`vitest@2.1.9`、`jsdom@24.1.3`、`typescript@5.9.2`、`@types/node@22.13.14`、`@types/markdown-it@14.2.0`），移除 `license-checker-rseidelsohn` Node24 门槛
- Markdown Visual Preview Task 1（审查修复）：新增无第三方许可工具的 production-tree notice walker（`npm ls --omit=dev --all --json` + lock 路径映射 + 缺失 license text fail-fast）并保留确定性排序
- Markdown Visual Preview Task 1（审查修复）：新增 `generate-manifest.mjs`，`npm run build` 顺序固定为 `vite build -> notices -> manifest`；clean 删除 `assets/md-viewer` 后可自动恢复 `index/assets/THIRD_PARTY_NOTICES/manifest`
- Markdown Visual Preview Task 1（审查修复）：`tests/test_md_web_assets.py` 扩展到 6 项，锁定 lock 根元数据、Node18 兼容 devDependency 基线、manifest 脚本接线与 opt-in clean build 恢复校验，当前 `6 passed`
- Markdown Visual Preview Task 1（同步收尾）：controller 已使用 repository owner 凭证将 `e403337` 成功推送到 `origin/main`，Task 1 当前所有提交已完成远端同步
- Markdown Visual Preview Task 1（Important 修复）：`generate-notices.mjs` 改为仅写稳定 `node_modules/...` POSIX 相对路径，不再写本机绝对路径；source/bundle notice 与 manifest 消除 checkout 路径泄露和不确定性
- Markdown Visual Preview Task 1（Important 修复验证）：`npm test`、`npm run typecheck`、`npm run build`、`tests/test_md_web_assets.py`（扩展至 `7 passed`）与 `git diff --check` 均通过；新增断言禁止 ROOT/Windows drive/backslash 路径泄露，并验证 label 在不同模拟根路径下稳定
- Markdown Visual Preview Task 2：新增 `renderMarkdown(source, sourceUrl)` 与 `WikiLink` 契约，`markdown-it` 关闭 raw HTML、启用 table/strikethrough，并注册 `[[target]]`/`[[target|alias]]` inline wikilink 规则，输出 `<a class="wiki-link is-pending" data-wiki-target="...">...`
- Markdown Visual Preview Task 2：渲染后仅重写相对 `img[src]` 到 `new URL(..., sourceUrl).href`，保留 `data:`/绝对 URL；表格统一包裹 `.table-scroll`，代码块与行内代码中的 `[[...]]` 保持原样不转换
- Markdown Visual Preview Task 2：新增 `web/md-viewer/src/style.css` 技术文档主题（paper/ink/accent/code 变量、表格/引用/内联代码/图片/selection/print 规则），并在 `main.ts` 挂载 `.markdown-document`
- Markdown Visual Preview Task 2 验证：RED `npm test -- src/markdown.test.ts`（缺少 `./markdown` 导入失败）→ GREEN 同命令 `2 passed`；随后 `npm test`（`3 passed`）、`npm run typecheck`、`npm run build`、`python -m pytest tests/test_md_web_assets.py -v`（`7 passed`）全部通过
- Markdown Visual Preview Task 2（审查修复）：wikilink inline rule 增加链接上下文防护（`state.linkLevel > 0` 直接放弃转换），并修正 silent 解析路径，避免 `[see [[note]]](target.md)` 触发 nested anchor / `state.pos` 异常
- Markdown Visual Preview Task 2（审查修复验证）：新增回归覆盖（普通链接内 wikilink 不转换且外层 `<a>` 结构合法、空 target/alias 保持源码、HTTP/data/hash/protocol-relative 图片不改写）；RED `npm test -- src/markdown.test.ts` 复现 `inline rule didn't increment state.pos`，GREEN 后同命令 `5 passed`；全量 `npm test`（`6 passed`）、`npm run typecheck`、`npm run build`、`python -m pytest tests/test_md_web_assets.py -v`（`7 passed`）、`git diff --check` 全部通过
- Markdown Visual Preview Task 3：新增 `web/md-viewer/src/mermaid.ts` 与 `renderMermaidBlocks(root)`，Mermaid 初始化固定 `securityLevel: "strict"` + `suppressErrorRendering: true`；按块渲染 `pre > code.language-mermaid`，单块失败仅替换为 `.mermaid-error`，源码通过 `textContent` 写入，坏图不影响全文
- Markdown Visual Preview Task 3：新增 `web/md-viewer/src/viewer.ts` 与 `startViewer(...)` 生命周期；同 root 复用前先销毁旧 controller（WeakMap），等待 Mermaid + 异步 `wikiExists` 全部完成后单次 `viewerReady`，为 resolved/missing wiki 分级并桥接 click；普通 `http/https/ws/wss` 锚点统一 `preventDefault`
- Markdown Visual Preview Task 3：`abort/destroy` 幂等清理 click listeners 与 DOM，阻断迟到 wiki 回调和 `viewerReady`；`main.ts` 完成 Qt WebChannel bootstrap，读取 `bridge.sourceUrl` 拉取 markdown，持有 `AbortController` 并暴露 `window.readerMdDispose`，在 `pagehide/beforeunload` 触发
- Markdown Visual Preview Task 3：新增 bootstrap 固定错误文案路径泄露防护测试（`viewerError` 不含 source path/raw exception），并补齐 Mermaid 单块成功/失败、viewer 时序与 late callback 回归
- Markdown Visual Preview Task 3（审查修复 Important）：`main.ts` fetch 显式绑定 `AbortController.signal`；bootstrap catch 在 `disposed` 或 `AbortError` 时直接静默，修复 dispose 后 pending/rejected fetch 触发 late `viewerError`
- Markdown Visual Preview Task 3（审查修复 Important）：`viewer.ts` wiki existence 改为 fail-closed；捕获 `bridge.wikiExists` 同步异常，并引入 `WIKI_EXISTS_TIMEOUT_MS=2000` 保证 never-callback 自动按 missing 收敛，回调/销毁均 clear timer，late callback no-op
- Markdown Visual Preview Task 3（审查修复 Important）：`main.ts` dispose 显式 `removeEventListener(pagehide/beforeunload)` 并清理 `readerMdDispose`；`main.test.ts` afterEach 主动 dispose，回归覆盖重复 module import 不累积 stale closure
- Markdown Visual Preview Task 3（审查修复 Minor）：移除不完整 `src/type-fest.d.ts` ambient shim，按 `npm view` 结果安装 Node18 兼容且 exact 的 `type-fest@4.41.0` devDependency，并通过 `npm ci`
- Markdown Visual Preview Task 3（审查修复 Minor）：清理 `.superpowers/sdd/md-task-3-report.md` 重复正文，保留单份原始 RED/GREEN 并追加本轮修复记录
- Markdown Visual Preview Task 3 审查验证：RED `npm test -- src/main.test.ts src/viewer.test.ts` 复现 `7 failed`（late error/wiki hang/listener 泄漏）；GREEN 后同命令 `13 passed`；全量 Web `npm test`（`19 passed`）、`npm run typecheck`、`npm run build`、`python -m pytest tests/test_md_web_assets.py -v`（`7 passed`）、`git diff --check` 通过
- Markdown Visual Preview Task 3（复审 Important）：`viewer.ts` 的 `settleWikiExists` 入口先检查 `settled/active`，保证 2s timeout 收敛 missing 后任何 late callback 都 no-op，不再把 DOM 状态或 click 权限改回 resolved/open
- Markdown Visual Preview Task 3（复审 Important）：`main.ts` 在 WebChannel bridge 返回后、创建 AbortController/fetch 前立即做 `if (disposed) return`，避免 dispose 先发生时仍触发 fetch/start 或误上报错误
- Markdown Visual Preview Task 3（复审验证）：新增回归 `timeout -> missing -> late true callback` 与 `dispose before async QWebChannel callback`；RED `npm test -- src/main.test.ts src/viewer.test.ts` 复现 `2 failed`，GREEN 后同命令 `15 passed`；全量 Web `npm test`（`21 passed`）、`npm run typecheck`、`npm run build`、Python `tests/test_md_web_assets.py`（`7 passed`）与 `git diff --check` 通过
- Markdown Visual Preview Task 4：`PreviewKind` 新增 `markdown`；`src/reader/formats/md.py` 增加 `to_visual()`，返回 `kind="markdown"`、`html=""`、`fallback_html=to_html(path).html`，状态为 `内置预览（视觉模式）`
- Markdown Visual Preview Task 4：Markdown fallback 读取改为 `utf-8 errors="replace"`，并将 `MarkdownIt("commonmark", {"html": False})` 作为安全渲染基线；invalid UTF-8 显示 `\ufffd`，raw HTML 不执行
- Markdown Visual Preview Task 4：`preview()` 支持 `.md` 的 `visual` 模式，且 `.md` 在 `builtin/visual` 均走 `fmt_md.to_visual`；保持 Markdown 零 Office 探测/导出，PPTX 行为保持不变
- Markdown Visual Preview Task 4：`_PreviewWorker.run` 将 `.md` 与 `.pptx` 统一纳入 visual strategy，visual 策略继续跳过 cache `get/put`；`PreviewCache.put(... kind="markdown")` 维持 `ValueError` 拒绝持久化
- Markdown Visual Preview Task 4 验证：RED 聚焦 `5 failed, 121 passed`；GREEN 聚焦 `126 passed`；Python 全量 `275 passed, 1 skipped`
- Markdown Visual Preview Task 5：新增 `src/reader/preview/md_view.py`，实现 `resolve_wikilink()` 同目录 canonical resolver（仅允许 sibling `.md`/裸名、拒绝绝对路径/分隔符/`..`/非 md 后缀，并阻断 symlink escape）
- Markdown Visual Preview Task 5：新增 `MarkdownBridge`/`MarkdownVisualView` 与 `OfflineRequestInterceptor`，对齐 QWebChannel `sourceUrl/wikiExists/openWiki/viewerReady/viewerError` 契约；`ready` 仅上报 `1`，`open_path` 仅发 canonical path，`missing_link` 限制为 256 字符，shutdown 后 late bridge 调用无副作用
- Markdown Visual Preview Task 5：Markdown WebEngine lifecycle 与安全边界落地（构造不加载、`start()` 加载 `assets/md-viewer/index.html`、off-the-record profile 隔离、仅放行 source 目录与 bundle 目录 descendants + `qrc/data/blob`、阻断 remote 与目录逃逸、fallback 原子 detach channel/scripts/interceptor + JS 禁用 + `QUrl()`，fallback HTML 1.9MB 上限）
- Markdown Visual Preview Task 5 验证：RED `python -m pytest tests/test_md_view.py -v`（`ModuleNotFoundError: reader.preview.md_view`）；GREEN `16 passed`；PPTX 回归 `17 passed`；Python 全量 `291 passed, 1 skipped`
- Markdown Visual Preview Task 5（Reviewer Request changes / Important）：修复 source symlink lexical root 语义；`sourceUrl` 与 resolver/interceptor 根均使用 `abspath` lexical source，权限判断改为 `exact canonical source target` + `canonical lexical-root descendants` + `canonical bundle descendants`，显式阻断 source target directory siblings 与 symlink escape
- Markdown Visual Preview Task 5（Reviewer Request changes / Important）：secure fallback 不再提前卸载 interceptor；fallback 仅原子清 scripts/channel 并禁用 JS，继续由 interceptor 约束 fallback 期间绝对 `file:` 子资源；仅在 `shutdown()` 才 detach interceptor
- Markdown Visual Preview Task 5（Reviewer Request changes / Minor）：补充回归 `tests/test_md_view.py`：source-resolve 指向他处时 lexical root 仍生效、target sibling 继续阻断、`qrc/data/blob` 允许、commonpath prefix collision 阻断
- Markdown Visual Preview Task 5（Reviewer 修复验证）：RED `python -m pytest tests/test_md_view.py -v` 复现 `3 failed`（lexical root 与 fallback interceptor 时序）；GREEN 同命令 `23 passed`；PPTX 回归 `17 passed`；Python 全量 `298 passed, 1 skipped`
- Markdown Visual Preview Task 6：`MainWindow` 默认 viewer factory 新增 `kind="markdown" -> MarkdownVisualView`，`.md` 初始模式切换为 `visual`，并保持 `.pptx` 默认视觉模式不变
- Markdown Visual Preview Task 6：visual 可选信号接线扩展到 `open_path` / `missing_link`，统一记录在 `visual_connections` 并复用 generation/document/widget/layout guard；resolved wikilink 通过 `open_paths([path])` 打开/复用标签页，missing 仅更新状态 `找不到：{target}`
- Markdown Visual Preview Task 6：`_visual_ready` 仅在 `kind="pptx"` 时写入 `append_visual_ready`；Markdown ready 不写 PPTX telemetry
- Markdown Visual Preview Task 6 验证：Task6 聚焦 RED `5 failed, 1 passed` -> GREEN `6 passed`；窗口全量 `99 passed`；`tests/test_md_view.py` `23 passed`；Python 全量 `304 passed, 1 skipped`
- Markdown Visual Preview Task 7：新增真实夹具 `tests/fixtures/md/visual-document.md`（heading/table/python/valid+invalid Mermaid/relative image/resolved+missing wikilink/remote probes）、`linked-note.md` 与真实 PNG `diagram.png`，并新增 `tests/test_md_webengine.py` 基于真实 `assets/md-viewer` + `MarkdownVisualView` 验证 Chromium fidelity
- Markdown Visual Preview Task 7（严格 TDD）：RED `python -m pytest tests/test_md_webengine.py -v` 为 `1 failed, 1 passed`（missing wiki click 未触发 `missing_link`）；先补 web 单测回归 RED `npm test -- src/viewer.test.ts` 为 `2 failed, 5 passed`，最小修复 `startViewer` 始终透传 wiki click 到 `openWiki`，GREEN 后 `src/viewer.test.ts` `7 passed`、Task7 真实 WebEngine `2 passed`
- Markdown Visual Preview Task 7（网络阻断与生命周期）：测试在注入前断言 `blocked_urls()==()`，临时开启 `LocalContentCanAccessRemoteUrls` 后注入 HTTP/HTTPS/WS/WSS，断言拦截器精确记录并阻断 4 项；所有真实 QWebEngine 用例统一严格 timeout + `finally shutdown()` 并等待 profile invalid，避免残留进程
- Markdown Visual Preview Task 7 验证：`npm test` `21 passed`；`tests/test_md_view.py` `23 passed`；`tests/test_pptx_webengine.py` `3 passed`；Python 全量 `306 passed, 1 skipped`
- Markdown Visual Preview Task 8：`reader.spec` 收集 `assets/md-viewer`；`build_windows.ps1` 对 pptx/md 两套 bundle 执行 `npm ci/test/typecheck/build`、通用 `Test-WebBundleManifest`、冻结资源与哈希校验
- Markdown Visual Preview Task 8：frozen smoke 拆成 Phase A PPTX、Phase B Markdown（`kind=markdown` ready）、Phase C IPC；窗口 ready 对 Markdown 写 `append_markdown_ready`，不改 PPTX `slides=4`
- Markdown Visual Preview Task 8 验证：Web md-viewer `21 passed`、pptx-viewer `28 passed`；Python 全量 `309 passed, 1 skipped`；`build_windows.ps1` exit 0；smoke PPTX `slides=4` + Markdown `kind=markdown` + 两批 IPC
- Markdown Visual Preview source/frozen md-viewer manifest SHA256 均为 `3685badafff19d10a7cc5b57675a0e4fa946df4d0202f22b4e55178059d2f667`；pptx manifest SHA256 均为 `1f165ff62ea65b671d164b738fdd0f9ec599527149333400d69c0633d967e8fb`
- 最终 `dist/Reader/Reader.exe`：`5896314 bytes`，SHA256 `4a4426d5547a1d99a4a4c91e3c4bd46a448e84fb0d12a9c27244c76115894b4d`；桌面 `Reader.lnk` 已刷新并验证 target/workdir/icon

## 下一步

1. 用户双击 `.docx` / `.md` / `.pdf` 确认都进 Reader
2. 同事：clone 后执行 `scripts\setup.ps1` 启动 Reader
3. 若还要 File / Edit / View 菜单行，再开规格

## 已完成（本增量）

- 默认打开方式：当前用户把 Reader 支持的文档后缀（含 `.pdf`）指到 `Reader.Document`；UCPD 锁住的 PDF 经 Settings UI 申索；全量 `386 passed, 1 skipped`；桌面 `Reader.lnk` 已覆盖刷新
- 文档 Ctrl+F：标题栏下查找条，Enter/F3 下一个，Esc 关闭；`tests/test_find.py` 5 passed；frozen smoke 通过；桌面 `Reader.lnk` 已覆盖刷新
- 代码文件阅读：`.json` / `.yaml` / `.yml` / `.xml` 只读行号视图 + `QSyntaxHighlighter`；全量 `377 passed, 1 skipped`；frozen smoke PPTX/MD/IPC 通过；桌面 `Reader.lnk` 已覆盖刷新
- 0.1.0 源码启动：`VERSION` + `scripts/setup.ps1` + 中文 README / `release/README.md`；git 不含 exe/zip
- Native PDF 空白修复：PDF 标签启用 Chromium PDF 插件；HTML 预览不启用插件
- Native PDF Task 1：`.pdf` 进入 sniff / pipeline / Open With；`to_preview` 指向源文件且 `asset_dir is None`
- Native PDF Task 2：源路径相同时不 pin、不进预览缓存；Office 缓存 PDF 仍 pin；打开对话框含 `*.pdf`
- Native PDF Task 3：全量 `341 passed, 1 skipped`；`build_windows.ps1` + smoke PPTX/MD/IPC 通过；桌面 `Reader.lnk` 已覆盖刷新
- Windows hashed-bundle LF：`.gitattributes` `eol=lf`；构建脚本 `WriteAllBytes` 写 LF manifest
- Markdown Visual-Default Task 1：已有 `.md` 默认视觉打开；未命名仍可编辑
- Markdown Visual-Default Task 2：Ctrl+I 进编辑，Ctrl+T 回渲染并强制保存
- Markdown Visual-Default Task 3：冻结构建 + smoke PPTX/MD/IPC + 桌面快捷方式刷新
- Notepad Cold-Open Icon Task 1：frame restore/`LayoutRequest` 后 stretch 编辑区；HWND `WM_SETICON` 重设 `reader.ico`；flush/icon 测试覆盖冷启动回归
- Notepad Cold-Open Icon Task 2：冻结构建 + smoke PPTX/MD/IPC + 桌面快捷方式刷新
- Notepad Seamless Chrome Task 1：caption/图标按下调用 `startSystemMove`；`+`/窗控不拖窗；DPI 校正 `WM_NCHITTEST`
- Notepad Seamless Chrome Task 2：chrome/标签页/编辑器统一 `#ffffff`；去掉表头底边与编辑框；隐藏状态栏，`status_text()` 仍可用
- Notepad Seamless Chrome Task 3：冻结构建 + smoke + 桌面快捷方式刷新
- Markdown Edit Chrome Task 1：整段 chrome（除标签/`+`/窗控）`HTCAPTION`；默认尺寸 `1200×640`、最小 `(800, 400)`；已推送 `39f27f4`
- Markdown Edit Chrome Task 2：`MarkdownTextView` UTF-8 快显只读→点击编辑；`.md` 默认文本编辑；`Ctrl+S` 有路径覆盖 / 无路径另存为；视觉 MD 仍可切换
- Markdown Edit Chrome Task 3：无文件启动与 `+` 默认 `未命名.md` 可编辑草稿；零标签时显示空窗口提示
- Markdown Edit Chrome Task 4：`warmup_webengine` 幂等预热；首窗 `QTimer.singleShot(0, ...)` 调度
- Markdown Edit Chrome Task 2–4 验证：全量 `321 passed, 1 skipped`；已推送 `7f7a465`
- Markdown Edit Chrome Task 5：`READER_SMOKE_MD_VISUAL` 保留冻结 Markdown 视觉认证；`build_windows.ps1` + smoke PPTX/MD/IPC 通过；桌面 `Reader.lnk` 已刷新
- Notepad Title Bar Task 1：隐藏菜单栏与标签栏「打开」按钮；空白提示改为 `拖入文件，或按 Ctrl+O 打开`；`Ctrl+O`/`actionNewTab`/预览 QAction 保留为窗口动作
- Notepad Title Bar Task 2：新增 `TitleChrome`，把 `QTabBar` 重排到单行 chrome（图标 | 标签 | + | 标题拖拽区）；`+` 紧跟末标签
- Notepad Title Bar Task 3：无边框窗口 + 自绘最小化/最大化/关闭按钮，状态切换刷新最大化图标
- Notepad Title Bar Task 4：`hit_test_for_window` + `nativeEvent` 处理 `WM_NCHITTEST`/`WM_NCCALCSIZE`（标题拖拽、边缘缩放、最大化按钮 HTMAXBUTTON）
- Notepad Title Bar Task 5：全量回归、冻结构建、smoke、桌面快捷方式刷新完成

## 阻塞项

- 2026-08-28 Markdown Task 7 同步状态：controller 已成功 owner push `HEAD`（`4b74767`），当前 `main` 与 `origin/main` 已同步，Task 7 push blocker 已关闭。
- 2026-08-28 Markdown Task 5 Reviewer 修复同步状态：controller 已成功推送 `ac8d6a2`（含 `408440b`），当前 `main` 与 `origin/main` 已同步，reviewer 修复 push blocker 已关闭。
- 2026-08-28 Markdown Task 5 同步状态：controller 已使用 owner credential 成功推送 `08f5ef8`（含 `89cbc7a`），当前 `main` 与 `origin/main` 已同步，Task 5 push blocker 已关闭。
- 2026-08-28 Markdown Task 4 同步状态：controller 已使用 owner helper 成功推送 `2929a6f`，当前 `main` 与 `origin/main` 已同步，先前 push blocker 已关闭。

## 接手检查清单

1. 读本文件与当前规格/计划  
2. `git log -15 --oneline` 与 `git status`  
3. 未推送的提交先推送，再改代码  
4. 改完更新本文件的「当前目标 / 已完成 / 下一步」，再提交推送  
