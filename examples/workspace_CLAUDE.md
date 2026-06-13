<!--
把本文件复制到你的【学习 workspace】根目录、改名为 CLAUDE.md，让 Claude Code 一进入就自举到 pipeline。
本文件只是样例，不属于 pipeline 运行的一部分。
-->

# 学习 workspace

本目录是**学习 workspace**（存放阅读材料、QA 文件、归档、教科书、复习卡等个人内容）。

学习方法 pipeline（prompt 规范 + 脚本）在环境变量 `$LEARNING_PIPELINE` 指向的仓库，**不在本目录**。

**动手前先读 `$LEARNING_PIPELINE/README.md`**，按其中的工作流 A/B 推进；脚本统一用
`python $env:LEARNING_PIPELINE\scripts\qa_archive.py ...` 调用。

个人背景稳定档案（含 `S_have` 知识资产台账）在 `$PERSONAL_BACKGROUND`：读前差集读它、学完台账回填写它。
与它同目录的 `WORK_LOG.md` 放周进度/切入点等动态流水账，工作进度回填写这里，不污染稳定档案。

周复盘时直接说「按 `$LEARNING_PIPELINE/weekly_review.md` 做周复盘回填」，把本周工作叙事交给它自动分流更新这两个文档。
