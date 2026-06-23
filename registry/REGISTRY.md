# 工具速查表 REGISTRY

> **本文件由 `scripts/gen_registry.py` 从各 prompt 的 frontmatter 生成，勿手改。**
> 改了 prompt 的 frontmatter 或新增 prompt 后重跑：`python $env:LEARNING_PIPELINE\scripts\gen_registry.py`
>
> **自举用法**：进入 workspace 后**先读本表**，按「何时用」选定要跑的 prompt，**再读那一份的全文**——不要全量读所有 prompt。设计要点 / 变更历史见 `dev_log.md`。

## Prompt（按工作流顺序）

| 文件 | stage | 何时用 | 读 → 写 |
|---|---|---|---|
| `topic_map.md` | A/宏观 | 把一个领域/大目标拆成有依赖的子主题地图 | 领域目标 + baseline.yaml + s_have → topics 表(topic-upsert) + Mermaid DAG |
| `source_selection.md` | B/collect | 有 theme、材料待获取，要定确定且范围可控的资料清单 | topics 节点(topic-show) + s_have(have-query) → {topic}_sources.md + topics.source |
| `prereq_and_objectives.md` | B/prereq | 材料已确定，读正文前出前置差集 + 目标问题 | 选定材料 + baseline.yaml + s_have(have-query) → {source}_prereq.md |
| `prereq_to_textbook.md` | B/prereq·预习教材(可选) | 要把前置差集扩写成可独立学一遍的预习小册 | {source}_prereq.md + to_tex.md → {topic}_预习_Textbook.tex |
| `source_to_textbook.md` | B/draft_textbook(可选) | 源密集/分散，先 consolidate 成主教材 v1 阅读底本 | {topic}_sources + 真实源 + to_tex.md → {topic}_Textbook.tex(v1) |
| `qa_note.md` | B/reading | 边读材料边问答，每个 QA 落成单文件 | 阅读材料(主教材 v1 或收料) → {source}_qa/QA_*.md（经 qa_archive.py new/finalize） |
| `qa_to_archive.md` | B/archive | QA 攒够，归档成原文素材文档 | {source}_qa/ 导航字段 → {topic}_arrangement.yaml → {topic}_原文素材归档.md（assemble） |
| `note_to_textbook.md` | B/textbook | 把 QA 内化成/融合进教科书（模式A 从零 / 模式B 融 v2） | 素材归档 或 教材 v1 + to_tex.md → {topic}_Textbook.tex(v2) |
| `to_review_cards.md` | B/review | 主题收尾，把已学材料转成间隔复习卡 | {source}_qa + 教材 warnbox/keybox + 目标问题 → {topic}_review.md |
| `background_update.md` | B/done(主题驱动) | 一个主题收尾，把新增能力写回台账 | 教材 / 复习卡 / 目标问题 → s_have(have-add) + topic-status done |
| `weekly_review.md` | 时间驱动 | 按周/里程碑，把一段时间的工作叙事沉淀 | 工作叙事 → WORK_LOG.md + s_have(have-add) |
| `topic_hub.md` | 视图/hub | 看/生成某主题的 obsidian 枢纽视图 | topics + s_have 表 → {topic}_hub.md（topic-render 生成视图） |
| `background_db.md` | 契约/background | 凡读写 S_have/topic —— 背景 DB 的 schema/CLI 契约 | — → —（契约层，被多个 prompt 引用） |
| `tool_prompts/to_tex.md` | 工具/渲染 | 已组织好的中文内容渲染成可编译教科书 .tex | 已组织好的内容 → .tex（预导言/TikZ/编译自检） |

## 脚本（机械层，被上面 prompt 调用）

| 脚本 | 一句话 |
|---|---|
| `scripts/background.py` | background.py — 个人背景的结构化机械层（SQLite 单库多表）。 |
| `scripts/qa_archive.py` | qa_archive.py — 机械搬运 / 校验层：把 LLM 的"编排决策"执行成字节级保真的归档。 |

