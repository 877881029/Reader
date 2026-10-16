# 基础整理（A1–A5）

日期：2026-10-16
状态：已实施（2026-10-16，0.1.1）
进度：`docs/STATUS.md`

## 1. 目标

把版本号、依赖、许可、文档和无用代码理顺，并让文本/代码里的网址可以点开，为后续数据安全、设置页、提速和公开发布打底。

## 2. 决定

### A1 版本号统一

- 版本号只写在仓库根目录 `VERSION`（一行 `主.次.修订`）。
- `pyproject.toml` 改为从 `VERSION` 动态读取，不再写死。
- Windows 文件版本信息（原 `version_info.txt`）在打包时由 `reader.spec` 按 `VERSION` 生成到 `build/`，仓库里不再保存这个文件。
- `scripts/bump_version.py`：默认修订号加 1，可选 `--minor` / `--major` / `--set X.Y.Z`；同时改 README 里「当前版本」那一行（`release/README.md` 是 0.1.0 源码快照的历史说明，留给 D1 发布时重写）。
- 规则：每次发布（通过发布验证并安装或公开发布）前运行一次 `bump_version.py`，并同步更新 STATUS（A3 之后还有更新日志）。写进 `AGENTS.md`、`docs/superpowers/process.md` 和 `.cursor/rules/git-progress-handoff.mdc`。
- 程序内的版本显示（欢迎页）继续读 `VERSION`。

### A2 依赖固定

- `pyproject.toml` 运行依赖与开发依赖全部写成 `==` 当前测试通过的版本。
- 测试断言每个依赖都是精确版本。

### A3 更新日志与许可证

- 新增 `CHANGELOG.md`（按版本倒序，中文）。
- 新增 `LICENSE`：本项目代码 MIT（与 Tasker 一致）；第三方组件（Qt/PySide6 为 LGPL-3.0 等）在 `THIRD_PARTY_NOTICES.md` 列出，与已有前端资源许可说明呼应。
- `bump_version.py` 在 `CHANGELOG.md` 顶部插入新版本标题。

### A4 文档与无用代码

- 删除：`src/reader/shell/settings_claim.py` 及其测试、`src/reader/ext/`（翻译/转换/分屏三个空壳）、根目录 4 个 `task-*-report.md`。
- STATUS 精简为「当前状态 + 每次更新必做 + 历史要点」，详细历史留在 git 与规格/计划中。
- README 按实际功能重写，加截图；GitHub 仓库补简介和标签。

### A5 网址可点击

- 文本/代码视图（`CodeTextView`、Markdown 编辑视图）里 `http://` / `https://` 网址：按住 Ctrl 时悬停显示手形并带下划线，Ctrl+单击用系统默认浏览器打开。
- 只识别 http/https，不执行其他协议。

## 3. 测试

- A1：版本号只有一个来源；脚本加 1、各位进位、`--set` 校验格式；README/发布说明同步；打包生成的版本资源与 `VERSION` 一致。
- A2：依赖全部为精确版本，且与当前环境已安装版本一致。
- A3：更新日志顶部版本与 `VERSION` 一致；许可文件存在。
- A4：被删模块不再存在且无引用；README 提到的功能入口都存在。
- A5：网址识别（含中文标点结尾、括号）；Ctrl+单击调用打开；不带 Ctrl 不打开；非 http(s) 不打开。
