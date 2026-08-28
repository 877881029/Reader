# Reader 项目状态（AI 接手必读）

最后更新：2026-08-28
Git：`main` 应与 `origin/main` 同步；功能边界必须提交并推送。

## 背景

Reader 是 Windows 桌面文档查看器（PySide6）。v1 已支持 `.docx` / `.pptx` / `.xlsx` / `.md`，标签页、内置预览优先、可选 Office COM 高保真、单实例 IPC、PyInstaller onedir `dist/Reader/Reader.exe`、透明蓝色 R 图标。

内置 PPTX 默认已切换为本地 WebEngine 视觉渲染；`python-pptx` 文本 HTML 保留为手动模式和视觉失败回退。

## 当前目标（进行中）

**Markdown 视觉预览：主题、离线 Mermaid、同目录双链开新标签**

- 规格：`docs/superpowers/specs/2026-08-28-markdown-visual-preview-design.md`（用户已批准）
- 计划：`docs/superpowers/plans/2026-08-28-markdown-visual-preview.md`（8 个 TDD 任务，Task 1 已完成）
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

## 下一步

1. 继续 Markdown Visual Preview Task 6（MainWindow 生命周期接线、`kind="markdown"` viewer factory 与 wikilink 开新标签集成）
2. 维持每个任务边界更新 STATUS、提交并推送 `origin/main`
3. 在 Markdown 全部任务完成后执行全量回归、重建冻结 Reader 并按需刷新桌面快捷方式

## 阻塞项

- 2026-08-28 Markdown Task 5 同步状态：本地提交 `89cbc7a` 已生成并通过验证；`git push origin main` 返回 GitHub 403（`Permission to 877881029/Reader.git denied to runqyang_amdeng`），owner helper `git_push(confirm=true)` 返回 `Pushing is blocked on protected branch 'main'`；当前 `main` 暂时 `ahead 1`，待仓库 owner 协助推送或放开策略。
- 2026-08-28 Markdown Task 4 同步状态：controller 已使用 owner helper 成功推送 `2929a6f`，当前 `main` 与 `origin/main` 已同步，先前 push blocker 已关闭。

## 接手检查清单

1. 读本文件与当前规格/计划  
2. `git log -15 --oneline` 与 `git status`  
3. 未推送的提交先推送，再改代码  
4. 改完更新本文件的「当前目标 / 已完成 / 下一步」，再提交推送  
