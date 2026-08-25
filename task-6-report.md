# PPTX Task 6 Report: Window Integration, Manual Text Mode, and Lifecycle

## 状态

完成。基于 `d87aa047a58ef33f24c93151fd22fca08e257c77`，严格执行 TDD RED→GREEN；按用户指令提交但不推送、不修改 git config。

## 交付

- `src/reader/shell/window.py`
  - 默认 viewer factory 对 `PreviewResult.kind == "pptx"` 创建 `PptxVisualView`。
  - `_install_document_content(...)` 统一校验 document identity、generation、closing 和 tab/widget 归属，替换内容后先绑定事件再调用 `start()`。
  - `_dispose_widget(...)` 统一调用可选 `shutdown()`，随后解除父子关系并 `deleteLater()`。
  - `actionTextPreview` / `actionVisualPreview` 仅服务 PPTX 手动模式切换。
  - `_Document.builtin_mode` 记录最近的 visual/text；Office 切回恢复该模式，Office 失败保留当前 widget/result 并恢复原 builtin mode。
  - visual `render_failed` 保持 `mode=builtin_mode=visual`，由 `PptxVisualView` 已展示的内部 fallback 承载内容，窗口状态更新为 `内置预览（视觉渲染失败）`。
  - ready、slide_changed、render_failed 均使用 generation + widget + mode + closing guard；迟到事件不改变当前文档。
  - 标签关闭、窗口关闭、切 Office、切文本/视觉都显式 shutdown visual。
- `tests/test_window.py`
  - 新增默认工厂、bind-before-start、视觉 fallback、手动文本/视觉、独立 text cache、Office 成功/失败/切回、关闭/重入、迟到 ready/slide/failure 等生命周期覆盖。
- `docs/STATUS.md`
  - Task 6 标记完成，下一步切换为 Task 7。

## TDD 与验证记录

- RED：
  - `.venv\Scripts\python.exe -m pytest tests/test_window.py -k "visual or text_mode or office_failure_preserves or shutdown_visuals" -v`
  - `10 failed, 1 passed`；失败点为默认 PPTX 工厂、动作、start、shutdown、事件状态等缺失，符合预期。
- GREEN（首次完整窗口）：
  - `.venv\Scripts\python.exe -m pytest tests/test_window.py -v`
  - `77 passed`。
- 补齐文本 Office 共存及启动重入覆盖后：
  - `.venv\Scripts\python.exe -m pytest tests/test_window.py -q`
  - `80 passed`。
- 全量：
  - `.venv\Scripts\python.exe -m pytest -v`
  - `237 passed`。
- 静态检查：
  - IDE lint：无错误。
  - `git diff --check`：通过。

## 需求核对

- [x] 默认 PPTX 创建 `PptxVisualView`，bundle 路径由 view 内 `resource_path(...)` 解析
- [x] worker、Office→builtin 恢复和错误内容均走统一安装路径
- [x] 所有已安装内容替换及 tab/window 关闭走统一销毁路径
- [x] `shutdown()` 先于 `deleteLater()`
- [x] visual/text builtin mode 持久化并与 Office 共存
- [x] Office 失败保留当前 visual fallback 或手动 text 内容
- [x] 手动 text 使用独立缓存；回 visual 创建并启动新 view
- [x] visual 整体失败状态精确且不误改为手动 text
- [x] ready/slide/failure 迟到事件受 generation/widget/closing guard
- [x] Task 5 的 MainWindow 集成边界完成

## 提交策略

按本次明确指令：创建本地提交，不执行 push，不修改 git config。
