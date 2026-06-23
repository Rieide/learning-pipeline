---
name: background-db
description: 个人背景「结构化台账」的权威契约（schema + CLI + 约定）。把 topic 状态/元数据与 S_have 知识资产从非结构化 markdown 升级为 SQLite（topics 主键 + s_have 按领域 FK→topic + changelog），由机械层脚本 scripts/background.py 读写/校验/渲染。差集只读相关领域（治 #2 全量重读），回填按 (domain,id) 幂等去重（治 #6 双入口重复），能力现状表与 obsidian hub 都退化为「由 DB 生成的视图」。个人基线（身份/出身/入职基线锚点）单独用 baseline.yaml 手编、不进 DB。本文件是被 prereq/background_update/weekly_review/topic_map/topic_hub 共同引用的契约层（类比渲染层 to_tex.md），它们只描述「语义怎么判断」，读写格式统一看这里。
---

# 背景结构化台账：schema + CLI 契约（机械层 background.py）

> **定位**：这是个人背景的**契约层 / 真相源定义**，与渲染层 `tool_prompts/to_tex.md` 同性质——被多个 prompt 引用、自己不是认知顺序上的一步。`prereq_and_objectives.md`（读 S_have）、`background_update.md` / `weekly_review.md`（写 S_have + 推进 status）、`topic_map.md`（建 topic）、`topic_hub.md`（渲染 hub 视图）都遵循本文件。
> **一句话**：LLM 只做**语义判断**（这条算不算新增能力、归哪个领域、是否仍存疑、topic 该进哪个状态）；**读、写、校验、渲染都交给 `scripts/background.py` + SQLite**——与 `qa_archive.py` 同一"机械步下沉、工程锁死"的哲学。

---

## 0. 为什么结构化（补的是哪些缺陷）

非结构化 markdown 台账有四个结构性毛病，结构化后逐一根治：

| 旧毛病 | 结构化后 |
|---|---|
| **#2 差集每轮全量重读整本台账**（主题越多越慢、越不准） | `have-query --domain X` 只读相关领域，按领域分区 |
| **#6 两个回填入口（主题驱动 / 周复盘）对同一能力重复计入** | `have-add` 按 `(domain,id)` 幂等 upsert，重复写=更新不新增 |
| **能力现状表与台账两处漂移**（要靠"以台账为准"的人肉纪律） | `have-table` 由 DB 生成，表是视图不是第二真相源 |
| **topic 状态/元数据散落在各 hub 的 frontmatter，无法统一查询** | `topics` 表为唯一真相源，`{topic}_hub.md` 由 `topic-render` 生成 |

---

## 1. 三层存储（按性质分离，不塞进一个库）

环境变量 `$PERSONAL_BACKGROUND` 现在指向 workspace 里的 **`background/` 目录**（不再是单个 .md 文件）：

```
$PERSONAL_BACKGROUND/                ← background/ 目录
├─ baseline.yaml      个人基线：身份 / 出身 / 入职基线锚点。低频、手编、YAML。脚本不碰。
├─ background.db      本脚本管的 SQLite：topics + s_have + changelog。topic/S_have 的唯一真相源。
├─ WORK_LOG.md        动态流水账：周进度 / 切入点 / 排障细节。不进差集。脚本不碰。
├─ <topic>_hub.md     由 `background.py topic-render` 生成的 obsidian 视图（勿手改）。
└─ 能力现状表.md       由 `background.py have-table` 生成的视图（可选）。
```

> **为什么基线单独 YAML、不进 DB**：基线是低频、人读人改的稳定锚点（差集的"地平线"），不需要查询/聚合；DB 管的是高频累积、要被差集相减的 S_have 与要被程序消费的 topic 状态。"不要一个库解决所有存储"。

`background.py` 的 `--db` 默认解析为 `$PERSONAL_BACKGROUND/background.db`，各 prompt 调用时一般无需显式给 `--db`。

---

## 2. Schema（`scripts/background.py init` 建表）

