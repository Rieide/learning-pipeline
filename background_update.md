---
name: background-update
stage: B/done(主题驱动)
when: 一个主题收尾，把新增能力写回台账
reads: 教材 / 复习卡 / 目标问题
writes: s_have(have-add) + topic-status done
description: 单主题深读流水线收尾后，把"这一轮新掌握了什么"用 background.py have-add 幂等写进结构化台账（SQLite 的 s_have 表，按领域 key、FK→topic；见 background_db.md），让下次 prereq 差集解析更准。强调写成"可被差集相减的颗粒度"（具体能力/概念，而非"学了某主题"）、按领域归位、标 main/prereq 组、把"仍存疑/未深入"记为 status: shaky 负向知识；幂等 upsert 天然防主题/周复盘双入口重复计入。收尾 background.py topic-status <topic> done。
---

# 阶段式个人背景更新（流水线闭环）

> **定位**：单主题深读流程的**最后一步**，在 `to_review_cards.md` 之后。把本轮学习产出写回**结构化台账**（`$PERSONAL_BACKGROUND/background.db` 的 `s_have` 表），喂养下一轮 `prereq_and_objectives.md` 的差集解析。**字段/枚举/CLI 一律见 `background_db.md`**，本文件只讲"语义怎么判断"。
> **为什么需要**：prereq 差集 = `S_need − S_have + S_bridge`，其中 `S_have` 查自 `s_have` 表。`S_have` 越新鲜、颗粒越细、领域越全，差集越准。每完成一个主题就 `have-add` 一次，是这条依赖的闭环。

> **三层存储（回填时分清写哪个，见 `background_db.md §1`）**：
> - **`background.db` 的 `s_have` 表**：本步主战场——`have-add` 幂等写入"可被差集相减的能力"。**按 `(domain,id)` upsert 天然防重复计入**，与 `weekly_review.md` 共写同一能力也不双计（治 #6）。
> - **`baseline.yaml`**（个人基线，手编 YAML）：身份/出身/入职基线锚点。**本步原则上不动**；确需证伪/升级稳定事实才显式改它。
> - **`WORK_LOG.md`**（动态日志，同目录）：周进度/切入点/排障流水。**"工作进度/TODO 勾选"写这里，不写进 DB**（否则退回"进度污染背景"老问题）。

---

## 0. 目标（一句话）

把刚完成的主题里**真正内化为能力的部分**，用 `background.py have-add` 幂等写进 `s_have` 表，使其成为下次差集解析的精确依据——既补"现在已会"（`mastered`），也记"仍存疑"（`shaky`）。

**两个不可动摇的落点：**
- **幂等写，不手攒文本**：能力进 `s_have` 表（按领域 key），重复写同一 `(domain,id)` 是更新不是新增；`baseline.yaml` 的稳定事实（身份、出身、入职基线）原则上不动，确需证伪/升级才显式改。
- **写成可相减的颗粒度**：每条 `--capability` 要用 `prereq` 能直接当 `S_have` 相减的语言——**具体概念/方法/工程能力**，而非"学了 X 主题"这种粗粒度结论。

---

## 1. 触发时机

- 一个主题的深读流水线走到 `to_review_cards.md` 产出复习卡之后（即将把 hub `status` 置为 `done` 之前）。
- 也可在大里程碑（如一周收尾、中期汇报前）批量补记，但优先随主题即时记。

---

## 2. 提炼方法：本轮到底新增了哪些 S_have

对照三处材料，抽出"现在比开始这个主题前多会了什么"：

1. 该主题的**教科书 `.tex`**（主教材 v2 与/或预习教材 v2）与**素材归档**（讲透了哪些概念/推导）。
2. 该主题的**复习卡**（哪些是真正要长期记住的关键概念/误区澄清）。
3. 该主题读前的**阅读目标问题**（哪些已能回答 = 已达成）。

抽取时做**差分**：只记"相对开始前新增/纠正"的。已声明过的即使重写也无害——`have-add` 幂等，同 `(domain,id)` 自动更新不新增。

