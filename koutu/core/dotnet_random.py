"""逐位复刻 .NET Framework `System.Random`（Knuth 减法发生器）。

用途：抠图 RANSAC 使用 `new Random(2024)`；为让 Python 重写复现同一组
随机三元组（进而同一拟合结果），这里按参考实现复刻其内部序列。

测试锚点（本机 PowerShell 5.1 = .NET Framework 实测）：
    2024.Next()      → 247130676,1495952918,1116080357,1216877399,28283303,...
    2024.Next(1000)  → 115,696,519,566,13,328,772,851,380,625,434,633
    2024.Next(61)    → 7,42,31,34,0,20,47,51,23,38,26,38
    2024.Next(7)     → 0,4,3,3,0,2,5,5,2,4,3,4
"""

from __future__ import annotations

MBIG = 2147483647
_MSEED = 161803398


class DotNetRandom:
    def __init__(self, seed: int) -> None:
        if seed == -2147483648:
            subtraction = 2147483647
        else:
            subtraction = abs(int(seed))
        seed_array = [0] * 56
        mj = _MSEED - subtraction
        seed_array[55] = mj
        mk = 1
        for i in range(1, 55):
            ii = (21 * i) % 55
            seed_array[ii] = mk
            mk = mj - mk
            if mk < 0:
                mk += MBIG
            mj = seed_array[ii]
        for _k in range(1, 5):
            for i in range(1, 56):
                seed_array[i] -= seed_array[1 + (i + 30) % 55]
                if seed_array[i] < 0:
                    seed_array[i] += MBIG
        self._seed_array = seed_array
        self._inext = 0
        self._inextp = 21

    def _internal_sample(self) -> int:
        inext = self._inext + 1
        if inext >= 56:
            inext = 1
        inextp = self._inextp + 1
        if inextp >= 56:
            inextp = 1
        ret = self._seed_array[inext] - self._seed_array[inextp]
        if ret == MBIG:
            ret -= 1
        if ret < 0:
            ret += MBIG
        self._seed_array[inext] = ret
        self._inext = inext
        self._inextp = inextp
        return ret

    def sample(self) -> float:
        """与 .NET `Random.Sample()` 相同：InternalSample() * (1.0/MBIG)。"""
        return self._internal_sample() * (1.0 / MBIG)

    def next(self, max_value: int) -> int:
        """与 .NET `Random.Next(maxValue)` 相同：(int)(Sample() * maxValue)。"""
        return int(self.sample() * max_value)