```sql
topics (                              -- topic 为主键；唯一真相源
  topic TEXT PRIMARY KEY,
  status TEXT,        -- 状态机，见 §3
  roi TEXT,           -- high|mid|low
  objective TEXT,
  deps TEXT,          -- JSON 数组：前置 topic（DAG 的边）
  source_hint TEXT,   -- JSON 数组：候选材料方向种子（topic_map 填，source_selection 消费）
  tags TEXT,          -- JSON 数组
  source TEXT,        -- 主材料文件名主体；QA 落 {source}_qa/。解决 #5（topic↔source 显式记录）
  created TEXT, updated TEXT, note TEXT
)

s_have (                              -- 知识资产台账；差集要相减的集合
  domain TEXT,        -- 领域 key：prediction / concurrency / systems / toolchain …
  id TEXT,            -- 领域内稳定唯一 slug
  capability TEXT,    -- 具体到"可被差集相减"的颗粒（不是"学了 X 主题"）
  status TEXT,        -- mastered | shaky（shaky = 负向知识"仍存疑/未深入"）
  topic TEXT,         -- FK -> topics.topic（哪个 topic 贡献的）
  grp TEXT,           -- main | prereq（两段分离：主组 vs 预习组跨域底子）
  source TEXT,        -- pipeline | weekly | manual
  added TEXT, note TEXT,
  PRIMARY KEY (domain, id),           -- 幂等 upsert 的依据（治 #6）
  FOREIGN KEY (topic) REFERENCES topics(topic)
)

changelog (ts, kind, ref, note)       -- 每次 upsert/状态切换自动留痕
```

---

## 3. 状态机（含 #4 修复：v1 生成态 `draft_textbook`）

```
planned → collect → prereq → [draft_textbook] → reading → archive → textbook → review → done
(topic_map)(source_  (prereq_  (source_to_       (qa_note (qa_to_   (note_to_  (to_review (background_
            selection) and_obj)  textbook v1,可选)  随文)    archive)  textbook   _cards)    update 写台账后
                                                                      v2)                  置 done)
```

- **`draft_textbook`**（新增，修 #4）：跑 `source_to_textbook.md` 从收料生成主教材 **v1（阅读底本）** 时的状态。以前 v1 存在却只能挂在 `reading`，使"reading 态下已有 .tex 教材"语义别扭；现在显式成态。源单一可直读、走 QA 优先时**跳过**此态，`prereq → reading`。
- `topic-status` 校验目标是合法枚举；**回退**（如 textbook→reading 返工）允许但会打印 `⚠️ 状态回退`并记 changelog。

---

## 4. 命名约定（topic 主键 + `source` 字段，修 #5）

旧约定说"同主题的 prereq/qa/归档/textbook/review 共用前缀"，但随文产物用**材料文件名** `{source}`、归档类产物用**主题名** `{topic}`，当二者不同（如材料 `2402.02519v1.pdf` vs 主题 `SIMPL`）时前缀并不统一、约定自相矛盾。

**新约定（显式记录映射，不再假装前缀统一）：**
- `{topic}` 是**主键**，归档类产物一律 `{topic}_*`：`{topic}_sources` / `{topic}_arrangement` / `{topic}_原文素材归档` / `{topic}_Textbook` / `{topic}_review` / `{topic}_hub`。
- `{source}` 是**主材料文件名主体**，随文产物用它：`{source}_qa/` / `{source}_prereq`。`{source}` 记在 `topics.source` 字段里，`topic-render` 渲染 hub 时据此生成正确链接——**映射显式存 DB，不靠"前缀恰好相同"**。
- 预习组统一 `{topic}_预习_*`（即把 `{source}` 取成 `{topic}_预习`），与主组 `{topic}_*` 命名空间分离。

> 当主材料就以主题命名（`source == topic`）时，一切退化为旧的"统一前缀"，无额外负担。

---

## 5. CLI 速查（典型调用；完整见 `python scripts/background.py -h`）

