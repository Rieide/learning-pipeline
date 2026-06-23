#!/usr/bin/env python3
"""qa_archive.py — 机械搬运 / 校验层：把 LLM 的"编排决策"执行成字节级保真的归档。

把"机械搬运"从 LLM 算子里彻底切除：LLM 只输出"去哪、排第几、丢不丢"的决策(编排表)，
正文的搬运与一切保真校验都由本脚本 + 文件系统完成——不需要语言理解，可 100% 复现。

子命令
  new       原子分配下一个 QA id（最大+1）并创建骨架文件；O_CREAT|O_EXCL 绝不覆盖已存在文件
  finalize  对 QA 文件夹里每个 .md 计算 body 哈希，写入 content_hash + status: final（幂等）
  verify    重哈希比对 + id==文件名 + id 唯一性；任一失败非零退出
  assemble  按编排表(YAML) 拼接 {topic}_原文素材归档.md，并做计数守恒/唯一性/哈希校验

设计铁律（与 qa_note.md / qa_to_archive.md 对应）
  - content_hash 是保真字段：只有本脚本(finalize)能写；LLM 只读、禁改。
  - content_hash 只覆盖 body 区(front-matter 之后)，对 body 做确定性归一(换行→LF + 整体 strip)后哈希，
    因此 LLM 改 front-matter 的导航字段不会破坏保真链。
  - id == 文件名主体；id 唯一性由文件系统(文件名不可重复)天然保证，verify 复核 id 字段与文件名一致。
  - id 的"取号+建文件"也下沉到本脚本(new)：O_CREAT|O_EXCL 原子占位，杜绝 LLM 数错号覆盖旧 QA
    （那是 verify 抓不到、不可恢复的失败）；LLM 不再手动取号/拼文件名。
  - assemble 的正文一律按 ID 从源文件取、字节级复制；LLM 全程不碰 body。

用法示例
  python qa_archive.py new       SIMPL/SIMPL_qa            # 原子分配下一个 id 并建骨架
  python qa_archive.py finalize  SIMPL/SIMPL_qa
  python qa_archive.py verify    SIMPL/SIMPL_qa
  python qa_archive.py assemble  SIMPL/SIMPL_qa --plan SIMPL/SIMPL_arrangement.yaml \\
                                 --out SIMPL/SIMPL_原文素材归档.md
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from collections import defaultdict
from pathlib import Path


# ---------- front-matter 解析（零依赖：finalize/verify 这条保真关键路径不依赖 pyyaml）----------

def split_frontmatter(text: str):
    """返回 (fm_lines: list[str], body: str)。text 已用 \\n 换行。"""
    if not text.startswith("---"):
        raise ValueError("缺少 YAML front-matter（文件须以 '---' 开头）")
    lines = text.split("\n")
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise ValueError("front-matter 未闭合（找不到第二个 '---'）")
    return lines[1:end], "\n".join(lines[end + 1:])


def fm_get(fm_lines, key):
    for ln in fm_lines:
        s = ln.lstrip()
        if s.startswith(key + ":"):
            return s[len(key) + 1:].strip()
    return None


def fm_set(fm_lines, key, value):
    """就地更新某标量字段；不存在则追加。只动这一行，其余字节不变。"""
    for i, ln in enumerate(fm_lines):
        s = ln.lstrip()
        if s.startswith(key + ":"):
            indent = ln[: len(ln) - len(s)]
            fm_lines[i] = f"{indent}{key}: {value}"
            return
    fm_lines.append(f"{key}: {value}")


# ---------- 哈希 ----------

def normalize_body(body: str) -> str:
    """确定性归一：换行统一 LF + 整体去首尾空白。消除编辑器/CRLF 造成的假阳性。"""
    return body.replace("\r\n", "\n").replace("\r", "\n").strip()


def body_hash(body: str) -> str:
    return "sha256:" + hashlib.sha256(normalize_body(body).encode("utf-8")).hexdigest()


# ---------- 文件 IO（写盘强制 LF，避免 Windows 把 \n 翻成 \r\n）----------

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def qa_files(folder: Path):
    return sorted(p for p in folder.glob("*.md") if p.is_file())


# ---------- new：原子分配下一个 QA id 并创建骨架（绝不覆盖）----------

_QA_NUM = re.compile(r"QA_(\d+)$")

_SKELETON = """\
---
# ── 机器验证字段（脚本写/验，LLM 只读，禁改）──
id: {id}
content_hash:
source: {source}
status: draft
# ── 导航字段（LLM 写）──
title:
summary:
questions: []
chapter_hint:
related: []
---
## Q

