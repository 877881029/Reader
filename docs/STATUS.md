# Reader 项目状态（AI 接手必读）

最后更新：2026-08-25  
Git：`main` 应与 `origin/main` 同步；功能边界必须提交并推送。

## 背景

Reader 是 Windows 桌面文档查看器（PySide6）。v1 已支持 `.docx` / `.pptx` / `.xlsx` / `.md`，标签页、内置预览优先、可选 Office COM 高保真、单实例 IPC、PyInstaller onedir `dist/Reader/Reader.exe`、透明蓝色 R 图标。

内置 PPTX 目前仍是 `python-pptx` 抽文本重画 HTML，丢失版式与图片。用户要求默认预览接近 Cursor 插件 PPTX Viewer：真实幻灯片画布，而不是大纲。

## 当前目标（进行中）

**PPTX 视觉预览（不依赖 PowerPoint）：Task 6 已完成，Task 7 待实施**

- 规格：`docs/superpowers/specs/2026-08-25-pptx-visual-preview-design.md`（已批准）
- 计划：`docs/superpowers/plans/2026-08-25-pptx-visual-preview.md`（已完成并通过计划审查，9 个 TDD 任务）
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
- PPTX Visual Preview Task 6 按本次用户指令只提交、不推送；本地提交将领先 `origin/main`

## 下一步

1. 按计划推进 PPTX Visual Preview Task 7：真实 WebEngine fidelity/offline 测试
2. Task 7 完成后推进 frozen resource/build 与独立视觉 smoke
3. 全部视觉预览任务完成后重建 `dist/Reader/Reader.exe`，按需更新桌面快捷方式  

## 接手检查清单

1. 读本文件与当前规格/计划  
2. `git log -15 --oneline` 与 `git status`  
3. 未推送的提交先推送，再改代码  
4. 改完更新本文件的「当前目标 / 已完成 / 下一步」，再提交推送  