| 子命令 | 谁调用 | 典型 |
|---|---|---|
| `init` | 一次性 | `background.py init` |
| `topic-upsert <topic> [--status --roi --objective --deps --source-hint --tags --source]` | `topic_map`（建节点）/各步推进元数据 | `background.py topic-upsert SIMPL --roi high --deps VectorNet,prediction-proto --source 2402.02519v1` |
| `topic-status <topic> <status>` | 各深读步推进 | `background.py topic-status SIMPL reading` |
| `topic-render <topic> [--out]` | 需要 obsidian 视图时 | `background.py topic-render SIMPL` → `SIMPL_hub.md` |
| `board [--out]` | 总览看板 | `background.py board --out 学习总览.md` |
| `have-add --domain --id --capability [--status --topic --group --source]` | `background_update` / `weekly_review` | `background.py have-add --domain prediction --id simpl-symmetry --capability "对称/视角无关表示" --topic SIMPL` |
| `have-query [--domain… --topic --group --status --format]` | `prereq_and_objectives`（差集读 S_have） | `background.py have-query --domain prediction concurrency` |
| `have-domains` | 概览 | `background.py have-domains` |
| `have-table [--out]` | 生成能力现状表视图 | `background.py have-table --out 能力现状表.md` |
| `validate` | 收尾自检 | `background.py validate` |

> 调用前缀按 README：`python $env:LEARNING_PIPELINE\scripts\background.py …`，`--db` 默认 `$PERSONAL_BACKGROUND/background.db`。

---

## 6. 各 prompt 怎么用它（职责切分）

- **`topic_map.md`**：每拆出一个节点 → `topic-upsert`（写 status=planned/roi/objective/deps/source_hint）。不再手写 hub 文件。
- **`source_selection.md` / 各步**：推进 `topic-status`；`source_selection` 确定主材料后顺手 `topic-upsert --source <主材料名>`。
- **`prereq_and_objectives.md`**：`S_have` = **baseline.yaml 锚点（直接读）** ∪ **`have-query --domain <相关领域>`（累积台账）**；差集只读相关领域，`shaky` 项不当已会、进 `S_bridge`。
- **`background_update.md` / `weekly_review.md`**：把"真正内化的能力"→ `have-add`（幂等，标 `--group main|prereq`、`--status mastered|shaky`、`--topic`、`--source pipeline|weekly`）；收尾 `topic-status <topic> done`。语义判断（算不算新增、归哪域、是否存疑）在那两份里讲，格式在这里。
- **`topic_hub.md`**：定义 hub 视图怎么由 `topic-render` 生成、怎么读；DB 是真相源，hub 勿手改。

---

## 7. 一次性迁移（旧 markdown 台账 → DB）

旧 `PERSONAL_BACKGROUND.md` 的"知识资产台账 / 能力现状表 / topic 状态"是散文，需**语义解析**，交给 LLM 一次性转换（不是机械脚本能做的）：

1. `background.py init` 建空库。
2. 让 LLM 通读旧台账，对**每个历史 topic** 产一条 `topic-upsert`（补 status/roi/objective/deps/source）。
3. 对台账里**每条已掌握/仍存疑能力**产一条 `have-add`（判定 domain、给稳定 id、标 group/status/topic）。
4. 把旧"稳定区身份/出身/入职基线"誊进 `baseline.yaml`；旧"周进度/切入点"留 `WORK_LOG.md`。
5. `background.py validate` 校验 FK/枚举；`board` / `have-table` 渲染视图，与旧文件人工核对一遍。
6. 重设环境变量 `$PERSONAL_BACKGROUND` 指向新的 `background/` 目录。

---

## 8. 硬边界

- ✅ LLM 只产**语义决策**（能力颗粒/领域/存疑/状态）并据此调 `background.py`；读写校验渲染全归脚本。
- ❌ 不手改 `background.db`、不手改 `topic-render`/`have-table` 生成的视图文件（改 DB 再重渲染）。
- ❌ 不把**周进度/TODO/排障流水**写进 DB——那是 `WORK_LOG.md`；DB 只装"可被差集相减的能力 + topic 元数据"。
- ❌ 不把**基线锚点**（身份/出身/入职基线）塞进 `s_have`——它们在 `baseline.yaml`，是差集的地平线、不是累积项。
- ✅ 能力颗粒度写到"可被 `have-query` 直接当 `S_have` 相减"：具体概念/方法/工程点，不是"学了某主题"。
