# 开发日志（dev log）：设计要点 + 变更历史

> README 只讲「怎么用」；**为什么这么设计（设计要点）**与**历次改进（变更历史）**都放这里，保持 README 精简。
> 工具速查表见 `registry/REGISTRY.md`（由 `scripts/gen_registry.py` 从各 prompt 的 frontmatter 生成）。
> 以后所有改进/审计/重构的留痕都进本文件「二、变更历史」（newest-first）。

---

## 一、设计要点（相对早期流程的改动）

1. **补检索回路**（`to_review_cards.md`）：早期流程只编码不提取，新增复用 QA 的复习卡，几乎零成本。
2. **prereq 升级为 prereq+目标问题**：被动阅读 → 带靶子的主动阅读。
3. **固化归档铁律**（`qa_to_archive.md`）：最易 LLM 漂移、原先无治理的一环，写死"只重排不改字"。
4. **宏观拆分成 DAG**（`topic_map.md`）：周计划退化为切片。
5. **obsidian 枢纽用状态机**（`topic_hub.md`）：多主题并行可视化、可恢复。状态机现在活在 `topics` 表里（含 v1 生成态 `draft_textbook`，见要点 12），`{topic}_hub.md` 退为 `topic-render` 生成的视图。
6. **阶段式背景回填**（`background_update.md`）：每完成一个主题，`have-add` 把新增能力写进 `s_have` 表，闭合"差集读背景→学完写回背景"的唯一反馈环，下次读前更精准（结构化细节见要点 12）。
7. **编辑层 / 渲染层解耦**（`to_tex.md` 上提为通用渲染层）：把"怎么组织某类素材"（编辑层，**共三层**：`prereq_to_textbook.md` 预习路、`source_to_textbook.md` 主教材生成路、`note_to_textbook.md` 成稿/融合路）与"怎么渲染成有教科书味的 .tex"（渲染层：`tool_prompts/to_tex.md`）分开。渲染层只有一份、来源无关，教科书味标准也统一收归于此；新增来源只需加一份薄编辑层，复用同一渲染层（见设计要点 11）。
8. **机械搬运下沉脚本 / QA 单文件化**（`qa_note.md` + `qa_to_archive.md` + `scripts/qa_archive.py`）：把"重排归档"从 LLM 的生成式搬运改成"LLM 出编排表、脚本字节级搬运 + 哈希校验"。每个 QA 切成带 front-matter 的独立文件，机器验证字段（`id`/`content_hash`，LLM 只读）与导航字段（`summary`/`questions`…，LLM 可写）严格分离，正文保真。连"取号 + 建文件"也由 `qa_archive.py new` 原子完成（`O_EXCL` 占位），堵死"数错号→覆盖旧 QA"这个 verify 也抓不到的失败。LLM 拿到的是理解与编排能力，工程锁死的是"改原文 / 覆盖原文"这一最危险失败模式。
9. **补全 `collect` 缺环 / 资料收集**（`source_selection.md`）：早期 pipeline 默认"材料是给定的"，差集公式的 `S_need` 靠通读材料抽——可一旦从 `topic_map` 拆出 theme，材料变成"待获取"，`S_need` 无从抽、差集链断在起点。新增 `source_selection.md` 把"主题 → 确定的、范围可控的资料清单"补上（服务 objective、按 `align` 降级取材、范围裁剪对抗通读），恰好填上 `topic_hub` 状态机里早就预留却一直空着的 `collect` 槽位（状态机比 prompt 集更完整，是当初设计直觉预留的位置）。差集链由此在"材料待获取"时也能闭合：`source_selection` 出确定材料 → `prereq` 抽 `S_need` → 减 `S_have` → 出前置。
10. **预习组 / 主材料组两段分离**（`prereq_to_textbook.md` + `qa_note.md` + `background_update.md`）：预习内容是**跨领域基础底子、非完整 topic**，故"预习教材 + 预习QA"自成一组（`{topic}_预习_*` 命名空间），与"主材料 + 主QA"组（`{topic}_*`）**全程不并入同一份归档**——否则跨域基础会污染 topic 归档。两组**分别回填能力画像**：预习组 → 跨域基础底子（标归属领域、惠及多 topic 差集），主组 → topic 专属。让台账分得清"底子 vs 专精"，这正是 topic 内分两段的动机。
11. **主教材 v1→QA→v2 与三编辑层对称**（`source_to_textbook.md` + `note_to_textbook.md` 两模式）：补上「收料 → 结构化主教材 v1（阅读底本）」这一步，使三条编辑层对称——预习路（差集→预习教材）、主教材生成路（收料→v1）、成稿/融合路（QA→融合进 v1→v2），都喂同一渲染层 `to_tex.md`。`note_to_textbook` 因此分两模式：**无 v1 时从 QA 从零建**（QA 优先路），**有 v1 时把 QA 原地融合成 v2**（教材优先路）。两种顺序按源类型择一：密集/分散源走教材优先，单一可直读源走 QA 优先。模式 B 对**预习教材与主教材同样适用**（预习路也是 v1→QA→预习 v2，与主路对称）。这把"对同一主题最多三份产物"塌缩成"一本会进化的预习册 + 一本会进化的主教材"。
12. **个人背景结构化为 DB**（`background_db.md` + `scripts/background.py`，重构 #2/#4/#5/#6）：把非结构化 markdown 台账升级为 **SQLite 单库多表**——`topics`（topic 主键，唯一真相源；hub/看板退为 `topic-render`/`board` 生成的视图）+ `s_have`（按领域 key、FK→topic）+ `changelog`，个人基线单独留 `baseline.yaml`。四个结构性收益：① 差集 `have-query` **只读相关领域**，治"主题越多差集越慢/越不准"（#2）；② 回填 `have-add` 按 `(domain,id)` **幂等**，治 `background_update`/`weekly_review` 双入口重复计入（#6）；③ 能力现状表/hub 都是**生成视图**，根除"台账 vs 表"两处漂移的人肉纪律；④ 新增状态 `draft_textbook` 给主教材 v1 一个名分（#4），`topics.source` 字段显式记 `topic↔主材料` 映射、修正旧"统一前缀"在 `source≠topic` 时的自相矛盾（#5）。LLM 只做语义判断，读写校验渲染全归脚本——与要点 8 同一"机械步下沉、工程锁死"哲学。
13. **工具速查表 REGISTRY（生成式）**（`registry/REGISTRY.md` + `scripts/gen_registry.py`）：prompt 越来越多，全量读又慢又耗 token。给每个 prompt 的 frontmatter 加 `stage`/`when`/`reads`/`writes` 路由字段（单一真相源），由脚本扫描生成一张速查表。自举时**先读 REGISTRY 选定 prompt、再读那一份全文**，不全量读。registry 是生成产物、勿手改（与 hub/能力表同属"生成视图"哲学）。

