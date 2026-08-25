# Task 1 Report - Deterministic Web Scaffold and Licensing (Review Fixes)

## 范围

- 仅记录本次对 PPTX Visual Preview Task 1 的审查修复与验证。
- 不包含其他历史任务内容。

## 审查修复项

1. 固定 Node 18 兼容且互相兼容的 dev 工具链精确版本（无 `^`/`~`）：
   - `vite@5.4.19`
   - `vitest@2.1.9`
   - `jsdom@24.1.3`
   - `typescript@5.9.2`
   - `@types/node@22.13.14`
2. 保持 `engines.node` 为 `>=18`，重建 lock 并执行 `npm ci`。
3. `fflate` 版本由 lock 实际解析为 `0.8.3`，许可证标题修正为 `fflate 0.8.3`，并保留 MIT 全文。
4. Python 测试改为从 lock 读取 `fflate` 实际版本并断言 notice 包含该版本，不再硬编码 `0.8.2`。
5. Web scaffold 测试升级为有价值断言：验证 `#app` 挂载点与 `main.ts` 不含远程 import。
6. `src/main.test.ts` 替换 `expect(true)`，改为离线本地 bootstrap 约束断言。

## 兼容性核验（npm view）

命令：

`npm view vite@5.4.19 engines --json`
`npm view vitest@2.1.9 engines --json`
`npm view jsdom@24.1.3 engines --json`
`npm view typescript@5.9.2 engines --json`

输出要点：

- vite: `^18.0.0 || >=20.0.0`
- vitest: `^18.0.0 || >=20.0.0`
- jsdom: `>=18`
- typescript: `>=14.17`

结论：上述版本满足 Node 18 约束。

## 严格 TDD 记录

### RED（先改测试）

命令：

`.\.venv\Scripts\python.exe -m pytest tests/test_pptx_web_assets.py -v`

结果（失败，符合预期）：

- `test_locked_supply_chain_and_node_floor` 失败（devDependencies 非精确且版本不符）
- `test_two_complete_mit_notices_and_ignore` 失败（notice 标题仍是 `fflate 0.8.2`）

### GREEN（修复后）

命令：

1. `npm ci --prefix web/pptx-viewer`
2. `npm --prefix web/pptx-viewer run test`
3. `npm --prefix web/pptx-viewer run typecheck`
4. `npm --prefix web/pptx-viewer run build`
5. `.\.venv\Scripts\python.exe -m pytest tests/test_pptx_web_assets.py -v`
6. `.\.venv\Scripts\python.exe -m pytest -v`

结果：

- npm test: `1 passed`
- npm typecheck: 通过
- npm build: 通过，产物输出至 `assets/pptx-viewer/`
- focused pytest: `4 passed`
- full pytest: `203 passed`

## 关键变更文件

- `web/pptx-viewer/package.json`
- `web/pptx-viewer/package-lock.json`
- `web/pptx-viewer/THIRD_PARTY_NOTICES.txt`
- `web/pptx-viewer/src/main.test.ts`
- `tests/test_pptx_web_assets.py`
- `docs/STATUS.md`

## 自审

- 已遵循“先 RED 后实现后 GREEN”。
- runtime 依赖名仍仅为 `fflate`（来自 `pptx-viewer` 传递依赖）。
- 未修改 git config，未 amend，未 push。
- “push 由 controller 审查后执行”属于流程约束，不是实现缺陷。

## 顾虑

- `npm ci` 报告上游生态漏洞（3 条）；本任务为脚手架与许可锁定，不在本次修复范围。
# Task 1 Report - Deterministic Web Scaffold and Licensing

## Scope

- Task: Reader PPTX Visual Preview Task 1.
- Baseline intent: deterministic offline web scaffold and license compliance.
- Working directory: `C:\Research\AgentDevelopor\READER`.

## TDD Evidence

### RED

Command:

`.\.venv\Scripts\python.exe -m pytest tests/test_pptx_web_assets.py -v`

Result (expected fail):

- `collected 3 items`
- `FAILED tests/test_pptx_web_assets.py::test_locked_supply_chain_and_node_floor`
- `FAILED tests/test_pptx_web_assets.py::test_two_complete_mit_notices_and_ignore`
- `FAILED tests/test_pptx_web_assets.py::test_vite_uses_jsdom_and_relative_bundle`
- Root cause: scaffold files did not exist yet (`FileNotFoundError` under `web/pptx-viewer/`).