## A
"""


def _next_qa_index(folder: Path) -> int:
    mx = 0
    for p in folder.glob("QA_*.md"):
        m = _QA_NUM.match(p.stem)
        if m:
            mx = max(mx, int(m.group(1)))
    return mx + 1


def cmd_new(folder: Path, source: str | None = None, count: int = 1) -> int:
    """原子分配下一个（或多个）QA id 并落骨架文件。

    取号(最大+1) + 建文件这一纯机械步从 LLM 下沉到此：用 O_CREAT|O_EXCL 创建，
    若目标名已存在则跳到下一号，绝不覆盖——堵死"LLM 数错号→覆盖旧 QA"这个 verify
    也抓不到、不可恢复的失败模式。LLM 只需把 Q/A 填进脚本生成的文件，再 finalize。
    """
    folder.mkdir(parents=True, exist_ok=True)
    if not source:
        name = folder.name
        source = name[:-3] if name.endswith("_qa") else name
    n = _next_qa_index(folder)
    created, guard = [], 0
    while len(created) < count:
        guard += 1
        if guard > count + 10000:
            print("  ✗ 连续分配失败（目录状态异常？）", file=sys.stderr)
            return 1
        qid = f"QA_{n:04d}"
        path = folder / f"{qid}.md"
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            n += 1            # 该号已被占用 → 跳过，绝不覆盖
            continue
        os.close(fd)          # O_EXCL 已原子占位；正文用 write_text 强制 LF 写入
        write_text(path, _SKELETON.format(id=qid, source=source))
        created.append(qid)
        n += 1
    for qid in created:
        print(f"  ✓ 预留 {qid} → {folder / (qid + '.md')}")
    print(f"[new] 原子分配 {len(created)} 个 id（O_EXCL，绝不覆盖已存在文件）｜source={source}")
    print("      下一步：把 Q/A 原文填进新文件的 ## Q / ## A，再跑 finalize 锁正文。")
    return 0


# ---------- finalize ----------

def cmd_finalize(folder: Path, force: bool = False) -> int:
    files = qa_files(folder)
    if not files:
        print(f"[finalize] {folder} 下没有 .md QA 文件")
        return 1
    changed = problems = 0
    for path in files:
        stem = path.stem
        try:
            fm, body = split_frontmatter(read_text(path))
        except ValueError as e:
            print(f"  ✗ {stem}: {e}")
            problems += 1
            continue
        cur_id = fm_get(fm, "id")
        if cur_id in (None, ""):
            fm_set(fm, "id", stem)
            cur_id = stem
        if cur_id != stem:
            print(f"  ✗ {stem}: id 字段({cur_id}) 与文件名不一致（id 必须等于文件名主体）")
            problems += 1
            continue
        h = body_hash(body)
        stored = fm_get(fm, "content_hash")
        status = fm_get(fm, "status")
        if status == "final" and stored:
            if stored == h:
                continue  # 已定稿且未变，幂等跳过
            if not force:
                print(f"  ✗ {stem}: 已 final 但正文哈希漂移——正文被改过。"
                      f"若确属有意修订，用 --force 重新定稿。")
                problems += 1
                continue
        fm_set(fm, "content_hash", h)
        fm_set(fm, "status", "final")
        write_text(path, "---\n" + "\n".join(fm) + "\n---\n" + body)
        changed += 1
        print(f"  ✓ {stem}: 定稿 {h[:16]}…")
    print(f"[finalize] 定稿 {changed}｜问题 {problems}｜共 {len(files)}")
    return 1 if problems else 0


# ---------- verify ----------

def cmd_verify(folder: Path, quiet: bool = False) -> int:
    files = qa_files(folder)
    if not files:
        print(f"[verify] {folder} 下没有 .md QA 文件")
        return 1
    problems = []
    ids = defaultdict(list)
    for path in files:
        stem = path.stem
        try:
            fm, body = split_frontmatter(read_text(path))
        except ValueError as e:
            problems.append(f"{stem}: {e}")
            continue
        cur_id = fm_get(fm, "id")
        if cur_id != stem:
            problems.append(f"{stem}: id 字段({cur_id}) ≠ 文件名")
        ids[cur_id].append(stem)
        stored = fm_get(fm, "content_hash")
        status = fm_get(fm, "status")
        if status != "final" or not stored:
            problems.append(f"{stem}: 未 finalize（先跑 finalize）")
            continue
        if body_hash(body) != stored:
            problems.append(f"{stem}: 哈希漂移——正文被改过且未重新定稿")
    for i, owners in ids.items():
        if len(owners) > 1:
            problems.append(f"id 重复 {i}: {owners}")
    if problems:
        print(f"[verify] ✗ 发现 {len(problems)} 个问题：")
        for p in problems:
            print(f"  - {p}")
        return 1
    if not quiet:
        print(f"[verify] ✓ {len(files)} 个 QA 全部通过（哈希/ id 一致/唯一）")
    return 0


# ---------- assemble ----------

def cmd_assemble(folder: Path, plan_path: Path, out_path: Path) -> int:
    try:
        import yaml  # 仅 assemble 需要；保真关键路径(finalize/verify)不依赖它
    except ImportError:
        print("assemble 需要 pyyaml：pip install pyyaml", file=sys.stderr)
        return 2

    if cmd_verify(folder, quiet=True) != 0:
        print("[assemble] 中止：QA 文件夹未通过 verify，先修干净再拼接。")
        cmd_verify(folder)
        return 1

    plan = yaml.safe_load(read_text(plan_path))
    topic = plan.get("topic", "")
    note = plan.get("note")
    outline = plan.get("outline") or []
    placement = plan.get("placement") or []

    folder_ids = {p.stem for p in qa_files(folder)}
    head_ids = {h["id"] for h in outline}
    errors = []

    seen, dropped = set(), set()
    by_head = defaultdict(list)
    for e in placement:
        qa = e.get("qa")
        if qa not in folder_ids:
            errors.append(f"编排表引用了不存在的 QA: {qa}")
            continue
        if e.get("drop"):
            dropped.add(qa)
            continue
        if qa in seen:
            errors.append(f"QA 被重复归位: {qa}")
            continue
        under = e.get("under")
        if under not in head_ids:
            errors.append(f"{qa} 的 under({under}) 不在 outline 标题里")
            continue
        seen.add(qa)
        by_head[under].append(e)

    orphans = folder_ids - seen - dropped
    if orphans:
        errors.append(f"有 QA 未被编排(既没归位也没标 drop): {sorted(orphans)}")

    if errors:
        print(f"[assemble] ✗ 编排表有 {len(errors)} 个问题：")
        for e in errors:
            print(f"  - {e}")
        return 1

    assert len(seen) + len(dropped) == len(folder_ids), "计数守恒断言失败（内部错误）"

    out = []
    if note:
        out.append(f"> {note}\n")
    for h in outline:
        out.append("#" * int(h.get("level", 1)) + " " + h["title"])
        out.append("")
        for e in sorted(by_head.get(h["id"], []), key=lambda x: x.get("order", 0)):
            qa = e["qa"]
            fm, body = split_frontmatter(read_text(folder / f"{qa}.md"))
            out.append(f"<!-- {qa} {fm_get(fm, 'content_hash')} -->")
            out.append(normalize_body(body))
            out.append("")
    write_text(out_path, "\n".join(out).rstrip() + "\n")

    print(f"[assemble] ✓ {out_path}")
    print(f"  topic={topic}｜总 QA {len(folder_ids)}｜归位 {len(seen)}｜"
          f"去重丢弃 {len(dropped)}｜守恒 OK｜正文字节级来自源文件")
    return 0


# ---------- CLI ----------

def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows 控制台默认 GBK，强制 UTF-8 以打印 ✓/中文
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(description="QA 归档的机械搬运/校验层（保真，零幻觉）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new", help="原子分配下一个 QA id 并创建骨架文件（O_EXCL，绝不覆盖）")
    p.add_argument("folder", type=Path)
    p.add_argument("--source", default=None, help="source 字段；默认由文件夹名去 _qa 推断")
    p.add_argument("--count", type=int, default=1, help="一次分配多个连续 id（默认 1）")

    p = sub.add_parser("finalize", help="计算并写入 content_hash + status:final（幂等）")
    p.add_argument("folder", type=Path)
    p.add_argument("--force", action="store_true", help="对已 final 但正文改过的文件重新定稿")

    p = sub.add_parser("verify", help="重哈希比对 + id 一致/唯一性校验")
    p.add_argument("folder", type=Path)

    p = sub.add_parser("assemble", help="按编排表拼接归档文档并校验守恒")
    p.add_argument("folder", type=Path)
    p.add_argument("--plan", type=Path, required=True, help="LLM 产出的编排表(YAML)")
    p.add_argument("--out", type=Path, required=True, help="输出的 {topic}_原文素材归档.md")

    args = ap.parse_args(argv)
    if args.cmd == "new":
        return cmd_new(args.folder, args.source, args.count)
    if args.cmd == "finalize":
        return cmd_finalize(args.folder, args.force)
    if args.cmd == "verify":
        return cmd_verify(args.folder)
    if args.cmd == "assemble":
        return cmd_assemble(args.folder, args.plan, args.out)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