---

## 二、变更历史（newest-first）

### 2026-06-23 · 工具速查表 REGISTRY + dev_log 拆分
- 新增 `scripts/gen_registry.py` + `registry/REGISTRY.md`：由各 prompt frontmatter 新增的 `stage`/`when`/`reads`/`writes` 字段生成工具速查表（14 prompts + 2 scripts）；自举改为"先读表→再读选定 prompt 全文"，治"全量读 prompt 又慢又耗 token"。
- **设计要点从 README 迁入本 `dev_log.md`**（README 太长不适合放设计/历史），README 改为指针。
- **`todo.md` 并入本文件**「二、变更历史」，以后改进历史统一进 dev_log。

### 2026-06-23 · 完整审计 + 落地修复（#1 / #2+#6 / #3 / #4 / #5 / #7）
对项目做完整审计，按结论逐条落地：
- [x] **#1 QA 取号下沉机械层**：`qa_archive.py` 加 `new` 子命令——原子扫描 `QA_*.md` 取最大+1、`O_CREAT|O_EXCL` 建骨架（**绝不覆盖**），堵死"LLM 数错号→覆盖旧 QA"这个 verify 也抓不到、不可恢复的失败。已测：squat 占位号 → new 跳到下一号、旧文件保全。
- [x] **#2+#6 个人背景结构化为 SQLite**：新增 `scripts/background.py` + `background_db.md`。`topics`（topic 主键）+ `s_have`（按领域 key、FK→topic）+ `changelog`；个人基线单独 `baseline.yaml`。差集 `have-query` 只读相关领域（治 #2）；回填 `have-add` 按 `(domain,id)` 幂等（治 #6）。能力现状表/hub 退为生成视图，根除"以台账为准"人肉纪律。改 7 个 prompt + README + `.gitignore`。已测：幂等 upsert、FK 拒绝悬空、render/board/validate。
- [x] **#3 决策流程图**：README 加「现在该跑哪个 prompt」按场景切的流程图，覆盖 v1 / 模式 A·B / 预习组等可选分支。
- [x] **#4 v1 生成态**：状态机加 `draft_textbook`（源单一可直读则跳过），给主教材 v1 一个名分。
- [x] **#5 命名修正**：`topics.source` 显式记 topic↔主材料映射；归档类 `{topic}_*` / 随文类 `{source}_*`，不再假装"统一前缀"。
- [x] **迁移**：旧 `PERSONAL_BACKGROUND.md` → DB（3 topics + 17 s_have），写 `baseline.yaml`、生成「能力现状表」视图；旧 md 留存为备份；`$PERSONAL_BACKGROUND` 本就指向 `background/` 目录、无需改。
- [~] **#7 清理 `settings.local.json`**：harness 禁止 Claude 改自己的权限文件；已给出清理后的最小安全白名单，待作者手动落。

