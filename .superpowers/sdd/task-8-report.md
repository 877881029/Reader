# UX Task 8 报告：Rapid Multi-Launch IPC and Multi-Arg Regression

## 状态

完成。基线 `689ad76b139f576fa7771884acdd50ace187989b`。

## TDD 记录

- RED：
  `python -m pytest tests/test_ipc.py::test_send_paths_drains_bytes_queued_by_flush -v`
  - 结果：1 failed。
  - 预期失败原因：`reader.ipc` 尚无 `POST_SEND_EVENT_PUMPS`，发送端也尚未在
    `flush()` 后保守排空。
- GREEN：运行新增 IPC、进程竞选和窗口多参数回归共 5 项，结果 `5 passed`。
- IPC 完整测试：`python -m pytest tests/test_ipc.py -v`，结果 `15 passed`。
- 并发竞选稳定性：进程级测试连续独立运行 3 次，每次均 `1 passed`。
- 最终全量：`python -m pytest -q`，结果 `155 passed`。
- IDE lint：修改文件无诊断；`git diff --check` 通过。

## 最小生产修复

- `src/reader/ipc.py`
  - 增加 `POST_SEND_EVENT_PUMPS = 3`。
  - 完整帧写入后先 `flush()`，再最多执行三轮 Qt event pump /
    `waitForBytesWritten()`，确认队列排空后才断开。
  - 保留原有长度前缀 JSON frame、UTF-8 编码、分块写入和连接重试协议。
- `ReaderApp._on_ipc_paths()` 已经一次调用 `window.open_paths(paths)` 转交完整批次，
  因此无需修改生产窗口或 `__main__`。

## 回归覆盖

- 8 次背靠背发送逐批、按顺序、无丢失、无重复送达；每批包含两个 argv 路径。
- 6 个 spawn 子进程通过同一个同步事件同时模拟 `__main__` 的 IPC 启动阶段：
  - 恰好一个进程持锁并成为 primary。
  - 其余进程均成功重试并转发。
  - 每个 launch 的多参数批次保持原子和参数内顺序，全集无丢失、无重复。
- 约 240 KiB 的 Unicode/emoji frame 使用 257-byte 人工分块完整送达。
- 监听尚未可连接时的退避重试以 fake socket 和替换 `sleep` 的确定性测试验证，
  不依赖真实等待。
- 非所有者不能监听、不能移除 endpoint；关闭非所有者不影响 primary 的既有回归继续通过。
- `READER_IPC_NAMESPACE` 每次随机生成，进程测试不与用户正在运行的 Reader 或其他测试冲突。
- 窗口回调收到两个 Unicode 路径时一次打开为两个 tab。

## 确定性与桌面隔离

- 进程 harness 只创建 `QCoreApplication`，不创建 `QApplication`、Reader 窗口或
  QtWebEngine 进程，不污染桌面。
- 同时起跑使用跨进程 `Event`；先监听重试测试替换 `time.sleep` 并断言退避值。
- timeout 仅作为死锁/子进程异常的安全上限，不参与测试排序或成功条件。
- `finally` 会终止异常残留子进程并关闭 multiprocessing queue。

## 变更文件

- `src/reader/ipc.py`
- `tests/test_ipc.py`
- `tests/test_window.py`
- `.superpowers/sdd/task-8-report.md`

## Important 审查修复（2026-08-24）

### 旧报告纠正

- 上文“确认队列排空后才断开”的表述对首版提交并不准确：首版循环达到三轮上限后，
  即使 `bytesToWrite() > 0` 仍会断开并返回 `True`。
- 上文约 240 KiB Unicode frame 的首版测试只在同一进程 Qt event loop 内发送，
  不能证明 secondary process 的大帧传输。
- 上文 cleanup 仅有 `terminate + join_thread`；它没有处理 terminate 后仍存活的进程，
  且 `Queue.join_thread()` 没有时间上限。
- 以下修复与验证结果取代这些旧结论。

### 严格 RED

命令：

`python -m pytest tests/test_ipc.py::test_send_paths_returns_false_when_flush_queue_stays_pending tests/test_ipc.py::test_send_paths_succeeds_when_failed_wait_pumps_queue_empty tests/test_ipc.py::test_send_paths_drains_normal_multi_round_flush_queue tests/test_ipc.py::test_send_paths_bounds_repeated_zero_byte_writes -v`

结果：`3 failed, 1 passed`。

- pending 一直非零：错误返回 `True`。
- `waitForBytesWritten(False)` 后 event pump 清空 pending：错误返回 `False`。
- 连续 `write()==0`：调用 101 次才因 fake 返回 `-1` 退出，证明可无界空转。
- 正常多轮归零用例已通过，作为既有正常路径的约束。

### 修复语义

- flush drain 每轮先检查 pending；仍有数据时执行 wait，随后 pump events，再次检查
  pending。wait 返回值不覆盖真实队列状态。
- 任意一轮观察到 `bytesToWrite() == 0` 才返回 `True`。
- 达到 `POST_SEND_EVENT_PUMPS` 上限后 pending 仍非零，断开并返回 `False`。
- 连续零字节 write 最多容忍 `MAX_CONSECUTIVE_ZERO_WRITES` 次；持续无进展或 wait
  失败时断开并返回 `False`，正向 write 会重置计数。
- 未加入可选 `MAX_FRAME_BYTES`：现有长度前缀协议保持兼容，240 KiB 回归不受影响。

### 进程级大帧与确定性

- 6 个 spawn launch 的每个 payload 都包含约 240 KiB Unicode/emoji 参数；
  因而无论哪个成为 primary，其余 5 个 secondary 都必须跨进程发送大帧。
- queue 结果严格断言恰好 `6 role / 5 sent / 1 seen`，拒绝未知消息类型，并验证
  launch id 全集。
- 批次内参数顺序与批次原子性完整保留；并发批次之间不假定全局顺序。
- autouse fixture 在每个测试前清除 `READER_IPC_NAMESPACE`。
- cleanup 顺序为 `join → terminate + join → kill + join`；queue 使用
  `cancel_join_thread + close`，不再无界 `join_thread`；独立 namespace lock file
  在 finally 中删除。

### GREEN 与最终验证

- 修复语义定向测试：`5 passed`。
- 完整 IPC：`18 passed`。
- 大帧进程竞选连续独立运行 3 次：每次均 `1 passed`。
- 最终全量：`158 passed in 43.20s`。
- IDE lint：修改文件无诊断。