### GREEN

Commands run:

1. `npm --prefix web/pptx-viewer run test`
2. `npm --prefix web/pptx-viewer run typecheck`
3. `npm --prefix web/pptx-viewer run build`
4. `.\.venv\Scripts\python.exe -m pytest tests/test_pptx_web_assets.py -v`
5. `.\.venv\Scripts\python.exe -m pytest -v`

Results:

- npm test: `Test Files 1 passed (1), Tests 1 passed (1)`
- npm typecheck: pass (`tsc --noEmit` exit 0)
- npm build: pass; Vite wrote deterministic output to `assets/pptx-viewer/`
- focused pytest: `3 passed`
- full pytest: `202 passed`

## Dependency and License Baseline

- Runtime dependency pinned: `pptx-viewer@0.2.2` (exact).
- Transitive runtime dependency asserted in lock: `fflate` from `pptx-viewer` dependency map (`^0.8.2`).
- Dev toolchain installed for deterministic local build/test: `vite`, `typescript`, `vitest`, `jsdom`, `@types/node`.
- `THIRD_PARTY_NOTICES.txt` includes two complete MIT license texts:
  - `pptx-viewer 0.2.2` copyright `2025`
  - `fflate 0.8.2` copyright `2023 Arjun Barrett`
- No `astx-jp` proprietary content referenced or copied.

## Files Changed

- Added: `tests/test_pptx_web_assets.py`
- Added: `web/pptx-viewer/package.json`
- Added: `web/pptx-viewer/package-lock.json`
- Added: `web/pptx-viewer/tsconfig.json`
- Added: `web/pptx-viewer/vite.config.ts`
- Added: `web/pptx-viewer/index.html`
- Added: `web/pptx-viewer/src/main.ts`
- Added: `web/pptx-viewer/src/style.css`
- Added: `web/pptx-viewer/src/vite-env.d.ts`
- Added: `web/pptx-viewer/src/main.test.ts`
- Added: `web/pptx-viewer/THIRD_PARTY_NOTICES.txt`
- Added (build output): `assets/pptx-viewer/index.html`, `assets/pptx-viewer/assets/*`
- Updated: `.gitignore` (append `web/pptx-viewer/node_modules/`)
- Updated: `docs/STATUS.md` (Task 1 completed + next step)

## Self-Review

- Confirmed RED before implementation.
- Confirmed required lock + jsdom + relative base constraints via focused pytest.
- Confirmed scaffold remains offline-first and does not introduce remote/network runtime dependencies.
- Confirmed no git config changes and no push performed in this task.

## Concerns / Follow-up

- Current `fflate` package license file in installed dependency may display a newer copyright year than the task brief expectation; task tests enforce `2023 Arjun Barrett` and pass against the committed notice.
- Build artifact filenames are hash-based and deterministic for fixed inputs/toolchain; future dependency/toolchain updates will change hashes by design.
# Task 1 Report: Window Geometry and Application Icon

## 实现内容

基于 `task-1-brief.md` 完成了窗口几何和图标加载改造，并保证图标资产缺失时安全 no-op：

- `src/reader/shell/window.py`
  - 新增 `MainWindow.DEFAULT_SIZE = (1200, 800)`、`MainWindow.MINIMUM_SIZE = (800, 500)`
  - `__init__` 中应用默认尺寸与最小尺寸
  - 新增 `center_on_screen(offset: int = 0)`，按屏幕可用区域居中并叠加偏移
  - 新增 `_window_icon_path()` 与 `_load_icon_if_exists(...)`
  - 图标加载支持测试注入：`icon_path_provider`、`icon_applier`
- `src/reader/app.py`
  - 新增 `_reader_icon_path()` 与 `_load_icon_if_exists(...)`
  - `ReaderApp.__init__` 增加图标注入接口：`icon_path_provider`、`icon_applier`
  - `new_window()` 接入 `_place_window(window)`，第二个及之后窗口偏移 `(32, 32)`
  - 新增 `ReaderApp._place_window(window: MainWindow) -> None`
  - `set_app_user_model_id` 增加可注入 `setter`，稳定 Windows 分支测试
