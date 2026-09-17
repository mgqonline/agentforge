---
name: version-control
description: Version Control
---

# Version Control
- 默认先显示当前分支：`git branch --show-current`
- 默认显示最近10条版本变更记录：`git reflog --date=iso -10`
- 用户指定前N条时，显示最近N条版本变更记录：`git reflog --date=iso -N`
- 版本变更记录必须保留 reflog 输出中的版本引用、HEAD 移动信息和时间信息
- 标记当前版本编号时，输出：
  - 当前分支：`git branch --show-current`
  - 当前短版本号：`git rev-parse --short HEAD`
  - 当前完整版本号：`git rev-parse HEAD`
- 用户指定版本回退时，先用 `git rev-parse --verify <版本号>` 校验版本是否存在
- 版本存在后，执行彻底回退：`git reset --hard <版本号>`
- 回退完成后，输出当前分支和最近10条版本变更记录，用于确认回退结果
- `git reset --hard` 会丢弃未提交变更，并让当前分支彻底回退到指定


# 版本输出模版
```
当前分支：xxx
版本引用：xxxxx
最近版本变更记录
| 版本引用 | 提交时间 | 分支 |变更信息 |
| -------- | -------- | -------- | -------- |
| xxx←当前 | yyyy-MM-dd HH:mm:ss | xxx | xxx |
| xxx | yyyy-MM-dd HH:mm:ss | xxx | xxx |
用户可输入版本号回退，注意：未提交的修改会丢失
```
