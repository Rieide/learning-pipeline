---
name: topic-hub-view
stage: 视图/hub
when: 看/生成某主题的 obsidian 枢纽视图
reads: topics + s_have 表
writes: {topic}_hub.md（topic-render 生成视图）
description: 单主题的 obsidian 汇总枢纽（MOC）——现在是「由 topics 表渲染生成的视图」，不再手维护。真相源是 background.db 的 topics 表（topic 主键 + status 状态机 + roi/objective/deps/source_hint/source），由 background.py topic-render 生成 {topic}_hub.md（frontmatter + 各产物链接 + 本 topic 贡献的 S_have），由 background.py board 生成全主题进度看板。topic_map.md 用 topic-upsert 建节点、各深读步用 topic-status 推进、收尾 background_update.md 置 done。本文件定义视图怎么生成/怎么读、状态机流转（含 v1 生成态 draft_textbook）、命名约定（topic 主键 vs source 随文前缀）。schema/CLI 见 background_db.md。
---

# obsidian 主题枢纽（MOC）：DB 渲染的视图

> **定位**：单主题的唯一入口。**真相源是 `background.db` 的 `topics` 表**（schema/CLI 见 `background_db.md`）；`{topic}_hub.md` 是 `background.py topic-render` 从表里**生成的视图**，不再手写、不手改。obsidian 照常读这份生成的 md（Dataview 也能在其 frontmatter 上工作）。
> **谁来填**：`topic_map.md` 用 `topic-upsert` 建节点（`status=planned`）；各深读步用 `topic-status` 推进；`background_update.md` 收尾置 `done`。**改了 DB 就重跑 `topic-render` 刷新视图。**

---

## 1. hub 视图怎么生成

```powershell
python $env:LEARNING_PIPELINE\scripts\background.py topic-render SIMPL    # → SIMPL_hub.md（DB→视图）
```

生成的 `{topic}_hub.md` 含：① frontmatter（下表字段，全部来自 `topics` 表）；② 状态机当前位置；③ 目标 / 核心问题；④ 各阶段产物的链接（按命名约定，见 §3）；⑤ **本 topic 贡献的 `S_have`**（从 `s_have` 表按 `topic` 取，`shaky` 标注）。视图顶部带 `generated_by: background.py`——**勿手改**，要改内容改 DB 再渲染。

### frontmatter 字段（= `topics` 表列）
| 字段 | 含义 |
|---|---|
| `topic` | 主键，与各归档类产物前缀一致 |
| `status` | 状态机，见 §2 |
| `roi` | high / mid / low |
| `objective` | 一句话目标 |
| `deps` | 前置 topic（DAG 的边） |
| `tags` | 检索标签（领域/方法/角色） |
| `source_hint` | 候选材料方向种子（`topic_map` 填，`source_selection` 消费） |
| `source` | 主材料文件名主体；随文产物 `{source}_qa/`、`{source}_prereq` 用它（见 §3） |
| `updated` | 最近推进日期（绝对日期） |

---

## 2. status 状态机（真相源在 DB；含 v1 生成态）

```
planned → collect → prereq → [draft_textbook] → reading → archive → textbook → review → done
```
| 状态 | 由谁推进（`topic-status`） |
|---|---|
| `planned` | `topic_map.md`（`topic-upsert` 建节点即 planned） |
| `collect` | `source_selection.md` |
| `prereq` | `prereq_and_objectives.md` |
| **`draft_textbook`** | `source_to_textbook.md`（收料 → 主教材 **v1**；**可选**：源单一可直读则跳过此态，直接 `reading`） |
| `reading` | `qa_note.md`（读 v1 或收料，随文 QA） |
| `archive` | `qa_to_archive.md` |
| `textbook` | `note_to_textbook.md`（模式 B：v1→QA 融合 **v2**；或模式 A：从 QA 从零建） |
| `review` | `to_review_cards.md` |
| `done` | `background_update.md`（`have-add` 写台账后 `topic-status done`） |

> **`draft_textbook`（修 #4）**：以前 v1 主教材生成出来却没有对应状态、只能挂在 `reading`，使"reading 态下已有 .tex 教材"语义别扭；现在显式成态。**v1、v2 是同一文件 `{topic}_Textbook` 的演进**（v2 不另起名）。
> **置 `done` 前置**：必须先 `background_update.md` 把本轮 `S_have`（含 `shaky` 项）`have-add` 进 `s_have` 表。没回填不算闭环、不置 done。
> 状态**回退**（返工，如 textbook→reading）允许，`topic-status` 会提示 `⚠️ 状态回退` 并记 `changelog`。

---

## 3. 命名约定（topic 主键 + source 随文前缀，修 #5）

- `{topic}` 是主键，**归档类产物**一律 `{topic}_*`：`{topic}_sources` / `{topic}_arrangement` / `{topic}_原文素材归档` / `{topic}_Textbook` / `{topic}_review` / `{topic}_hub`。
- `{source}`（= `topics.source`，主材料文件名主体）用于**随文产物**：`{source}_qa/` / `{source}_prereq`。`topic-render` 据 `source` 字段生成正确链接——**映射显式存 DB，不靠"前缀恰好相同"**（旧约定在 source≠topic 时自相矛盾，这里根治）。
- 预习组统一 `{topic}_预习_*`（与主组命名空间分离）。
- 详见 `background_db.md §4`。

---

## 4. 总览进度看板

```powershell
python $env:LEARNING_PIPELINE\scripts\background.py board --out 学习总览_MOC.md   # 全 topic 一张表
```
`board` 直接从 `topics` 表生成 markdown 表（topic / status / roi / deps / objective / updated），**不依赖 Dataview 插件、不靠扫 frontmatter**。若仍想用 obsidian Dataview，它照样能在 `topic-render` 生成的各 hub frontmatter 上聚合。

---

## 5. 约定

- **DB 是唯一真相源**：topic 的 status / 元数据只在 `topics` 表里维护；`{topic}_hub.md`、`学习总览` 都是视图——改完 DB 重渲染，**不手改视图**。
- **status 单调推进**为主（`topic-status`，顺手刷新 `updated`）；回退允许但留痕。
- **命名前缀**：归档类用 `{topic}`、随文类用 `{source}`，映射记在 `topics.source`（§3）。
