# Reader 项目状态（AI 接手必读）

最后更新：2026-08-25  
Git：`main` 应与 `origin/main` 同步；功能边界必须提交并推送。

## 背景

Reader 是 Windows 桌面文档查看器（PySide6）。v1 已支持 `.docx` / `.pptx` / `.xlsx` / `.md`，标签页、内置预览优先、可选 Office COM 高保真、单实例 IPC、PyInstaller onedir `dist/Reader/Reader.exe`、透明蓝色 R 图标。

内置 PPTX 目前仍是 `python-pptx` 抽文本重画 HTML，丢失版式与图片。用户要求默认预览接近 Cursor 插件 PPTX Viewer：真实幻灯片画布，而不是大纲。

## 当前目标（进行中）

**PPTX 视觉预览（不依赖 PowerPoint）：Task 4 待实施**

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

## 下一步

1. 按计划推进 PPTX Visual Preview Task 4：新增 visual/text 结果模式与 cache contract，并延续任务级 TDD  
2. Task 5 接入 `QWebEngineView` 与 Python bridge 后，再执行真实产品链路及 frozen smoke  
3. 全部视觉预览任务完成后重建 `dist/Reader/Reader.exe`，按需更新桌面快捷方式  

## 接手检查清单

1. 读本文件与当前规格/计划  
2. `git log -15 --oneline` 与 `git status`  
3. 未推送的提交先推送，再改代码  
4. 改完更新本文件的「当前目标 / 已完成 / 下一步」，再提交推送  
