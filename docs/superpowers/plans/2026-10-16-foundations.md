# 计划：基础整理（A1–A5）

日期：2026-10-16
状态：已批准
规格：`docs/superpowers/specs/2026-10-16-foundations-design.md`

## 任务 1（A1）版本号统一
RED：版本来源唯一、`bump_version.py` 行为、打包版本资源由 `VERSION` 生成。GREEN：`scripts/version_tools.py` + `bump_version.py`，`pyproject` 动态版本，`reader.spec` 生成版本资源，删除 `version_info.txt`，流程文档写入规则。

## 任务 2（A2）依赖固定
RED：依赖必须是 `==` 且与环境一致。GREEN：改 `pyproject.toml`。

## 任务 3（A3）更新日志与许可证
RED：`CHANGELOG.md` 顶部版本 = `VERSION`，`LICENSE`、第三方说明存在，脚本插入新版本标题。GREEN：新增文件，扩展脚本。

## 任务 4（A4）删除无用代码与文档整理
RED：被删模块不存在且无引用。GREEN：删除；精简 STATUS；重写 README 加截图；仓库简介和标签。

## 任务 5（A5）网址可 Ctrl+点击
RED：网址识别与 Ctrl+单击打开。GREEN：文本/代码视图实现。

## 收尾
发布验证 → 运行 `bump_version.py` → 安装 → STATUS 记录 → 推送。
