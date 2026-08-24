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
# Reader v1 Task 8 报告：预览磁盘缓存与 200MiB LRU

## 变更文件
- `src/reader/preview/cache.py`
- `tests/test_cache.py`

## 行为实现说明
- key 由 `resolved path + mtime_ns + size + strategy` 组成后做 SHA-256。
- 默认缓存目录为 `LOCALAPPDATA/Reader/preview-cache`（无环境变量时回退到 `~/AppData/Local/Reader/preview-cache`）。
- 支持 HTML 与 PDF 的 cache roundtrip：
  - HTML 存 `preview.html`。
  - PDF 拷贝为缓存槽位下 `preview.pdf` 并返回缓存内路径。
- 源文件变化会 miss：因为 key 包含 `mtime_ns` 与 `size`。
- 真正 LRU：
  - 每次 `put/get` 成功都刷新 `last_access_ns.txt`。
  - `enforce_limit` 按访问时间从旧到新淘汰，默认上限 `200 * 1024 * 1024`。
- 删除目录稳健：
  - `put` 前会确保根目录存在并可重建。
  - 淘汰使用 `shutil.rmtree(..., ignore_errors=True)` 防止目录删除异常中断。
- 不影响源文件：
  - 仅 `stat/read` 源文件，不写回源路径。
- 损坏缓存处理：
  - `meta.json` 损坏/字段异常/文件缺失时均按 miss 处理，不抛出到调用层。

## TDD 证据
### RED（先失败）
命令：
`python -m pytest tests/test_cache.py -v`

结果要点：
- 8 个测试全部 FAIL。
- 失败原因为 `ModuleNotFoundError: No module named 'reader.preview.cache'`。

### GREEN（最小实现后通过）
命令：
`python -m pytest tests/test_cache.py -v`

结果要点：
- `tests/test_cache.py` 8/8 PASS。

### 全量回归
命令：
`python -m pytest -v`

结果要点：
- 全量 46/46 PASS。

## 测试覆盖点
- HTML roundtrip。
- PDF roundtrip（缓存副本存在且字节一致）。
- 源文件修改后 miss。
- strategy 参与 key（不同策略互不命中）。
- 命中会刷新 LRU 顺序（淘汰最久未使用项）。
- 损坏缓存按 miss 处理。
- 缓存目录被删除后可重建继续工作。
- `put` 不修改源文件内容与大小。

## 顾虑与后续建议
- 当前以目录+文件实现元数据与 LRU，符合“不扩展复杂数据库”要求；并发进程同时访问时未做文件锁，极端并发下可能出现短暂竞争（当前任务范围外）。
- PDF 结果读取时返回缓存内 `preview.pdf` 路径；调用方若需要长期保留，应自行复制到目标位置。

## Task 8 审查 Important 修复（追加）
### 本次变更
- `src/reader/preview/cache.py`
  - `meta` 统一记录 `artifact`、`artifact_size`、`artifact_sha256`。
  - `get` 时验证 artifact 存在、size/hash 匹配；PDF 额外要求非空，不满足即 miss。
  - LRU 淘汰改为“实际删除驱动”：删除失败继续尝试其他槽位；仅目录确实不存在才视为删除；每轮后按剩余文件重新统计总大小。
- `tests/test_cache.py`
  - 新增空 PDF、篡改 PDF、缺失 PDF 文件均 miss 测试。
  - 新增“最旧槽删除失败仍继续淘汰且计量正确”测试。

### 本次 TDD 证据
#### RED（先失败）
命令：
`python -m pytest tests/test_cache.py -v`

结果要点：
- 12 项中 3 项 FAIL：
  - `test_pdf_miss_when_cached_pdf_is_empty`
  - `test_pdf_miss_when_cached_pdf_is_tampered`
  - `test_enforce_limit_keeps_accounting_when_oldest_delete_fails`

#### GREEN（实现后通过）
命令：
`python -m pytest tests/test_cache.py -v`

结果要点：
- 12/12 PASS。

#### 全量回归
命令：
`python -m pytest -v`

结果要点：
- 50/50 PASS。

### 新增顾虑
- LRU 在无法删除被锁定目录时会保留残留，符合“允许残留且不误算已删除”；但当残留文件本身已超过上限时，缓存总量可能暂时高于阈值，需等待文件解锁后的后续淘汰周期恢复。
