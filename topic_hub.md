---
name: topic-hub-template
description: 单主题的 obsidian 汇总枢纽（MOC）模板与约定。每个深读主题一份 hub 文件，用 frontmatter 当状态机（status/tags/deps/roi），正文用链接把"核心问题、前置知识、原始材料、最终产物、复习卡"串成单一入口。配套一段 Dataview，可在总 MOC 自动出全主题进度看板。topic_map.md 生成占位条目、各深读步骤推进 status。
---

# obsidian 主题枢纽（MOC）模板

> **定位**：单主题的唯一入口。把深读流程各阶段产物（前置/QA/归档/教科书/复习卡）用链接收拢到一处，并用 frontmatter 暴露状态，供 Dataview 汇总。
> **谁来填**：`topic_map.md` 生成骨架（`status: planned`）；各深读步骤推进 `status` 并补对应链接区。

---

## 1. 单主题 hub 模板

把下面整段复制为 `{topic}_hub.md`（或就用主题同名文件），随流程推进逐区填充：

```markdown
---
topic: SIMPL
tags: [prediction, motion-forecasting, evaluator]
status: planned        # planned→collect→prereq→reading→archive→textbook→review→done
deps: [VectorNet, prediction-proto]
roi: high
objective: 讲清 SIMPL 对称/instance-centric 表示，并与 MTR/VectorNet 对照
source_hint: [SIMPL 论文 arXiv:2402.02519, modules/prediction 下 simpl_* 源码]
updated: 2026-06-05
---

# {topic}

## 核心问题（读前设定）
- 来自 prereq_and_objectives.md 的 3–5 个阅读目标问题
- [ ] Q1 …
- [ ] Q2 …

## 资料清单（collect）
→ [[{topic}_sources]]（source_selection.md 把 theme 收敛成确定的、范围可控的材料）

## 前置知识（预习组，与主材料组分离）
→ [[{source}_prereq]]（差集脚手架）
→ [[{topic}_预习_Textbook.pdf]]（预习教材，prereq_to_textbook 可选旁支）
- 预习随文 QA：`{topic}_预习_qa/` ｜ 归档：[[{topic}_预习_原文素材归档]]

## 原始材料
- 随文问答：`{source}_qa/`（单文件 QA，front-matter 带 id/content_hash；脚本 finalize 锁定正文）
- 编排表：[[{topic}_arrangement]]（LLM 出的"去哪/排第几/去重"决策）
- 素材归档：[[{topic}_原文素材归档]]（由 `qa_archive.py assemble` 按编排表字节级拼接生成）

## 最终产物
→ [[{topic}_Textbook.pdf]]

## 复习卡
→ [[{topic}_review]]
- 复习时点：+1d ☐  +3d ☐  +7d ☐

## 备注 / 卡点
-
```

### frontmatter 字段约定
| 字段 | 含义 |
|---|---|
| `topic` | 主题名，与文件名/各产物前缀一致 |
| `tags` | 检索标签（领域/方法/角色） |
| `status` | 状态机，见下方流转 |
| `deps` | 前置主题（来自 topic_map 的 DAG） |
| `roi` | high / mid / low |
| `objective` | 一句话目标 |
| `source_hint` | 候选材料方向种子（topic_map 填，`source_selection.md`/collect 步消费） |
| `updated` | 最近推进日期（绝对日期） |

### status 流转（与各 prompt 对应）
```
planned  →  collect          →  prereq              →  reading      →  archive        →  textbook            →  review            →  done
(topic_map) (source_selection)   (prereq_and_objectives) (qa_note 随文)   (qa_to_archive)   (note_to_textbook)     (to_review_cards)   (background_update 写台账后置 done)
```

> **可选 · 教材优先路（v1→QA→v2）**：`reading` 之前可先跑 `source_to_textbook.md`，从收料生成主教材 **v1**（阅读底本）；之后 `qa_note` 读 v1 边读边 QA，`note_to_textbook` 模式 B 把 QA 融合回 v1 → **v2**（`status: textbook` 即指 v2 成稿）。源单一可直读时跳过此路，走 QA 优先（`note_to_textbook` 模式 A 从 QA 从零建）。主教材 v1、v2 是**同一文件 `{topic}_Textbook` 的演进**。

> **置 done 的前置条件**：跑完 `background_update.md`，把本轮新增 `S_have`（及"仍存疑"项）追加进背景文件（`$PERSONAL_BACKGROUND`）的知识资产台账。没回填背景，不算闭环，不置 done。

---

## 2. 总 MOC 的进度看板（Dataview）

在一个总入口文件（如 `学习总览_MOC.md`）放下面代码块，自动列出全部主题及状态。需安装 Dataview 插件：

````markdown
## 主题进度

```dataview
TABLE status, roi, deps, updated
FROM "week2_learning"
WHERE topic
SORT status ASC, roi DESC
```

## 待推进（卡在早期阶段的）

```dataview
LIST
FROM "week2_learning"
WHERE topic AND status != "done"
SORT updated ASC
```
````

> 路径 `"week2_learning"` 按实际主题存放目录调整；若 hub 散在多目录，去掉 FROM 用全库，靠 `WHERE topic` 过滤。

---

## 3. 约定

- **一主题一 hub**，所有该主题产物都从 hub 出链；不在别处维护重复链接列表。
- **status 单调推进**，每次推进顺手更新 `updated`。
- **命名前缀统一**：`{source}` 用材料文件名主体，`{topic}` 用主题名；同主题的 prereq/qa_note/归档/textbook/review 共用前缀，便于配对与 Dataview。
