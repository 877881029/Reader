# PPTX Task 8 报告：Frozen Resources and Native Fail-Fast Build

## 状态

完成。基线 `238a3f711e2a0dbb25052afd7f4daffe042756f0`。

## TDD 记录

- 初始 RED：
  `.venv\Scripts\python.exe -m pytest tests/test_packaging.py tests/test_pptx_web_assets.py -v`
  - 结果：`4 failed, 13 passed`。
  - 预期失败：spec 未收集 QtWebChannel/PPTX bundle，构建脚本无原生 npm
    fail-fast，manifest 尚不存在。
- 原生失败传播 RED/GREEN：
  - fake `npm.cmd` 返回 23；断言只收到 `ci --prefix web\pptx-viewer`，
    sentinel dist 文件未被删除。
  - 首版测试通过后，真实 npm 位于 `C:\Program Files\nodejs`，clean build 复现
    `C:\Program is not recognized`；将 fake npm 移入含空格目录后自动化 RED 稳定复现。
  - 使用 `cmd /d /s /c call "...\npm.cmd"` 后 GREEN。
- manifest 兼容性 RED/GREEN：
  - Windows PowerShell/.NET Framework 无 `[IO.Path]::GetRelativePath`，真实构建在
    PyInstaller 前退出。
  - 改为已解析 bundle 根目录的受控前缀截取，并以
    `[StringComparer]::Ordinal` 排序相对路径。
- 最终聚焦：`19 passed`。
- Python 全量：`251 passed in 72.89s`。

## 实现覆盖

- `reader.spec`
  - 收集整个 `assets/pptx-viewer`，包括 HTML/JS/CSS、第三方 notice 和 manifest。
  - 显式加入 `collect_submodules('PySide6.QtWebChannel')`。
- `scripts/build_windows.ps1`
  - 最先 `Get-Command node.exe` / `npm.cmd`，要求 Node.js 18+。
  - 在 Python/PyInstaller 前依次原生运行 `npm ci` 和 `npm run build`；后者包含
    typecheck。
  - 使用 `$process.ExitCode` 严格传播 npm 失败。
  - 构建后复制 notice、按 ordinal 路径顺序生成并立即验证 `manifest.sha256`。
  - PyInstaller 后验证 frozen index/notice/manifest、QtWebChannel `.pyd`，并根据
    frozen manifest 逐文件复算 SHA256。
- 普通 pytest 配置无 npm session/config hook；npm 只在显式生产构建或隔离 fake
  失败测试中执行。

## 真实 clean build

命令：

`powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1`

最终结果：exit 0，`Build complete`，总耗时约 396 秒。

确认存在：

- `dist/Reader/Reader.exe`
- `dist/Reader/_internal/assets/pptx-viewer/index.html`
- `dist/Reader/_internal/assets/pptx-viewer/assets/index-C2nkv8va.js`
- `dist/Reader/_internal/assets/pptx-viewer/assets/index-LoyaVShE.css`
- `dist/Reader/_internal/assets/pptx-viewer/THIRD_PARTY_NOTICES.txt`
- `dist/Reader/_internal/assets/pptx-viewer/manifest.sha256`
- `dist/Reader/_internal/PySide6/QtWebChannel.pyd`

源与 frozen `manifest.sha256` 文件的 SHA256 均为
`f6f32aa6416717bb47aebcd4f365cc976dd01c24d86a8e768a12b70042fc2633`。

## Important / Minor 审查修复

### 严格 RED

命令：

`$env:READER_RUN_NPM_BUILD_TEST='1'; .venv\Scripts\python.exe -m pytest tests/test_packaging.py tests/test_pptx_web_assets.py -v`

结果：`3 failed, 17 passed`。

- 构建脚本没有从 `npm.cmd` 目录选择 `node.exe`，静态契约失败。
- source/frozen manifest 没有共用严格格式与空行 guard，静态契约失败。
- 进程集成将真实 `node.exe` 同时复制到 PATH 首目录和 fake npm 目录；原脚本没有输出
  npm-relative Node 路径，选择证据断言失败。
- Vite `outDir`、`emptyOutDir: true` 与植入 stale asset 后的真实 build 删除行为已存在，
  两项 Minor 在 RED 轮直接通过。

### 修复

- 先解析 `npm.cmd`，若同目录存在 `node.exe` 则使用其解析后路径；只有同目录 Node
  不存在时才回退 `Get-Command node.exe`。
- 用选定路径运行 `--version`；版本命令失败、格式无效或 major 小于 18 时，错误均包含
  实际 Node 路径。构建同时输出 `Using Node.js from <path>` 作为真实选择证据。
- fake npm 进程测试令另一个 Node 目录位于 PATH 首位，并断言日志明确选择 fake npm
  同目录 Node；fake npm 仍返回 23，dist sentinel 保留，PyInstaller 前 fail-fast 不变。
- source/frozen bundle 都通过同一个 `Test-PptxManifest` 验证器，拒绝空行和不符合
  `64 lowercase hex + two spaces + relative path` 的条目。
- Vite stale asset 测试仅在 `READER_RUN_NPM_BUILD_TEST=1` 时运行；它在 `finally`
  恢复完整 bundle。普通 pytest 默认 skip，因此不会调用真实 npm。

### 审查后验证

- 显式 npm 聚焦：`20 passed in 57.24s`。
- 普通全量（显式移除 opt-in 环境变量）：`251 passed, 1 skipped in 92.87s`。
- 首轮全量暴露既有 Office availability 双 queued signal 测试竞态：
  `office.calls` 已写入但最终 tooltip 尚未更新；定向连续复现后，将测试等待条件收紧为
  最终 tooltip，定向 `1 passed`，随后全量通过。未改窗口产品代码。
- clean build：
  `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1`
  exit 0；输出明确记录
  `Using Node.js from C:\Program Files\nodejs\node.exe`，PyInstaller `Build complete`。

## 观察

`npm ci` 对锁定依赖报告 3 个 audit finding（1 moderate、1 high、1 critical）。
Task 8 未改变已批准的精确依赖锁；该提示不影响离线 bundle 构建和冻结验证。

## 交付约束

- 只删除既有安全脚本限定的仓库内 `build/` 与 `dist/`。
- 未删除用户其他数据。
- 按用户要求：提交但不 push，不修改 git config。
