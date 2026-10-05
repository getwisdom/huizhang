"""自然序：1,2,…,10,11 不乱序（StrCmpLogicalW）。"""

from functools import cmp_to_key

from koutu.core.naming import natural_cmp


def test_numeric_order():
    names = ["10", "2", "1", "11", "9", "3"]
    got = sorted(names, key=cmp_to_key(natural_cmp))
    assert got == ["1", "2", "3", "9", "10", "11"]


def test_filename_order():
    names = ["10.png", "2.png", "1.png", "6.png", "测试_1.png"]
    got = sorted(names, key=cmp_to_key(natural_cmp))
    assert got == ["1.png", "2.png", "6.png", "10.png", "测试_1.png"]
