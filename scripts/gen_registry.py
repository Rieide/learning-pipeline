#!/usr/bin/env python3
"""gen_registry.py — 由各 prompt 的 frontmatter 生成工具速查表 registry/REGISTRY.md。

单一真相源 = 每个 prompt 的 frontmatter（name/stage/when/reads/writes）。本脚本只读它们，
把"路由元数据"汇成一张表，供 LLM 自举时**先读本表选定要用的 prompt、再读那一份全文**，
避免全量读所有 prompt（慢且耗 token）。registry 是生成产物，勿手改——改 frontmatter 再重跑。

改了任何 prompt 的 frontmatter（或新增 prompt）后重跑：
  python $env:LEARNING_PIPELINE\\scripts\\gen_registry.py
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "registry" / "REGISTRY.md"

# 工作流顺序（决定表内排序）；未列出的新 prompt 排到最后，提示把它补进本列表
ORDER = [
    "topic_map.md", "source_selection.md", "prereq_and_objectives.md",
    "prereq_to_textbook.md", "source_to_textbook.md", "qa_note.md",
    "qa_to_archive.md", "note_to_textbook.md", "to_review_cards.md",
    "background_update.md", "weekly_review.md", "topic_hub.md",
    "background_db.md", "tool_prompts/to_tex.md",
]

FM_RE = re.compile(r"^([A-Za-z_][\w-]*):\s?(.*)$")


def parse_frontmatter(text: str):
    if not text.startswith("---"):
        return None
    lines = text.split("\n")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return None
    fm = {}
    for ln in lines[1:end]:
        m = FM_RE.match(ln)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm


def cell(s: str) -> str:
    return (s or "").replace("|", "\\|").strip()


def collect_prompts():
    rows = []
    md_files = list(ROOT.glob("*.md")) + list((ROOT / "tool_prompts").glob("*.md"))
    for p in md_files:
        fm = parse_frontmatter(p.read_text(encoding="utf-8"))
        if not fm or "stage" not in fm:
            continue   # 非工具文件（README/dev_log/REGISTRY…）无 stage，自动跳过
        rows.append({
            "file": p.relative_to(ROOT).as_posix(),
            "stage": fm.get("stage", ""),
            "when": fm.get("when", ""),
            "reads": fm.get("reads", ""),
            "writes": fm.get("writes", ""),
        })
    rank = {name: i for i, name in enumerate(ORDER)}
    rows.sort(key=lambda r: (rank.get(r["file"], len(ORDER)), r["file"]))
    return rows


def collect_scripts():
    rows = []
    for p in sorted((ROOT / "scripts").glob("*.py")):
        if p.name == Path(__file__).name:
            continue
        try:
            doc = ast.get_docstring(ast.parse(p.read_text(encoding="utf-8"))) or ""
        except SyntaxError:
            doc = ""
        rows.append({"file": f"scripts/{p.name}", "desc": doc.split("\n", 1)[0].strip()})
    return rows


def main() -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows 控制台默认 GBK/cp1252，强制 UTF-8
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    prompts = collect_prompts()
    scripts = collect_scripts()
    out = [
        "# 工具速查表 REGISTRY",
        "",
        "> **本文件由 `scripts/gen_registry.py` 从各 prompt 的 frontmatter 生成，勿手改。**",
        "> 改了 prompt 的 frontmatter 或新增 prompt 后重跑："
        "`python $env:LEARNING_PIPELINE\\scripts\\gen_registry.py`",
        ">",
        "> **自举用法**：进入 workspace 后**先读本表**，按「何时用」选定要跑的 prompt，"
        "**再读那一份的全文**——不要全量读所有 prompt。设计要点 / 变更历史见 `dev_log.md`。",
        "",
        "## Prompt（按工作流顺序）",
        "",
        "| 文件 | stage | 何时用 | 读 → 写 |",
        "|---|---|---|---|",
    ]
    for r in prompts:
        out.append(f"| `{r['file']}` | {cell(r['stage'])} | {cell(r['when'])} | "
                   f"{cell(r['reads'])} → {cell(r['writes'])} |")
    out += ["", "## 脚本（机械层，被上面 prompt 调用）", "",
            "| 脚本 | 一句话 |", "|---|---|"]
    for r in scripts:
        out.append(f"| `{r['file']}` | {cell(r['desc'])} |")
    out.append("")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    print(f"[gen_registry] ✓ {OUT.relative_to(ROOT).as_posix()}："
          f"{len(prompts)} prompts + {len(scripts)} scripts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
