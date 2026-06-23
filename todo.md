- [x] 可能需要为工作区单独指定背景，Codex将工作区背景直接写进了个人背景
  - 解决（2026-06-13）：背景按变动频率拆两份——`$PERSONAL_BACKGROUND` 稳定档案（稳定信息+知识资产台账+变更记录）+ 同目录 `WORK_LOG.md` 动态日志（周进度/切入点）。`background_update.md` 工作进度回填改写 `WORK_LOG.md`，不再污染个人背景；读 `S_have` 的 prompt 仍只读 `$PERSONAL_BACKGROUND`。

## 2026-06-13 流程演进 + 完整性审计（变更留痕）

- [x] **两段分离（预习组 / 主材料组）固化**：预习内容是跨领域基础底子、非完整 topic，故"预习教材+预习QA"自成一组（`{topic}_预习_*`），与"主材料+主QA"组（`{topic}_*`）全程不并归档，分别回填能力画像（预习组→基础底子、主组→topic 专属）。改 `prereq_to_textbook` / `qa_note` / `background_update` / `README` / `topic_hub`。
- [x] **新增主教材生成路 `source_to_textbook.md`**：收料 → 结构化主教材 v1（阅读底本 + QA 融合底本），与预习路对称、共用 `to_tex`；可选（按源类型：密集/分散源才生成）。
- [x] **`note_to_textbook` 重框为两种模式**：A 从 QA 从零建（QA 优先路）/ B 把 QA 融合回生成教材 v1 → v2（教材优先路）。三编辑层对称：预习路 / 主教材生成路 / 成稿融合路。
- [x] **审计修复 — 预习路缺融合步**：模式 B 原本只绑主教材；已推广到"任一生成教材 + 其对应组 QA"，预习教材即预习组 v1，可对称融合成预习 v2。预习路与主路结构现已完全对称。
- [x] **三个通用项补齐（不破坏通用性）**：`qa_to_archive`（按组各跑、不跨组合并）/ `to_review_cards`（分组各出卡、来源列标组）/ `background_update §2`（取料覆盖两组教材+QA）——均以"分组可选适用 + 单组行为不变"措辞，保持通用。
- [x] **Bootstrap 校验**：14 个 prompt/脚本 README 全覆盖；新领域→DAG→差集→预备材料→QA融合→主教材+收料→QA融合，端到端贯通。

## 2026-06-23 完整审计 + 落地修复（#1 / #2+#6 / #3 / #4 / #5 / #7）

对项目做完整审计，按结论逐条落地：

- [x] **#1 QA 取号下沉机械层**：`qa_archive.py` 加 `new` 子命令——原子扫描 `QA_*.md` 取最大+1、`O_CREAT|O_EXCL` 建骨架（**绝不覆盖**），堵死"LLM 数错号→覆盖旧 QA"这个 verify 也抓不到、不可恢复的失败。改 `qa_note`/README。已测：squat 占位号 → new 跳到下一号、旧文件保全。
- [x] **#2+#6 个人背景结构化为 SQLite**：新增 `scripts/background.py`（机械层）+ `background_db.md`（契约）。`topics`（topic 主键，唯一真相源）+ `s_have`（按领域 key、FK→topic）+ `changelog`；个人基线单独 `baseline.yaml`。差集 `have-query` 只读相关领域（治 #2 全量重读）；回填 `have-add` 按 `(domain,id)` 幂等（治 #6 双入口重复）。能力现状表/hub 退为生成视图（`have-table`/`topic-render`），根除"以台账为准"人肉纪律。改 `prereq_and_objectives`/`background_update`/`weekly_review`/`topic_map`/`source_selection`/`examples`/README/`.gitignore`。已测：幂等 upsert（3 写 1 行、首次 added 保留）、FK 拒绝悬空 topic、shaky 标注、render/board/validate。
- [x] **#3 决策流程图**：README 加「现在该跑哪个 prompt」按场景切的流程图，覆盖 v1 / 模式 A·B / 预习组等可选分支。
- [x] **#4 v1 生成态**：状态机加 `draft_textbook`（源单一可直读则跳过），给 `source_to_textbook` 的主教材 v1 一个名分；消除"reading 态下已有 .tex"的别扭。
- [x] **#5 命名修正**：`topics.source` 字段显式记 topic↔主材料映射；归档类用 `{topic}_*`、随文类用 `{source}_*`，不再假装"统一前缀"（source≠topic 时旧约定自相矛盾）。
- [~] **#7 清理 settings.local.json**：harness 禁止 Claude 改自己的权限文件；已给出清理后的最小安全白名单，待作者手动落。
- [ ] **迁移（待作者执行）**：旧 `PERSONAL_BACKGROUND.md` → DB 需一次性 LLM 语义转换（见 `background_db.md §7`），并把 `$PERSONAL_BACKGROUND` 重指向 `background/` 目录、跑 `background.py init`。