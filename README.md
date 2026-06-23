# 学习工作流总览

> 这组 prompt 把"从一个领域，到能讲清/能用的个性化知识资产"拆成两套工作流（宏观拆分 + 单主题深读）、一个时间驱动的背景同步入口，外加一类被流程步骤调用的工具 prompt、一份结构化背景契约（`background_db.md`）和两个机械层脚本（QA 保真 `qa_archive.py` + 背景结构化 `background.py`）。
> 每份 prompt 是手动调用的上下文规范（非 Claude Code skill）。下面是它们如何衔接。

---

## 使用方式（工具仓库 / workspace 分离 / 自举）

**本仓库是「学习笔记 pipeline」工具，不存放任何个人学习内容。** 你的学习材料、笔记、产物（QA 文件、归档、教科书 `.tex`、复习卡、个人背景台账…）放在**单独的 workspace 目录**（建议自建私有仓库），与本仓库分离——这样 pipeline 可独立 `git pull` 更新而不与你的笔记冲突，个人/隐私内容也不会进公开仓库。

### 两个环境变量（位置无关地连接 pipeline 与 workspace）
| 变量 | 指向 | 谁维护 |
|---|---|---|
| `$LEARNING_PIPELINE` | 本仓库的 clone 路径 | 跟随 clone 位置 |
| `$PERSONAL_BACKGROUND` | 你的个人背景 **`background/` 目录**（住在 workspace：`baseline.yaml` 基线 + `background.db` 结构化台账 + `WORK_LOG.md` 流水账） | `background.py` 读写（`background_update.md`/`weekly_review.md` 写 S_have、推进 topic 状态） |

> **背景三层存储**（住在 `$PERSONAL_BACKGROUND` 目录，详见 `background_db.md`）：① **`baseline.yaml`**——身份/出身/入职基线锚点，低频手编；② **`background.db`**（SQLite）——`topics` 表（topic 主键 + 状态机，是 obsidian hub 的真相源）+ `s_have` 表（按领域 key 的知识资产台账，差集相减的集合），由 `background.py` 读写/校验/渲染；③ **`WORK_LOG.md`**——周进度/切入点等动态流水账，不进差集。差集用 `have-query` 按领域取，回填用 `have-add` 幂等写（主题/周复盘两入口不双计）。

Windows（PowerShell，设为用户级持久变量）：
```powershell
[Environment]::SetEnvironmentVariable("LEARNING_PIPELINE",   "C:\path\to\learning-pipeline",        "User")
[Environment]::SetEnvironmentVariable("PERSONAL_BACKGROUND", "C:\path\to\your-workspace\background", "User")
# $PERSONAL_BACKGROUND 现在指向 background/ 目录（内含 baseline.yaml + background.db + WORK_LOG.md）
# 首次建库： python $env:LEARNING_PIPELINE\scripts\background.py init
```

### 路径约定
本 README 与各 prompt 内提到的 `scripts/...`、`tool_prompts/...`、各 `*.md`，**路径一律相对 `$LEARNING_PIPELINE`**。需要在 shell 里实际敲的脚本命令用环境变量写全，例如：
```powershell
python $env:LEARNING_PIPELINE\scripts\qa_archive.py finalize <workspace>\{source}_qa
```

### 自举（让 LLM 启动任务）
在你的 workspace 里打开 Claude Code，告诉它：「读 `$LEARNING_PIPELINE/README.md`，然后我们开始 X」。
> **省 token 的关键**：要跑某一步时，**先读 `$LEARNING_PIPELINE/registry/REGISTRY.md`（工具速查表）**，按「何时用」选定那一个 prompt，**再读它的全文**——不要全量读所有 prompt。
可在 workspace 根放一个一行 `CLAUDE.md` 自举（样例见 `examples/workspace_CLAUDE.md`）：
> 本目录是学习 workspace；pipeline 在 `$LEARNING_PIPELINE`，动手前先读它的 `README.md`。

---

