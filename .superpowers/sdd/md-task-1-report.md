# Markdown Visual Preview Task 1 Report

## 实现内容
- 按 TDD 创建 `tests/test_md_web_assets.py`，覆盖离线 scaffold、精确依赖、production 依赖树 notice 覆盖、bundle manifest 字节校验。
- 创建 `web/md-viewer` 离线工程：`package.json`、`package-lock.json`、`index.html`、`tsconfig.json`、`vite.config.ts`、`vitest.config.ts`、`src/main.ts`。
- 运行时依赖仅 `markdown-it`、`mermaid`，全部通过 `npm install --save-exact` 安装；开发依赖同样 `--save-exact`。
- 实现 `web/md-viewer/scripts/generate-notices.mjs`：调用 `license-checker-rseidelsohn` 扫描 production tree，按 `name@version` 排序，逐包读取 `licenseFile`，缺失/空文本立即失败；输出确定性 `THIRD_PARTY_NOTICES.txt`，并复制同字节到 `assets/md-viewer/THIRD_PARTY_NOTICES.txt`。
- 生成 `assets/md-viewer/manifest.sha256`（按相对路径排序、SHA256 双空格格式），并在 `.gitignore` 新增 `web/md-viewer/node_modules/`。
- 更新 `docs/STATUS.md` 与计划 `docs/superpowers/plans/2026-08-28-markdown-visual-preview.md` 的 Task 1 全部 checkbox。

## RED/GREEN 命令与关键输出
### RED
```powershell
.venv\Scripts\python.exe -m pytest tests\test_md_web_assets.py -v
```
- 结果：`3 failed`
- 关键失败点：
  - `web/md-viewer/package.json` 不存在（`FileNotFoundError`）
  - `cwd=web/md-viewer` 无效（目录不存在）
  - `assets/md-viewer/index.html` 不存在

### GREEN 准备
```powershell
npm init -y
npm install --save-exact markdown-it mermaid
npm install --save-dev --save-exact @types/markdown-it @types/node jsdom typescript vite vitest license-checker-rseidelsohn
npm ci
npm test
npm run typecheck
npm run build
```
- 关键输出：
  - `npm ci`: `added 339 packages ... found 0 vulnerabilities`
  - `npm test`: `Test Files 1 passed (1), Tests 1 passed (1)`
  - `npm run build`: 输出到 `../../assets/md-viewer`，随后执行 `node scripts/generate-notices.mjs`

### GREEN 验证
```powershell
.venv\Scripts\python.exe -m pytest tests\test_md_web_assets.py -v
git diff --check
```
- 结果：`3 passed in 4.61s`
- `git diff --check`：无输出（通过）

## 变更文件
- `.gitignore`
- `docs/STATUS.md`
- `docs/superpowers/plans/2026-08-28-markdown-visual-preview.md`
- `tests/test_md_web_assets.py`
- `web/md-viewer/package.json`
- `web/md-viewer/package-lock.json`
- `web/md-viewer/index.html`
- `web/md-viewer/tsconfig.json`
- `web/md-viewer/vite.config.ts`
- `web/md-viewer/vitest.config.ts`
- `web/md-viewer/src/main.ts`
- `web/md-viewer/src/main.test.ts`
- `web/md-viewer/scripts/generate-notices.mjs`
- `web/md-viewer/THIRD_PARTY_NOTICES.txt`
- `assets/md-viewer/index.html`
- `assets/md-viewer/assets/index-*.js`
- `assets/md-viewer/THIRD_PARTY_NOTICES.txt`
- `assets/md-viewer/manifest.sha256`

## 测试清单
- Python:
  - `tests/test_md_web_assets.py`（RED 失败记录 + GREEN 全通过）
- Node/Web:
  - `npm test`（vitest）
  - `npm run typecheck`
  - `npm run build`
- Diff hygiene:
  - `git diff --check`

## 自审结果
- 严格 TDD：先测试并记录 RED，再实现至 GREEN。
- npm 依赖来源合规：全部通过 npm 安装，且 `--save-exact`，未手填版本。
- 许可生成器覆盖 production dependency tree，不是仅顶层依赖，并对缺失 license 文本 fail-fast。
- 构建输出与 manifest 均可复算，路径与排序规则确定。
- 未改动 PPTX 相关代码、资产与行为。

## Concerns
- `license-checker-rseidelsohn@5.0.1` 的 `package.json` 声明 `engines.node >=24`；当前环境可运行，但若未来在更低 Node 版本执行 `npm run notices` 可能触发兼容性风险，需要在后续任务确认项目 Node 基线或替换等价许可证扫描方案。

---

## Reviewer 修复追加（Task 1 needs-fixes）

### 修复内容
- 移除 `license-checker-rseidelsohn`，改为内建 deterministic notice walker：通过 `npm ls --omit=dev --all --json` 获取 production tree，再以 `package-lock.json` 生产包路径定位 `node_modules`，逐包读取 license 文本；缺失文本立即 `throw`（fail-fast）。
- 新增 `web/md-viewer/scripts/generate-manifest.mjs`，构建顺序固定为：`vite build`（`emptyOutDir`）→ `npm run notices`（复制 notices 到 bundle）→ `npm run manifest`。
- 修复 Windows notices 调用：由 `execFileSync("npm.cmd", ...)` 改为 `cmd /d /s /c npm.cmd ...`，避免 `spawnSync npm.cmd EINVAL`。
- devDependency 改为 Node 18 兼容 exact pin（全部通过 npm 安装并刷新 lock）：`@types/markdown-it@14.2.0`、`@types/node@22.13.14`、`jsdom@24.1.3`、`typescript@5.9.2`、`vite@5.4.19`、`vitest@2.1.9`。
- `package-lock.json` 根元数据已同步为 `reader-md-viewer@0.1.0`。
- 扩展 `tests/test_md_web_assets.py` 到 6 项：新增 devDependency 基线/engines 校验、manifest 脚本接线校验、opt-in clean build 恢复测试。

### 本轮命令与关键输出
```powershell
npm ci
npm test
npm run typecheck
Remove-Item -Recurse -Force assets/md-viewer
npm run build
.venv\Scripts\python.exe -m pytest tests\test_md_web_assets.py -v
git diff --check
```
- `npm ci`：`added 229 packages ...`
- `npm test`：`Test Files 1 passed (1), Tests 1 passed (1)`
- `npm run typecheck`：通过
- clean build：`npm run build` 后 `assets/md-viewer/{index.html,assets/*,THIRD_PARTY_NOTICES.txt,manifest.sha256}` 全量恢复
- `pytest`：`6 passed in 7.40s`
- `git diff --check`：无空白错误（仅 CRLF 警告）

### 新提交
- `8be7064` `fix: harden md-viewer node18 deterministic build chain`
- `22515cd` `docs: append md task1 reviewer-fix report`

### Concerns（更新）
- 旧 concern（`license-checker-rseidelsohn` Node24 下限）已关闭：该依赖已移除。
- `git push origin main` 当前仍失败：`403 Permission denied to runqyang_amdeng`。本次未能完成“已用 repo owner credential 成功推送”的验收条件，需先切换凭证后重试。

### Controller 关闭说明
- `2026-08-28`：controller 已使用 repository owner 凭证将 HEAD `e403337` 推送到 `origin/main`，上述 push 权限 concern 已关闭。
