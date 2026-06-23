---
name: source-selection
stage: B/collect
when: 有 theme、材料待获取，要定确定且范围可控的资料清单
reads: topics 节点(topic-show) + s_have(have-query)
writes: {topic}_sources.md + topics.source
description: 「资料收集」环节，填补 topic_hub 状态机里早就预留、却一直没有 prompt 的 collect 槽位。输入：topics 表里的该 theme 节点（topic-show，带 objective / roi / align / source_hint）+ 背景 S_have（have-query）。输出：一份「确定的、范围可控的资料清单」{topic}_sources.md，每条标注类型 / 选它的理由（对齐 objective 哪部分）/ 范围裁剪（读哪几节·哪几页·哪几个函数，对抗"通读"）/ 优先级 + 可砍。硬边界：服务 objective 不做综述式铺料、按 align 降级取材、用 S_have 剔冗余；产出物正是 prereq_and_objectives.md 抽 S_need 的输入。把「主题」变成「一份确定材料」，让差集链在材料待获取时也能闭合。
---

# 资料收集：theme → 确定的、范围可控的资料清单

> **定位**：宏观拆分（`topic_map.md`）与单主题深读（`prereq_and_objectives.md` → …）之间的桥接环节，对应 `topic_hub.md` 状态机里的 **`collect`** 状态。链条是 `topic_map`（拆出 theme，材料待获取） → **本步（把 theme 变成确定材料）** → `prereq_and_objectives`（从确定材料抽 `S_need`）。
> **为什么需要（补的是哪个缺环）**：整条 pipeline 早期默认了"材料是给定的"（论文 / 源码 / 教材已经在那）。一旦从 topic_map 拆出 theme，材料就从"给定"变成"待获取"——而 `prereq_and_objectives.md` 的差集公式 `S_need − S_have + S_bridge` 里，`S_need` 是"通读材料抽取出来的"。**没有材料，`S_need` 无从抽，整条差集链断在起点。** 本步把"主题 → 一份确定的、范围可控的阅读材料"补上，让差集链在材料待获取时也能闭合。这是 `collect` 这个空状态一直等待的 prompt。

---

## 0. 目标（一句话）

把一个 **theme（目标明确、但材料待定）**，收敛成一份**确定的、范围可控的资料清单**：每条都服务该 theme 的 objective、标好"读哪几节"、可被 `prereq_and_objectives.md` 直接拿去抽 `S_need`。

**两个不可动摇的落点：**
- **服务 objective，不铺综述**：选材以"达成该 theme 的 objective 所必需"为准绳，不做领域百科式铺料。
- **范围可控，对抗通读**：每条资料必须标"读哪几节 / 哪几页 / 哪几个函数"，而不是整本 / 整篇。**范围裁剪是本步最核心的价值。**

---

## 1. 输入

- **topics 表里的该 theme 节点**（`background.py topic-show {topic}`）：`objective` / `roi` / `align` / `deps` / `source_hint`（候选材料方向的种子）。`align` 决定取材深度（§2.2）。
- **背景 `S_have`**（`background.py have-query --domain <相关领域>`）：判断 `source_hint` 里哪些候选对作者是冗余的（已在 `S_have` → 剔除或仅复习），哪些是真缺。

> `source_hint` 只是**方向种子**（"大概去哪类材料找"）；本步负责把它**确定到"具体哪一份 + 读哪一部分"**，并把确定的主材料名 `topic-upsert --source` 回写 `topics` 表（供随文产物命名）。

---

## 2. 选材与裁剪原则

1. **objective 驱动**：先把 theme 的 objective 拆成 2–4 个"要回答 / 要会"的子点；每条入选资料都要对应它覆盖 objective 的哪个子点。**覆盖不到 objective 的资料不选。**
2. **按 `align` 降级取材（关键）**：theme 的 `align` 决定取材**深度**——
   - 标"只认识 / 只对齐坐标系 / 只到接口"的 theme → 只取**概念地图 / 综述 / 接口文档**级材料，不取深啃材料；
   - 标"深入 / 精读"的 theme → 才取论文精读 / 源码精读级材料。
   降级直接决定取材深度，别给降级 theme 配深啃材料。
3. **用 `S_have` 剔冗余**：`source_hint` 里作者已掌握的（`have-query` 命中 `S_have`）只标"已会，跳过 / 仅复习"，不作为新材料铺开。
4. **范围裁剪 > 数量**：宁可 3 条精确裁剪，不要 10 条整本。每条给"读哪几节 / 页 / 函数 + 预计篇幅"。
5. **标优先级与可砍**：每条 `high / mid / low` + 可砍标记；进度落后时按此砍，保住覆盖 objective 主干的那几条。

---

## 3. 产出格式

文件名 `{topic}_sources.md`，与该 theme 的 hub 同级（workspace）。结构：

```markdown
# {topic} — 资料清单（collect）
> 服务 objective：<复述 theme 的 objective>
> align（取材深度）：<降级说明，如"只到接口级">
> 下游：prereq_and_objectives.md 从本清单抽 S_need。

## objective 拆解（选材靶子）
- O1 …
- O2 …

## 资料清单
| # | 资料（含定位/链接） | 类型 | 覆盖 objective | 范围裁剪（读哪几节/页/函数） | 优先级 | 可砍 |
|---|---|---|---|---|---|---|
| 1 | … | 论文/文档/源码/书章节/blog | O1,O2 | 仅 §3–4 / pp.x–y / `Foo()` | high | 否 |

## 取材决策记录（为什么没选）
- X：<对齐不上 objective / 已在 S_have / 已被第 N 条覆盖>
```

---

## 4. 硬边界

**不能做：**
- ❌ **领域综述式铺料**：不为"完整 / 全面"而加入与 objective 无关的材料。
- ❌ **出"整本 / 整篇"无裁剪条目**：每条都必须有范围裁剪。
- ❌ **违 `align` 越级取材**：降级 theme 不配深啃材料。
- ❌ **复述 `S_have`**：作者已会的不作为新材料铺开。

**必须做：**
- ✅ **产出即 `prereq` 的 `S_need` 抽取输入**：清单 + 裁剪范围合起来，就是 `prereq_and_objectives.md` §1 所说"本材料所需工具/概念集合"的来源——它通读的不再是"凭空的材料"，而是本步选定且裁剪过的那几份。

---

## 5. 与上下游接口 / 状态机

- **上游 `topic_map.md`**：从 `topics` 表（`topic-show`）取 theme 的 `source_hint`（候选种子）+ `objective` / `align`。
- **下游 `prereq_and_objectives.md`**：其 §1"通读材料抽 `S_need`"中的"材料"= 本步产出的 `{topic}_sources.md` 选定且裁剪的材料；范围裁剪让 `S_need` 抽取也聚焦，不被无关章节稀释。
- **状态机**：开工 `background.py topic-status {topic} collect`；确定主材料后 `background.py topic-upsert {topic} --source <主材料名>`（回写映射）；产出清单后 `topic-status {topic} prereq` 交给 `prereq_and_objectives.md`。清单命名 `{topic}_sources.md`（归档类用 `{topic}` 前缀）。

---

## 6. 开工前应确认

- 是哪个 theme（topic_map 节点）；其 `objective` / `align` / `source_hint` 是否齐全（缺 `align` 则无法判断取材深度）。
- 时间预算（决定清单长度与可砍线）。
- 是否有作者指定的必含 / 必排除资料。
