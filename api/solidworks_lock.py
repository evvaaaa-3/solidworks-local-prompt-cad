"""Process-local serialization for real SolidWorks operations."""

from __future__ import annotations

from threading import Lock


solidworks_operation_lock = Lock()