> **分组回填（预习组 vs 主组，靠字段而非两张表区分）**：
> - **主材料组**（`{topic}_*`）的 S_have = **topic 专属**：`have-add --group main --topic {topic} --domain <该 topic 所属领域>`。
> - **预习组**（`{topic}_预习_*`，见 `prereq_to_textbook.md` / `qa_note.md`）的 S_have = **跨领域基础底子**（如"进程内存模型""data race 定义""-g/-O0 调试构建"）：`have-add --group prereq --topic {topic} --domain <该底子真正所属领域，如 systems / concurrency / toolchain>`。预习底子按**它自己的领域**归位（可惠及未来多个 topic 的差集），别塞进 topic 的主领域。
> 两组靠 `--group` + `--domain` 自然分开，能力画像分得清"底子 vs 专精"——不再需要"基础行/topic 行"的人肉表格区分。

---

## 3. 怎么写：一条能力 = 一次 have-add（字段见 `background_db.md §5`）

把本轮提炼出的每条能力，落成一条幂等命令（`--id` 给领域内稳定 slug，便于以后更新同一条）：

```powershell
# 新增已掌握（→ 并入 S_have，下次差集视为"已会"，不再展开）
python $env:LEARNING_PIPELINE\scripts\background.py have-add `
  --domain prediction --id simpl-symmetry `
  --capability "对称/视角无关表示、相对位姿编码、instance-centric 消息传递" `
  --status mastered --group main --topic SIMPL --source pipeline

# 仍存疑/未深入（→ status: shaky；下次差集**不要**默认已会，遇到要补 S_bridge）
python $env:LEARNING_PIPELINE\scripts\background.py have-add `
  --domain concurrency --id thread-pool `
  --capability "多线程 thread_pool 只认识、未深入" `
  --status shaky --group prereq --topic SIMPL
```

- **`mastered` vs `shaky`** 是关键设计：`shaky` 是负向知识，让差集更准——避免下次把没真懂的误判为已会而跳过。
- **`--id` 稳定**：同一条能力以后深入了，用同一 `--domain/--id` 再 `have-add --status mastered` 原地升级，不产生重复条目。
- **心智模型变化 / 本轮叙事**：不进 `s_have`（那是"能力清单"）；值得留就写 `WORK_LOG.md`。

---

## 4. 同步更新（大多是自动的）

- **能力现状表**：不用手动维护——它是 `background.py have-table` 由 `s_have` 表生成的**视图**。要看就重渲染：`have-table --out 能力现状表.md`。
- **变更记录**：`have-add` / `topic-status` 已自动写 `changelog` 表，无需手记。
- **工作进度 / TODO**：若该主题对应的 TODO 已完成，在 `WORK_LOG.md` 里勾掉/更新（**不写进 DB**）。
- **置 done + 刷新视图 + 自检**：
  ```powershell
  python $env:LEARNING_PIPELINE\scripts\background.py topic-status {topic} done
  python $env:LEARNING_PIPELINE\scripts\background.py topic-render {topic}   # 刷新 obsidian hub 视图
  python $env:LEARNING_PIPELINE\scripts\background.py validate              # FK/枚举/JSON 自检
  ```

---

## 5. 硬边界

- ❌ 不把整份教科书摘要塞进 DB——`s_have` 只记"可相减的能力颗粒"，详情留在各主题产物里（hub 视图自动链）。
- ❌ 不臆测作者掌握程度：拿不准就 `--status shaky`，宁可下次差集多补，也不要误判已会。
- ❌ 不在 DB 里记基线锚点（身份/出身/入职基线）——那在 `baseline.yaml`；确需改稳定事实，显式改 `baseline.yaml` 并在 commit/note 里标注（如"⚠️ 原'出身纯 LLM 方向'修正为…"）。
- ❌ 不手改 `background.db` 或生成的视图（能力现状表 / hub）——一律经 `have-add` / `topic-*`，改完重渲染。

---

## 6. 开工前应确认

- 本轮主题的教科书 / 复习卡 / 归档路径（取料用）；topic 名与各能力的 `--domain` 归位。
- 哪些是 `mastered`、哪些只能 `shaky`——拿不准逐条问，不替作者拔高。
- 是否随主题即时记，还是并入某个里程碑批量记（幂等，批量补记不会重复计）。
