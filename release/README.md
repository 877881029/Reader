# Reader 0.1.0（源码快照）

这是 **0.1.0** 说明目录，不是二进制发布仓。

**git 里没有** zip、`Reader.exe`、`bin/` 或 Qt `_internal`。clone 之后用脚本从源码跑起来。

## 运行

Windows + Python 3.12+ + Node 18+：

```text
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup.ps1
```

这会装依赖并打出 `dist\Reader\Reader.exe`（不要提交）。只要源码运行可加 `-SkipBuild`。详见仓库根目录 `README.md`。

## 本机自己打 exe

`setup.ps1` 默认就会调用 `scripts\build_windows.ps1`。也可以单独再跑该脚本。生成的 exe/zip **不要提交**；`.gitignore` 已忽略 `dist/`、`release/*.zip`、`release/*.exe`。