## 工作流 A：宏观拆分（独立）
- **`topic_map.md`** — 领域/目标 → 子主题 DAG（依赖图 + ROI + 每节点带 `source_hint`/`align`，用 `background.py topic-upsert` 写进 `topics` 表）。周/日计划只是从这张图切片。

## 工作流 B：单主题深读（按认知顺序的闭环）

```
source_selection.md        收料：theme(+source_hint) → 确定的、范围可控的资料清单  status: collect
        │                  （服务 objective+按 align 降级取材+范围裁剪，对抗通读）
prereq_and_objectives.md   读前：从资料清单抽 S_need → 前置知识(差集)+阅读目标问题  status: prereq
  └ 预习路 prereq_to_textbook.md → to_tex.md：差集→预习教材 v1；再 qa_note→预习QA→note_to_textbook模式B 融合成预习 v2
                               （预习组 {topic}_预习_* 与主材料组 {topic}_* 全程分离、各自归档，分别喂能力画像；结构与主路对称）
  └ 主教材生成路 source_to_textbook.md → to_tex.md：收料 → 结构化主教材 v1（阅读底本；可选，密集/分散源才生成）  status: draft_textbook
        │
qa_note.md                 随文：读主教材 v1（或收料）边读边 QA，落单文件到 {source}_qa/  status: reading
        │                  （front-matter：id/hash 机器管，导航字段 LLM 写）
qa_to_archive.md           归档：LLM 出编排表 → 脚本 assemble 保真拼接  status: archive
        │                  （机械搬运交脚本：哈希/计数/id 守恒，零改字）
note_to_textbook.md        成稿：模式A 从QA建教材 / 模式B 把QA融合回主教材v1→v2（同文件演进）  status: textbook
  └ 调用渲染层 tool_prompts/to_tex.md（教科书味+排版/编译，见下方「工具 prompt」）
        │
to_review_cards.md         回路：QA/误区框/目标问题 → 复习卡     status: review
        │                  （主动提取+间隔重复，对抗流畅性幻觉）
background_update.md        闭环：新增能力→have-add 写 s_have 表（按领域，幂等）  status: done
        │                  （幂等回填，喂养下次 prereq 差集；两入口不双计）
topic_hub.md               枢纽：{topic}_hub.md 由 background.py topic-render 从 topics 表生成（视图，勿手改）；board 出总览看板
```

> **闭环依赖**：`prereq_and_objectives.md` 的差集用 `background.py have-query` 读 `s_have` 表（按领域）；
> `background_update.md` 在每个主题收尾时 `have-add` 把新增 `S_have` 幂等写回。
> 主题做得越多，台账越厚、领域越全，下一轮读前差集越精准——这是整套流程唯一的反馈环。

## 决策：现在该跑哪个 prompt（按场景切）

```
新领域要规划？        → topic_map.md（拆 DAG，topic-upsert 建节点）
有 theme、材料待定？   → source_selection.md（收料、定 --source、status collect→prereq）
有确定材料、要读？     → prereq_and_objectives.md（差集 have-query + 3–5 目标问题）
  ├ 缺跨域基础底子？   → 预习路：prereq_to_textbook → qa_note(预习组 {topic}_预习_*) →（可选）模式B 融合预习 v2
  └ 主材料怎么读？
      ├ 密集/分散源    → 教材优先：source_to_textbook(v1, draft_textbook) → qa_note 读 v1 → note_to_textbook 模式B 融合 v2
      └ 单一可直读源    → QA 优先：qa_note 直接对收料 → note_to_textbook 模式A 从 QA 从零建
随文 QA 攒够了？       → qa_to_archive.md（LLM 编排表 + 脚本 assemble 保真拼接）
教材成稿了？          → to_review_cards.md（复习卡）→ background_update.md（have-add 回填 + topic-status done）
过了一周想沉淀？       → weekly_review.md（工作叙事 → WORK_LOG + have-add）
```
> 每步顺手 `background.py topic-status {topic} <态>` 推进；状态机/命名/CLI 见 `topic_hub.md`、`background_db.md`。

