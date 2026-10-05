"""DotNetRandom：与 PowerShell 5.1 / .NET Framework 实测序列逐位一致。"""

from koutu.core.dotnet_random import DotNetRandom


def test_next_1000_sequence():
    r = DotNetRandom(2024)
    got = [r.next(1000) for _ in range(12)]
    assert got == [115, 696, 519, 566, 13, 328, 772, 851, 380, 625, 434, 633]


def test_next_61_sequence():
    r = DotNetRandom(2024)
    got = [r.next(61) for _ in range(12)]
    assert got == [7, 42, 31, 34, 0, 20, 47, 51, 23, 38, 26, 38]


def test_next_7_sequence():
    r = DotNetRandom(2024)
    got = [r.next(7) for _ in range(12)]
    assert got == [0, 4, 3, 3, 0, 2, 5, 5, 2, 4, 3, 4]


def test_next_raw_sequence():
    r = DotNetRandom(2024)
    got = [r._internal_sample() for _ in range(8)]
    assert got == [
        247130676,
        1495952918,
        1116080357,
        1216877399,
        28283303,
        704472390,
        1659538823,
        1828387271,
    ]
