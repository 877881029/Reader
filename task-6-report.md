# Task 6 Report: Shell Registration Uses Reader.exe and Icons

## 状态

完成。按严格 TDD 执行 RED -> GREEN，并完成聚焦/全量回归。

## 变更文件

- `src/reader/shell/associate.py`
- `src/reader/__main__.py`
- `tests/test_associate.py`
- `tests/test_main_launch.py`（新增）

## 实现结果

- 新增 `reader.__main__._association_target()`：
  - frozen：`(sys.executable, ())`，即 `Reader.exe`
  - development：`(sys.executable, ("-m", "reader"))`
- `register_open_with()` 支持 `args`，并生成安全命令：
  - frozen：`"<exe>" "%1"`
  - development：`"<python.exe>" -m reader "%1"`
- 注册 `DefaultIcon` 到 `Software\Classes\Reader.Document\DefaultIcon`，值为 exe 路径。
- `create_desktop_shortcut()` 支持 `args` 与 `icon`：
  - `Targetpath=exe`
  - `Arguments` 按参数拼接
  - `WorkingDirectory=exe目录`
  - `IconLocation=icon or exe`
- 所有关联/快捷方式写入仍仅在 `main()` 中执行（非 import-time）；异常继续吞掉，保证首次运行幂等且不阻断 app。

## TDD 记录

- RED：
  - `python -m pytest tests/test_associate.py::test_register_open_with_sets_default_icon_to_exe tests/test_associate.py::test_create_desktop_shortcut_sets_icon_location tests/test_main_launch.py -v`
  - 结果：4 failed（符合预期）
- GREEN（聚焦）：
  - `python -m pytest tests/test_associate.py tests/test_main_launch.py -v`
  - 结果：9 passed
- 全量：
  - `python -m pytest -q`
  - 结果：130 passed

## 自检清单

- [x] frozen 使用 `sys.executable`（Reader.exe）
- [x] source dev 使用 `python -m reader`
- [x] registry command 安全引用路径及 `%1`
- [x] `DefaultIcon=exe,0` 语义（写入 exe 路径，Windows 默认索引 0）
- [x] desktop shortcut frozen/dev 启动均可构造
- [x] 不在 import 时写注册表
- [x] tests 使用 fake winreg/shortcut
- [x] 首次运行幂等，错误不阻断 app
- [x] 开发态测试可运行

---

## Blocker/Major 修复追加

### 修复项

- `DefaultIcon` 改为精确 `f"{exe},0"`。
- registry command 改为 `subprocess.list2cmdline([exe, *args]) + ' "%1"'`，并确保 `%1` 作为 literal suffix，始终双引号，不交给 `list2cmdline`。
- shortcut `Arguments` 改为 `subprocess.list2cmdline(list(args))`，无 `args` 时为空串。
- shortcut `IconLocation` 统一为 `exe,0`（若传入 `icon` 且无索引，也补 `,0`）。
- 保持签名兼容：
  - `register_open_with(exe, winreg_module=None, *, args=())`
  - `create_desktop_shortcut(exe, name="Reader", winshell_or_com=None, *, args=(), icon=None)`

### RED 测试补充

- 新增覆盖 `Program Files` 路径。
- 新增 `args` 特殊字符：空格、tab、引号、尾反斜杠。
- 期望值使用 `subprocess.list2cmdline` 作为 oracle。
- 明确断言 command 以 ` "%1"` 结尾。
- 明确断言 `DefaultIcon` 为 `,0`。
- 明确断言 dev `Arguments` 为 `-m reader`，`IconLocation` 为 `exe,0`。

### 验证结果

- RED：
  - `python -m pytest tests/test_associate.py -v`
  - 结果：7 failed（符合预期，修复前失败）
- GREEN（聚焦）：
  - `python -m pytest tests/test_associate.py tests/test_main_launch.py -v`
  - 结果：11 passed
- 全量：
  - `python -m pytest -q`
  - 结果：132 passed
