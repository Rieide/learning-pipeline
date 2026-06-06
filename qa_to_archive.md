---
name: qa-to-archive
description: 把 {source}_qa/ 里的单文件 QA 归档成「原文素材归档」文档的规范——但机械搬运彻底交给脚本。LLM 只读每个 QA 的导航字段(summary/questions/chapter_hint)，输出一张编排表(YAML：章节骨架 outline + 每个 QA id 归到哪个标题、排第几 placement + 去重 drop/dup_of)；正文由 qa_archive.py assemble 按 ID 字节级从源文件搬运拼接，并做哈希守恒/计数守恒/id 唯一性校验。LLM 全程不碰正文、不碰 content_hash，从工程上锁死"重排时改字"的幻觉。它是 qa_note.md 与 note_to_textbook.md 之间的一环，产出物正是 note_to_textbook.md 期望的输入。
---

# QA 归档：LLM 出编排表 + 脚本保真拼接

> **定位**：单主题深读流程的中间环节，承上启下：
> 上游 `qa_note.md`（单文件 QA，带 front-matter） → **本步** → 下游 `note_to_textbook.md`（重写成教科书内容 → `to_tex.md` 渲染）。
> `note_to_textbook.md §1` 假设的"已三道加工（按主题归档→章内重排→去重）的非结构化 note"，**正是本步 `assemble` 的产出**。

---

## 0. 目标与职责切分（一句话）

把散落在 `{source}_qa/` 的单文件 QA，**重组**成一份有逻辑主线、章节归位、去掉明显重复、但逐字不改正文的原文素材归档文档。

**职责切分（这是本次重构的灵魂）：**
> **LLM 只做编排决策，脚本做机械搬运。** LLM 读导航字段，输出"哪个 QA 去哪个标题、排第几、丢不丢"的编排表；正文一律由 `qa_archive.py assemble` 按 ID 从源文件**字节级搬运**。LLM 全程**不打开、不复制、不改动任何 QA 正文**——"只重排不改字"不再靠自律，而是靠"它根本碰不到正文"这一工程事实保证。

---

## 1. 输入

- 一个 `{source}_qa/` 文件夹（同一主题、多阶段累积的单文件 QA）。每个文件已含导航字段，且应已 `finalize`（`content_hash`/`status: final`）。
  - 若尚未 finalize：先 `python $env:LEARNING_PIPELINE\scripts\qa_archive.py finalize {source}_qa`。
- 可选：`prereq_and_objectives.md` 的阅读目标问题（规划章节骨架用）。

> **LLM 只读 front-matter 的导航字段**（`title`/`summary`/`questions`/`chapter_hint`/`related`）来做编排判断。**不需要、也不应该读正文区**——读正文只会诱使你去"搬运/改写"，那是脚本的活。

---

## 2. 产出：一张编排表（YAML）

LLM 的**唯一产物**是编排表 `{topic}_arrangement.yaml`，结构如下（这就是 `qa_archive.py assemble` 消费的格式）：

```yaml
topic: SIMPL
note: 本文件为按逻辑主线归档+章内重排+去重后的原文素材，文字未改写；下游教科书化见 note_to_textbook.md。
outline:                              # 第1步：章节骨架（不碰任何正文）
  - {id: ch1,  level: 1, title: 动机与问题设定}
  - {id: ch2,  level: 1, title: 对称 / instance-centric 表示}
  - {id: s2_1, level: 2, title: 为什么要视角无关}
placement:                            # 第2/3步：归位 + 排序 + 去重（纯决策）
  - {qa: QA_0017, under: s2_1, order: 1}
  - {qa: QA_0009, under: s2_1, order: 2}
  - {qa: QA_0031, drop: true, dup_of: QA_0017}   # 明显重复 → 丢弃（可审）
```

字段说明：
- `outline`：有序标题列表，`id` 任意但唯一，`level` 控制 `#` 级数。
- `placement`：每个 QA 一条。归位项给 `under`（必须是某 outline id）+ `order`（同标题内排序）；丢弃项给 `drop: true`（建议附 `dup_of` 便于复查）。
- **守恒要求**：文件夹里**每个** QA 必须在 `placement` 里出现恰好一次——要么归位、要么标 `drop`。漏掉会被脚本判为"未编排"而报错。

---

## 3. 三步加工（顺序不可乱，但全部是"决策"而非"搬运"）

### 第 1 步：宏观展开逻辑主线（搭 `outline`）
不碰任何 QA，只依据主题内在逻辑（参考阅读目标问题、材料章节结构）列出章节骨架：先整体后细节、动机→机制→闭环。骨架是"这份素材应按什么主线展开"，不是 QA 的产生顺序。

### 第 2 步：归位（填 `placement` 的 `under`）
按每个 QA 的**导航字段**（`title`/`summary`/`chapter_hint`）判断它逻辑上最该属于哪个标题。一个 QA 跨多个主题时，归到它**最主要**的标题，不切碎。此步只产决策，不搬正文。

### 第 3 步：章内排序 + 去重（填 `order` / `drop`）
- **章内排序**：同一 `under` 下用 `order` 按叙述逻辑排（动机在前、推导其次、小结在后）。
- **去重**：只对**明显重复的副本**（同一问几乎原样问了两遍）标 `drop: true` + `dup_of`。
- **故意保留**：提问演进、走过的弯路、自我纠正、前后说法的澄清——这些是认知轨迹，是下游"常见误区→澄清"的原料，**绝不当冗余 drop**。

---

## 4. 执行拼接（脚本）

编排表写好后，跑：
```powershell
python $env:LEARNING_PIPELINE\scripts\qa_archive.py assemble {source}_qa `
       --plan {topic}_arrangement.yaml --out {topic}_原文素材归档.md
```
脚本会：先 `verify` 整个文件夹（哈希/ id 一致与唯一）；再按 `outline` 顺序、`placement` 的 `under`+`order` 把**正文按 ID 从源文件字节级取出**拼接；最后报告**计数守恒**（归位 + 丢弃 == 总数）、**id 唯一性**、每块带 `<!-- QA_xxxx sha256:... -->` 出处注释。任一校验不过则非零退出、不产出脏文档。

---

## 5. 硬边界

**可以做：**
- 用 `outline`/`placement` 决定 QA 的归属、顺序。
- 用 `drop` 删除明显重复的整条 QA。
- 在 `outline` 里加结构性标题（骨架本身）。

**不能做：**
- ❌ 打开 / 复制 / 改写 / 摘要任何 QA 的正文（`## Q`/`## A`）——正文搬运是脚本的事。
- ❌ 触碰任何 QA 的 `content_hash` / `id`（机器验证字段，只读）。
- ❌ 外扩：编排表里不得出现 `{source}_qa/` 之外的内容；不得手写正文进归档文档。
- ❌ 把"看似矛盾/重复"的认知澄清痕迹当冗余 drop。

> 一句话：进归档文档的每一句正文，都由脚本从某个 QA 文件**字节级复制**而来（出处注释可回溯）；LLM 产出的只是"去哪、排第几、丢不丢"的编排表。

---

## 6. 开工前应确认

- 要归档哪个 `{source}_qa/`（路径）；是否已 finalize（没有则先跑）。
- 逻辑主线骨架采用材料原章节，还是按阅读目标重新组织。
- 编排表与归档文档的落位（默认 `{topic}_arrangement.yaml` + `{topic}_原文素材归档.md`，与 QA 文件夹同级）。
