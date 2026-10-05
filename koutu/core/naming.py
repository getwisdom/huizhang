"""Windows 自然序（`StrCmpLogicalW`）：`1,2,…,10,11` 不乱序。"""

from __future__ import annotations

import ctypes
from functools import cmp_to_key

_shlwapi = None


def _get_shlwapi():
    global _shlwapi
    if _shlwapi is None:
        _shlwapi = ctypes.WinDLL("shlwapi")
        _shlwapi.StrCmpLogicalW.restype = ctypes.c_int
        _shlwapi.StrCmpLogicalW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
    return _shlwapi


def natural_cmp(a, b) -> int:
    """与旧实现 `StrCmpLogicalW(a, b)` 一致的比较函数。"""
    return int(_get_shlwapi().StrCmpLogicalW(str(a), str(b)))


def natural_key_func():
    """返回可直接用作 `sorted(key=...)` 的键函数工厂。"""

    def key(s):
        return cmp_to_key(natural_cmp)(str(s))

    return key
