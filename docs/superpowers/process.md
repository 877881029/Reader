# Reader 开发流程

目标：换会话、换模型后仍能从 git 恢复背景、目标和进度，而不是依赖聊天记录。

## 1. 单一事实来源

| 内容 | 路径 |
|---|---|
| 活状态（必读） | `docs/STATUS.md` |
| 已批准规格 | `docs/superpowers/specs/` |
| 实施计划 | `docs/superpowers/plans/` |
| 本流程 | `docs/superpowers/process.md` |
| Cursor 强制规则 | `.cursor/rules/git-progress-handoff.mdc` |

聊天记录不是权威。权威是已推送的 git。

## 2. 功能增量节奏

1. 设计：用户确认后写入 `specs/`，更新 `STATUS.md`，提交并推送。  
2. 计划：TDD 计划写入 `plans/`，更新 `STATUS.md`，提交并推送。  
3. 实现：每个可独立审查的任务完成后提交；**每个任务（或每个工作会话结束）推送 `origin/main`**。  
4. 收尾：测试通过、必要时重建 `Reader.exe`、按用户要求更新桌面快捷方式；`STATUS.md` 把该功能标为完成并写下一步。

## 3. 提交与推送

- 规格、计划、STATUS、规则变更与代码同等对待，必须进 git。  
- 提交说明写清「为什么」（目标），不要只列文件名。  
- 禁止把进度只留在本地：实现中途若暂停，至少推送 STATUS + 当前提交。  
- 推送失败（权限/账号）必须写进 STATUS 的阻塞项，不能假装已同步。

## 4. 新会话启动

先读 `docs/STATUS.md`，再读其中指向的规格/计划，再 `git status` / `git log`。不要在未读 STATUS 的情况下改产品方向。