- `tests/test_window.py`
  - 新增几何测试：
    - `test_main_window_default_size_and_minimum`
    - `test_new_window_offsets_from_existing_window`
  - 新增图标 no-op/注入测试：
    - `test_main_window_icon_loading_supports_injected_path`
    - `test_reader_app_icon_loading_supports_injected_path`
  - 调整 `test_app_user_model_id_uses_reader_desktop_on_windows` 使用注入 setter

## RED/GREEN 命令与输出

### RED（先写失败测试）

命令：

`python -m pytest tests/test_window.py::test_main_window_default_size_and_minimum tests/test_window.py::test_new_window_offsets_from_existing_window -v`

输出（节选）：

```
tests/test_window.py::test_main_window_default_size_and_minimum FAILED
tests/test_window.py::test_new_window_offsets_from_existing_window FAILED
E       assert 640 == 1200
E       assert QPoint(...) == QPoint(...) + QPoint(32, 32)
```

结论：符合预期 RED（默认窗口尺寸与新窗口偏移尚未实现）。

### GREEN（最小实现后）

命令：

`python -m pytest tests/test_window.py::test_main_window_default_size_and_minimum tests/test_window.py::test_new_window_offsets_from_existing_window -v`

输出：

```
tests/test_window.py::test_main_window_default_size_and_minimum PASSED
tests/test_window.py::test_new_window_offsets_from_existing_window PASSED
============================== 2 passed in 7.31s ==============================
```

### 图标相关新增测试

命令：

`python -m pytest tests/test_window.py::test_main_window_icon_loading_supports_injected_path tests/test_window.py::test_reader_app_icon_loading_supports_injected_path -v`

输出：

```
tests/test_window.py::test_main_window_icon_loading_supports_injected_path PASSED
tests/test_window.py::test_reader_app_icon_loading_supports_injected_path PASSED
============================== 2 passed in 6.40s ==============================
```

### 全量回归

命令：

`python -m pytest -q`

输出：

```
100 passed in 16.75s
```

## 变更文件

- `src/reader/app.py`
- `src/reader/shell/window.py`
- `tests/test_window.py`
- `.superpowers/sdd/task-1-report.md`

## 自审

- [x] 严格执行 TDD：先 RED，再最小实现，再 GREEN，再全量测试
- [x] `MainWindow` 默认尺寸、最小尺寸、居中偏移接口与 brief 一致
- [x] `ReaderApp._place_window(window)` 已接入 `new_window()` 流程
- [x] 图标路径缺失时安全 no-op，不依赖最终资产存在
- [x] 图标行为可通过注入接口 + 临时文件进行验证
- [x] 未引入 git config 变更，未 push

## 顾虑

1. 当前图标测试验证“存在即尝试加载/不存在即不加载”，不校验图标文件内容有效性（符合本任务范围）。
2. 图标最终视觉资产仍待 Task 5 生成；当前实现在资产缺失时保持静默安全行为。

## Task 1 审查修复（Important）

### 问题

`ReaderApp._place_window()` 原实现对所有第二及后续窗口使用固定 `offset=32`，导致第三窗口与第二窗口完全重叠。

### 修复

- 新增 RED 用例：`test_new_window_offsets_increment_for_third_window`
  - 验证 `first/second/third` 三窗口均不重叠
  - 验证 `second = first + (32, 32)`
  - 验证 `third = second + (32, 32)`
- 最小实现：将 `_place_window()` 偏移改为 `max(0, len(self._windows) - 1) * 32`，按窗口序号递增。

### 修复 RED/GREEN 记录

RED 命令：

`python -m pytest tests/test_window.py::test_new_window_offsets_increment_for_third_window -v`

RED 输出（节选）：

```
tests/test_window.py::test_new_window_offsets_increment_for_third_window FAILED
E       assert QPoint(152, 222) != QPoint(152, 222)
```

GREEN 命令：

`python -m pytest tests/test_window.py::test_new_window_offsets_from_existing_window tests/test_window.py::test_new_window_offsets_increment_for_third_window -v`

GREEN 输出：

```
tests/test_window.py::test_new_window_offsets_from_existing_window PASSED
tests/test_window.py::test_new_window_offsets_increment_for_third_window PASSED
============================= 2 passed in 11.01s ==============================
```

全量回归命令：

`python -m pytest -q`

全量输出：

```
101 passed in 26.20s
```
