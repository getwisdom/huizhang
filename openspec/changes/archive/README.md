# 归档（archive）

已经实现、验证并合并进 `openspec/specs/` 的变更提案放在这里，命名 `<YYYY-MM-DD>-<change-id>/`，
作为"当时为什么这么改"的决策历史保留。

## 合并规则

1. 把提案 `specs/<capability>/spec.md` 里的 `ADDED / MODIFIED / REMOVED Requirements`
   逐条落到 `openspec/specs/<capability>/spec.md`（新增追加、修改就地替换、删除移除该节）；
2. 检查实现代码与合并后的规格一致（含 `抠图工具.cs` / `cut_badge.ps1` 之类的双实现）；
3. 把整个提案目录移入本目录，不要留在 `changes/` 根下。

## 当前状态

无已归档提案。本仓库于 2026-10-05 首次建立 OpenSpec 基线，
基线内容是把**已经存在的代码**反向整理成的规格，见 `openspec/specs/`。