### 2026-06-13 · 流程演进 + 完整性审计
- [x] **两段分离（预习组 / 主材料组）固化**：预习内容是跨领域基础底子、非完整 topic，故"预习教材+预习QA"自成一组（`{topic}_预习_*`），与"主材料+主QA"组（`{topic}_*`）全程不并归档，分别回填能力画像（预习组→基础底子、主组→topic 专属）。改 `prereq_to_textbook` / `qa_note` / `background_update` / `README` / `topic_hub`。
- [x] **新增主教材生成路 `source_to_textbook.md`**：收料 → 结构化主教材 v1（阅读底本 + QA 融合底本），与预习路对称、共用 `to_tex`；可选（按源类型：密集/分散源才生成）。
- [x] **`note_to_textbook` 重框为两种模式**：A 从 QA 从零建（QA 优先路）/ B 把 QA 融合回生成教材 v1 → v2（教材优先路）。三编辑层对称：预习路 / 主教材生成路 / 成稿融合路。
- [x] **审计修复 — 预习路缺融合步**：模式 B 原本只绑主教材；已推广到"任一生成教材 + 其对应组 QA"，预习教材即预习组 v1，可对称融合成预习 v2。预习路与主路结构现已完全对称。
- [x] **三个通用项补齐（不破坏通用性）**：`qa_to_archive`（按组各跑、不跨组合并）/ `to_review_cards`（分组各出卡、来源列标组）/ `background_update §2`（取料覆盖两组教材+QA）——均以"分组可选适用 + 单组行为不变"措辞，保持通用。
- [x] **Bootstrap 校验**：14 个 prompt/脚本 README 全覆盖；新领域→DAG→差集→预备材料→QA融合→主教材+收料→QA融合，端到端贯通。

### 2026-06-13 · 背景按变动频率拆两份
- [x] 可能需要为工作区单独指定背景（Codex 把工作区背景直接写进了个人背景）。解决：背景拆两份——稳定档案（稳定信息+知识资产台账+变更记录）+ 同目录 `WORK_LOG.md` 动态日志（周进度/切入点）。工作进度回填改写 `WORK_LOG.md`，不再污染个人背景。（注：2026-06-23 此结构进一步升级为 `baseline.yaml` + `background.db` + `WORK_LOG.md`，见上方。）
