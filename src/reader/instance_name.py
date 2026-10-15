"""Qt-free single-instance naming, shared by the IPC server and the fast launcher."""

from __future__ import annotations

import os
import re

SERVER_NAME = "Reader.SingleInstance.v1"


def qualified_server_name(base: str) -> str:
    namespace = os.environ.get("READER_IPC_NAMESPACE", "").strip()
    if not namespace:
        return base
    safe_namespace = re.sub(r"[^A-Za-z0-9_.-]", "_", namespace)
    return f"{base}.{safe_namespace}"


def server_name() -> str:
    return qualified_server_name(SERVER_NAME)