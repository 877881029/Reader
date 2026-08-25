# Reader 项目状态（AI 接手必读）

最后更新：2026-08-25  
Git：`main` 应与 `origin/main` 同步；功能边界必须提交并推送。

## 背景

Reader 是 Windows 桌面文档查看器（PySide6）。v1 已支持 `.docx` / `.pptx` / `.xlsx` / `.md`，标签页、内置预览优先、可选 Office COM 高保真、单实例 IPC、PyInstaller onedir `dist/Reader/Reader.exe`、透明蓝色 R 图标。

内置 PPTX 目前仍是 `python-pptx` 抽文本重画 HTML，丢失版式与图片。用户要求默认预览接近 Cursor 插件 PPTX Viewer：真实幻灯片画布，而不是大纲。

## 当前目标（进行中）

**PPTX 视觉预览（不依赖 PowerPoint）**

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
- PPTX Visual Preview Task 1：完成确定性 Web scaffold 与许可基线（`web/pptx-viewer`、锁定 `pptx-viewer@0.2.2`、唯一 runtime 传递依赖 `fflate`、`THIRD_PARTY_NOTICES.txt`、输出到 `assets/pptx-viewer/`）

## 下一步

1. 按计划推进 PPTX Visual Preview Task 2（桥接协议与离线加载基线），延续每任务 TDD、独立审查、提交并推送 `origin/main`  
2. 全量回归并重建 `dist/Reader/Reader.exe`  
3. 验证 PPTX 视觉 frozen smoke，更新桌面快捷方式  

## 接手检查清单

1. 读本文件与当前规格/计划  
2. `git log -15 --oneline` 与 `git status`  
3. 未推送的提交先推送，再改代码  
4. 改完更新本文件的「当前目标 / 已完成 / 下一步」，再提交推送  
