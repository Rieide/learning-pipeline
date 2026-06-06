# 学习工作流总览

> 这组 prompt 把"从一个领域，到能讲清/能用的个性化知识资产"拆成两套工作流，外加一类被流程步骤调用的工具 prompt 和一个机械层脚本。
> 每份 prompt 是手动调用的上下文规范（非 Claude Code skill）。下面是它们如何衔接。

---

## 使用方式（工具仓库 / workspace 分离 / 自举）

**本仓库是「学习笔记 pipeline」工具，不存放任何个人学习内容。** 你的学习材料、笔记、产物（QA 文件、归档、教科书 `.tex`、复习卡、个人背景台账…）放在**单独的 workspace 目录**（建议自建私有仓库），与本仓库分离——这样 pipeline 可独立 `git pull` 更新而不与你的笔记冲突，个人/隐私内容也不会进公开仓库。

### 两个环境变量（位置无关地连接 pipeline 与 workspace）
| 变量 | 指向 | 谁维护 |
|---|---|---|
| `$LEARNING_PIPELINE` | 本仓库的 clone 路径 | 跟随 clone 位置 |
| `$PERSONAL_BACKGROUND` | 你的个人背景台账文件（住在 workspace） | 你自己（`background_update.md` 写回） |

Windows（PowerShell，设为用户级持久变量）：
```powershell
[Environment]::SetEnvironmentVariable("LEARNING_PIPELINE",   "C:\path\to\learning-pipeline",        "User")
[Environment]::SetEnvironmentVariable("PERSONAL_BACKGROUND", "C:\path\to\your-workspace\个人背景.md", "User")
```

### 路径约定
本 README 与各 prompt 内提到的 `scripts/...`、`tool_prompts/...`、各 `*.md`，**路径一律相对 `$LEARNING_PIPELINE`**。需要在 shell 里实际敲的脚本命令用环境变量写全，例如：
```powershell
python $env:LEARNING_PIPELINE\scripts\qa_archive.py finalize <workspace>\{source}_qa
```

### 自举（让 LLM 启动任务）
在你的 workspace 里打开 Claude Code，告诉它：「读 `$LEARNING_PIPELINE/README.md`，然后我们开始 X」。
可在 workspace 根放一个一行 `CLAUDE.md` 自举（样例见 `examples/workspace_CLAUDE.md`）：
> 本目录是学习 workspace；pipeline 在 `$LEARNING_PIPELINE`，动手前先读它的 `README.md`。

---

## 工作流 A：宏观拆分（独立）
- **`topic_map.md`** — 领域/目标 → 子主题 DAG（依赖图 + ROI + obsidian 占位条目）。周/日计划只是从这张图切片。

## 工作流 B：单主题深读（按认知顺序的闭环）

```
prereq_and_objectives.md   读前：前置知识(差集)+阅读目标问题   status: prereq
  └ 旁支 prereq_to_textbook.md → 渲染层 tool_prompts/to_tex.md：把预习也做成可复习教材
        │
qa_note.md                 随文：每个 QA 落单文件到 {source}_qa/  status: reading
        │                  （front-matter：id/hash 机器管，导航字段 LLM 写）
qa_to_archive.md           归档：LLM 出编排表 → 脚本 assemble 保真拼接  status: archive
        │                  （机械搬运交脚本：哈希/计数/id 守恒，零改字）
note_to_textbook.md        成稿（笔记编辑层）：归档 → 教科书内容  status: textbook
  └ 调用渲染层 tool_prompts/to_tex.md（教科书味+排版/编译，见下方「工具 prompt」）
        │
to_review_cards.md         回路：QA/误区框/目标问题 → 复习卡     status: review
        │                  （主动提取+间隔重复，对抗流畅性幻觉）
background_update.md        闭环：新增能力→背景文件 知识资产台账     status: done
        │                  （追加式 history，喂养下次 prereq 差集）
topic_hub.md               枢纽：obsidian MOC，frontmatter 状态机 + Dataview 看板
```

