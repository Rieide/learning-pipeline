<!--
把本文件复制到你的【学习 workspace】根目录、改名为 CLAUDE.md，让 Claude Code 一进入就自举到 pipeline。
本文件只是样例，不属于 pipeline 运行的一部分。
-->

# 学习 workspace

本目录是**学习 workspace**（存放阅读材料、QA 文件、归档、教科书、复习卡等个人内容）。

学习方法 pipeline（prompt 规范 + 脚本）在环境变量 `$LEARNING_PIPELINE` 指向的仓库，**不在本目录**。

**动手前先读 `$LEARNING_PIPELINE/README.md`**，按其中的工作流 A/B 推进；脚本统一用
`python $env:LEARNING_PIPELINE\scripts\qa_archive.py ...` 调用。

个人背景在 `$PERSONAL_BACKGROUND`（workspace 的 `background/` 目录，见 `$LEARNING_PIPELINE/background_db.md`）：`baseline.yaml` 基线 + `background.db`（`s_have` 台账 / `topics` 状态，由 `scripts/background.py` 读写）+ `WORK_LOG.md` 动态流水账。读前差集 `have-query`，学完 `have-add` 回填；周进度只进 `WORK_LOG.md`。

周复盘时直接说「按 `$LEARNING_PIPELINE/weekly_review.md` 做周复盘回填」，把本周工作叙事交给它自动分流更新。
