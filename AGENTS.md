# Agent 入口

开始任何工作前：

1. 读 `docs/STATUS.md`（背景、当前目标、进度）。
2. 读 `docs/superpowers/process.md`。
3. 按 `.cursor/rules/git-progress-handoff.mdc`：设计/计划/任务边界提交并推送到 `origin/main`。
4. 当前目标、开发列表和对应的规格/计划路径都在 `docs/STATUS.md`「当前目标」一节。
5. 每次发布（通过 `scripts\verify.ps1 -Release` 并安装或公开发布）：发布前运行 `python scripts\bump_version.py`（修订号加 1；`--minor` / `--major` / `--set X.Y.Z`），版本号只写在 `VERSION`；同时更新 STATUS（有更新日志后一并更新）。