> **闭环依赖**：`prereq_and_objectives.md` 的差集读**背景文件**（路径由环境变量 `$PERSONAL_BACKGROUND` 指定）的 `S_have`；
> `background_update.md` 在每个主题收尾时把新增 `S_have` 追加回去。
> 主题做得越多，台账越厚，下一轮读前差集越精准——这是整套流程唯一的反馈环。

## 工具 prompt（被流程步骤调用的可复用规范）
> 与工作流 A/B 的**阶段** prompt 不同：工具 prompt 不是认知顺序上的一步，而是被某个步骤**调用**的可复用规范，单独成份便于复用与维护。
- **`tool_prompts/to_tex.md`** — **通用渲染层**：把一份**已组织好的中文内容**渲染成可编译、有教科书味的 `.tex`，**来源无关**。拥有 ctexbook + XeLaTeX 完整预导言、固定 TikZ 样式、画图避坑、编译自检，以及统一的「教科书味」写作标准（§6）。
  - **两个消费者（编辑层）**：`note_to_textbook.md`（笔记这一路）与 `prereq_to_textbook.md`（预习这一路）都调用它来渲染。编辑层只管"把某类素材组织成内容"，渲染与教科书味全交给本工具。

## 脚本（机械层 / 保真）
> 纯机械、可 100% 复现、不需要语言理解的步骤从 LLM 算子里**下沉到脚本**，由文件系统 + 哈希锁死 LLM 最危险的失败模式（篡改原文）；LLM 只保留"理解与编排决策"。
- **`scripts/qa_archive.py`** — QA 归档的搬运/校验层：`finalize`（对正文区写 `content_hash`、置 `status: final`）、`verify`（重哈希比对 + id 一致/唯一性）、`assemble`（按 LLM 编排表字节级拼接 `{topic}_原文素材归档.md` + 计数/守恒/唯一性校验）。被 `qa_note.md`（finalize）与 `qa_to_archive.md`（assemble）调用。

## 设计要点（相对早期流程的改动）
1. **补检索回路**（`to_review_cards.md`）：早期流程只编码不提取，新增复用 QA 的复习卡，几乎零成本。
2. **prereq 升级为 prereq+目标问题**：被动阅读 → 带靶子的主动阅读。
3. **固化归档铁律**（`qa_to_archive.md`）：最易 LLM 漂移、原先无治理的一环，写死"只重排不改字"。
4. **宏观拆分成 DAG**（`topic_map.md`）：周计划退化为切片。
5. **obsidian 枢纽用状态机**（`topic_hub.md`）：多主题并行可视化、可恢复。
6. **阶段式背景回填**（`background_update.md`）：每完成一个主题，追加新增能力到**背景文件**（`$PERSONAL_BACKGROUND`）的知识资产台账，闭合"差集读背景→学完写回背景"的唯一反馈环，下次读前更精准。
7. **编辑层 / 渲染层解耦**（`to_tex.md` 上提为通用渲染层）：把"怎么组织某类素材"（编辑层：`note_to_textbook.md` 笔记路、`prereq_to_textbook.md` 预习路）与"怎么渲染成有教科书味的 .tex"（渲染层：`tool_prompts/to_tex.md`）分开。渲染层只有一份、来源无关，教科书味标准也统一收归于此；新增来源只需加一份薄编辑层，复用同一渲染层。预习路据此从"差集脚手架"长出可选的"预习教材"旁支。
8. **机械搬运下沉脚本 / QA 单文件化**（`qa_note.md` + `qa_to_archive.md` + `scripts/qa_archive.py`）：把"重排归档"从 LLM 的生成式搬运改成"LLM 出编排表、脚本字节级搬运 + 哈希校验"。每个 QA 切成带 front-matter 的独立文件，机器验证字段（`id`/`content_hash`，LLM 只读）与导航字段（`summary`/`questions`…，LLM 可写）严格分离，正文保真。LLM 拿到的是理解与编排能力，工程锁死的是"改原文"这一最危险失败模式。