## 时间驱动的背景同步（与工作流 A/B 并行的入口）
- **`weekly_review.md`** — **周/里程碑复盘回填**入口：把一段时间的**原始工作叙事**（做了什么/卡在哪/学到什么/结论）分流——详细流水账写 `WORK_LOG.md`，真正内化的能力用 `background.py have-add` 幂等写进 `s_have` 表（`--source weekly`）。与 `background_update.md` **互补**：后者是**主题驱动**（深读主题收尾，输入是教科书/复习卡/目标问题），本入口是**时间驱动**（输入是工作叙事）；**两入口共写同一表、幂等不双计**；字段/CLI 见 `background_db.md`，语义规则复用 `background_update.md`。

## 工具 prompt（被流程步骤调用的可复用规范）
> 与工作流 A/B 的**阶段** prompt 不同：工具 prompt 不是认知顺序上的一步，而是被某个步骤**调用**的可复用规范，单独成份便于复用与维护。
- **`tool_prompts/to_tex.md`** — **通用渲染层**：把一份**已组织好的中文内容**渲染成可编译、有教科书味的 `.tex`，**来源无关**。拥有 ctexbook + XeLaTeX 完整预导言、固定 TikZ 样式、画图避坑、编译自检，以及统一的「教科书味」写作标准（§6）。
  - **三个消费者（编辑层）**：`prereq_to_textbook.md`（预习路：差集→预习教材）、`source_to_textbook.md`（主教材生成路：收料→v1）、`note_to_textbook.md`（成稿/融合路：QA→融合进 v1→v2）都调用它来渲染。编辑层只管"把某类素材组织成内容"，渲染与教科书味全交给本工具。

## 脚本（机械层 / 保真）
> 纯机械、可 100% 复现、不需要语言理解的步骤从 LLM 算子里**下沉到脚本**，由文件系统 + 哈希锁死 LLM 最危险的失败模式（篡改原文）；LLM 只保留"理解与编排决策"。
- **`scripts/qa_archive.py`** — QA 归档的搬运/校验层：`new`（原子分配下一个 QA id + 建骨架，`O_CREAT|O_EXCL` 绝不覆盖，把"取号/建文件"也锁进脚本）、`finalize`（对正文区写 `content_hash`、置 `status: final`）、`verify`（重哈希比对 + id 一致/唯一性）、`assemble`（按 LLM 编排表字节级拼接 `{topic}_原文素材归档.md` + 计数/守恒/唯一性校验）。被 `qa_note.md`（new + finalize）与 `qa_to_archive.md`（assemble）调用。
- **`scripts/background.py`** — 个人背景的结构化机械层（SQLite：`topics` 主键 + `s_have` 按领域 FK→topic + `changelog`），契约见 **`background_db.md`**。`have-query`（差集只读相关领域，治全量重读）、`have-add`（按 `(domain,id)` 幂等去重，治主题/周复盘双入口重复计入）、`topic-upsert`/`topic-status`（topic 唯一真相源）、`topic-render`/`board`/`have-table`（生成 obsidian hub / 看板 / 能力表**视图**）、`validate`（FK/枚举/JSON 自检）。被 `prereq_and_objectives.md`（读 S_have）/`background_update.md`·`weekly_review.md`（写台账+推进 status）/`topic_map.md`（建 topic）/`topic_hub.md`（渲染 hub）调用。
- **`scripts/gen_registry.py`** — 由各 prompt frontmatter（`stage`/`when`/`reads`/`writes`）生成工具速查表 **`registry/REGISTRY.md`**（自举先读它选 prompt、再读全文，治"全量读又慢又耗 token"）。改 frontmatter 或新增 prompt 后重跑。

## 设计要点 / 变更历史 → 见 `dev_log.md`

> 为保持 README 精简，**设计要点（为什么这么设计）**与**历次改进 / 审计留痕**都迁到 **`dev_log.md`**；
> 工具速查表见 **`registry/REGISTRY.md`**（由 `scripts/gen_registry.py` 从各 prompt frontmatter 生成）。
