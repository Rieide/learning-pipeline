#!/usr/bin/env python3
"""background.py — 个人背景的结构化机械层（SQLite 单库多表）。

把"差集要读的 S_have 台账"与"topic 状态/元数据"从非结构化 markdown 升级为可查询、
可校验、可渲染的结构化数据：LLM 只做语义判断（这条能力算不算新增、归哪个领域、是否仍存疑），
读写与完整性校验交给本脚本 + SQLite —— 与 qa_archive.py 同一"机械步下沉"哲学。

三层存储（按性质/变动频率分离，不塞进一个库）：
  - baseline.yaml   个人基线（身份/出身/入职基线锚点）：低频、手编、YAML，本脚本不碰。
  - background.db   本脚本管的 SQLite：topics（topic 主键）+ s_have（按领域，FK→topic）+ changelog。
  - WORK_LOG.md     动态流水账（周进度/切入点）：不进差集，本脚本不碰。

obsidian 的 {topic}_hub.md 退化为"由 DB 渲染生成的视图"（topic-render）——DB 是唯一真相源。

子命令
  init           建表（幂等）
  topic-upsert   新增/更新一个 topic（topic 为主键；保留 created，刷新 updated；只覆盖给定字段）
  topic-status   切换 status（校验状态枚举 + 记 changelog）
  topic-list     列出 topics（可按 status 过滤）
  topic-show     显示某 topic 及其 S_have
  topic-render   把某 topic 渲染成 {topic}_hub.md 视图（DB→视图，勿手改视图）
  board          渲染全 topic 进度看板（markdown 表）
  have-add       幂等写入一条 S_have（按 (domain,id) upsert）——根治主题/周复盘双入口重复计入
  have-query     读 S_have（按领域/topic/组/状态过滤）：prereq 差集的 S_have 来源
  have-domains   列出领域 + 计数
  have-table     渲染"能力现状表"（按领域汇总，取代手维护的表）
  validate       校验 FK 完整性 + 枚举值 + 必填

状态枚举（#4 已含 v1 生成态 draft_textbook）：
  planned → collect → prereq → [draft_textbook] → reading → archive → textbook → review → done

DB 路径解析：--db 优先；否则取 $PERSONAL_BACKGROUND/background.db。
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

STATUSES = ["planned", "collect", "prereq", "draft_textbook",
            "reading", "archive", "textbook", "review", "done"]
HAVE_STATUS = ["mastered", "shaky"]
GROUPS = ["main", "prereq"]
SOURCES = ["pipeline", "weekly", "manual"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS topics (
    topic       TEXT PRIMARY KEY,
    status      TEXT NOT NULL DEFAULT 'planned',
    roi         TEXT,
    objective   TEXT,
    align       TEXT,                            -- 与阶段定位的对齐/降级说明（source_selection 取材深度依据）
    deps        TEXT NOT NULL DEFAULT '[]',      -- JSON array of topic names
    source_hint TEXT NOT NULL DEFAULT '[]',      -- JSON array
    tags        TEXT NOT NULL DEFAULT '[]',      -- JSON array
    source      TEXT,                            -- 主材料文件名主体（QA 落 {source}_qa/）；解决 #5
    created     TEXT,
    updated     TEXT,
    note        TEXT
);
CREATE TABLE IF NOT EXISTS s_have (
    domain     TEXT NOT NULL,
    id         TEXT NOT NULL,
    capability TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'mastered', -- mastered|shaky
    topic      TEXT,                             -- FK -> topics.topic（哪个 topic 贡献的）
    grp        TEXT NOT NULL DEFAULT 'main',     -- main|prereq（两段分离）
    source     TEXT NOT NULL DEFAULT 'pipeline', -- pipeline|weekly|manual
    added      TEXT,
    note       TEXT,
    PRIMARY KEY (domain, id),
    FOREIGN KEY (topic) REFERENCES topics(topic)
);
CREATE TABLE IF NOT EXISTS changelog (
    ts   TEXT NOT NULL,
    kind TEXT,            -- topic | status | s_have
    ref  TEXT,            -- topic 名 或 domain/id
    note TEXT
);
"""


# ---------- 基础设施 ----------

def resolve_db(args) -> Path:
    if getattr(args, "db", None):
        return Path(args.db)
    env = os.environ.get("PERSONAL_BACKGROUND")
    if env:
        p = Path(env)
        # $PERSONAL_BACKGROUND 约定为 background/ 目录；兼容直接给 .db
        return p if p.suffix == ".db" else p / "background.db"
    print("缺少 DB 路径：给 --db，或设环境变量 $PERSONAL_BACKGROUND 指向 background/ 目录",
          file=sys.stderr)
    raise SystemExit(2)


def connect(db: Path, create: bool = False) -> sqlite3.Connection:
    if not create and not db.exists():
        print(f"DB 不存在：{db}（先跑 `background.py init --db {db}`）", file=sys.stderr)
        raise SystemExit(2)
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def today(args) -> str:
    return getattr(args, "date", None) or date.today().isoformat()


def jlist(s: str | None):
    if not s:
        return []
    return [x.strip() for x in s.split(",") if x.strip()]


def log(con, kind, ref, note, ts):
    con.execute("INSERT INTO changelog (ts, kind, ref, note) VALUES (?,?,?,?)",
                (ts, kind, ref, note))


# ---------- init ----------

def cmd_init(args) -> int:
    db = resolve_db(args)
    con = connect(db, create=True)
    con.executescript(SCHEMA)
    con.commit()
    print(f"[init] ✓ schema 就绪：{db}")
    return 0


# ---------- topic ----------

def cmd_topic_upsert(args) -> int:
    con = connect(resolve_db(args))
    ts = today(args)
    cur = con.execute("SELECT * FROM topics WHERE topic=?", (args.topic,)).fetchone()
    if args.status and args.status not in STATUSES:
        print(f"✗ 未知 status：{args.status}（合法：{'/'.join(STATUSES)}）", file=sys.stderr)
        return 1
    row = dict(cur) if cur else {}
    merged = {
        "topic": args.topic,
        "status": args.status or row.get("status") or "planned",
        "roi": args.roi if args.roi is not None else row.get("roi"),
        "objective": args.objective if args.objective is not None else row.get("objective"),
        "align": args.align if args.align is not None else row.get("align"),
        "deps": json.dumps(jlist(args.deps), ensure_ascii=False) if args.deps is not None else row.get("deps", "[]"),
        "source_hint": json.dumps(jlist(args.source_hint), ensure_ascii=False) if args.source_hint is not None else row.get("source_hint", "[]"),
        "tags": json.dumps(jlist(args.tags), ensure_ascii=False) if args.tags is not None else row.get("tags", "[]"),
        "source": args.source if args.source is not None else row.get("source"),
        "created": row.get("created") or ts,
        "updated": ts,
        "note": args.note if args.note is not None else row.get("note"),
    }
    con.execute("""
        INSERT OR REPLACE INTO topics
        (topic,status,roi,objective,align,deps,source_hint,tags,source,created,updated,note)
        VALUES (:topic,:status,:roi,:objective,:align,:deps,:source_hint,:tags,:source,:created,:updated,:note)
    """, merged)
    log(con, "topic", args.topic, "upsert" if cur else "create", ts)
    con.commit()
    print(f"[topic-upsert] {'更新' if cur else '新建'} {args.topic}｜status={merged['status']}"
          f"｜roi={merged['roi']}｜source={merged['source']}")
    return 0


def cmd_topic_status(args) -> int:
    if args.status not in STATUSES:
        print(f"✗ 未知 status：{args.status}（合法：{'/'.join(STATUSES)}）", file=sys.stderr)
        return 1
    con = connect(resolve_db(args))
    ts = today(args)
    cur = con.execute("SELECT status FROM topics WHERE topic=?", (args.topic,)).fetchone()
    if not cur:
        print(f"✗ topic 不存在：{args.topic}（先 topic-upsert）", file=sys.stderr)
        return 1
    old = cur["status"]
    con.execute("UPDATE topics SET status=?, updated=? WHERE topic=?", (args.status, ts, args.topic))
    log(con, "status", args.topic, f"{old}→{args.status}", ts)
    con.commit()
    back = STATUSES.index(args.status) < STATUSES.index(old)
    print(f"[topic-status] {args.topic}: {old} → {args.status}" + ("  ⚠️ 状态回退" if back else ""))
    return 0


def _fmt_topic(r) -> str:
    deps = ", ".join(json.loads(r["deps"] or "[]"))
    return (f"{r['topic']:<22} {r['status']:<14} roi={r['roi'] or '-':<5} "
            f"deps=[{deps}] updated={r['updated'] or '-'}")


def cmd_topic_list(args) -> int:
    con = connect(resolve_db(args))
    q = "SELECT * FROM topics"
    params = []
    if args.status:
        q += " WHERE status=?"
        params.append(args.status)
    q += " ORDER BY updated DESC"
    rows = con.execute(q, params).fetchall()
    if not rows:
        print("(无 topic)")
        return 0
    for r in rows:
        print(_fmt_topic(r))
    print(f"\n共 {len(rows)} 个 topic")
    return 0


def cmd_topic_show(args) -> int:
    con = connect(resolve_db(args))
    r = con.execute("SELECT * FROM topics WHERE topic=?", (args.topic,)).fetchone()
    if not r:
        print(f"✗ topic 不存在：{args.topic}", file=sys.stderr)
        return 1
    print(f"# {r['topic']}")
    print(f"status: {r['status']}｜roi: {r['roi']}｜source: {r['source']}｜updated: {r['updated']}")
    print(f"objective: {r['objective']}")
    print(f"align: {r['align']}")
    print(f"deps: {json.loads(r['deps'] or '[]')}｜source_hint: {json.loads(r['source_hint'] or '[]')}")
    have = con.execute("SELECT * FROM s_have WHERE topic=? ORDER BY domain, id", (args.topic,)).fetchall()
    print(f"\n## 贡献的 S_have（{len(have)} 条）")
    for h in have:
        flag = "⚠️shaky" if h["status"] == "shaky" else "mastered"
        print(f"- [{flag}] ({h['domain']}/{h['grp']}) {h['capability']}  ‹id:{h['id']}›")
    return 0


def cmd_topic_render(args) -> int:
    con = connect(resolve_db(args))
    r = con.execute("SELECT * FROM topics WHERE topic=?", (args.topic,)).fetchone()
    if not r:
        print(f"✗ topic 不存在：{args.topic}", file=sys.stderr)
        return 1
    have = con.execute("SELECT * FROM s_have WHERE topic=? ORDER BY grp, domain, id", (args.topic,)).fetchall()
    t = r["topic"]
    src = r["source"] or t
    deps = json.loads(r["deps"] or "[]")
    hint = json.loads(r["source_hint"] or "[]")
    tags = json.loads(r["tags"] or "[]")
    lines = []
    lines.append("---")
    lines.append(f"topic: {t}")
    lines.append(f"status: {r['status']}")
    lines.append(f"roi: {r['roi'] or ''}")
    lines.append(f"deps: {json.dumps(deps, ensure_ascii=False)}")
    lines.append(f"tags: {json.dumps(tags, ensure_ascii=False)}")
    lines.append(f"objective: {r['objective'] or ''}")
    lines.append(f"align: {r['align'] or ''}")
    lines.append(f"source: {src}")
    lines.append(f"source_hint: {json.dumps(hint, ensure_ascii=False)}")
    lines.append(f"updated: {r['updated'] or ''}")
    lines.append("generated_by: background.py   # 本文件由 DB 渲染生成，勿手改；改 DB 后重跑 topic-render")
    lines.append("---")
    lines.append("")
    lines.append(f"# {t}")
    lines.append("")
    lines.append(f"> 状态机：{' → '.join(STATUSES)}")
    lines.append(f">  当前：**{r['status']}**")
    lines.append("")
    lines.append("## 目标 / 核心问题")
    lines.append(r["objective"] or "-")
    lines.append("")
    lines.append("## 产物（按命名约定）")
    lines.append(f"- 资料清单：[[{t}_sources]]　前置：[[{src}_prereq]]")
    lines.append(f"- 随文 QA：`{src}_qa/`　归档：[[{t}_原文素材归档]]　编排：[[{t}_arrangement]]")
    lines.append(f"- 教材：[[{t}_Textbook.pdf]]　复习卡：[[{t}_review]]")
    lines.append(f"- 预习组：[[{t}_预习_Textbook.pdf]]　`{t}_预习_qa/`")
    lines.append("")
    lines.append(f"## 本 topic 贡献的 S_have（{len(have)} 条，来自 DB）")
    if not have:
        lines.append("- （尚无）")
    for h in have:
        flag = "⚠️ shaky" if h["status"] == "shaky" else "mastered"
        lines.append(f"- [{flag}] ({h['domain']} / {h['grp']}) {h['capability']}　‹id: {h['id']}›")
    lines.append("")
    out = Path(args.out) if args.out else Path(f"{t}_hub.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[topic-render] ✓ {out}（由 DB 生成的视图；勿手改）")
    return 0


def cmd_board(args) -> int:
    con = connect(resolve_db(args))
    rows = con.execute("SELECT * FROM topics ORDER BY status, roi DESC, updated DESC").fetchall()
    out_lines = ["# 主题进度看板（由 background.py board 生成）", "",
                 "| topic | status | roi | deps | objective | updated |",
                 "|---|---|---|---|---|---|"]
    for r in rows:
        deps = ", ".join(json.loads(r["deps"] or "[]"))
        obj = (r["objective"] or "").replace("|", "\\|")
        out_lines.append(f"| {r['topic']} | {r['status']} | {r['roi'] or '-'} | {deps} | {obj} | {r['updated'] or '-'} |")
    text = "\n".join(out_lines) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"[board] ✓ {args.out}（{len(rows)} 个 topic）")
    else:
        print(text)
    return 0


# ---------- s_have ----------

def cmd_have_add(args) -> int:
    if args.status not in HAVE_STATUS:
        print(f"✗ 未知 status：{args.status}（合法：{'/'.join(HAVE_STATUS)}）", file=sys.stderr)
        return 1
    if args.group not in GROUPS:
        print(f"✗ 未知 group：{args.group}（合法：{'/'.join(GROUPS)}）", file=sys.stderr)
        return 1
    if args.source not in SOURCES:
        print(f"✗ 未知 source：{args.source}（合法：{'/'.join(SOURCES)}）", file=sys.stderr)
        return 1
    con = connect(resolve_db(args))
    ts = today(args)
    if args.topic:
        if not con.execute("SELECT 1 FROM topics WHERE topic=?", (args.topic,)).fetchone():
            print(f"✗ topic 不存在：{args.topic}（先 topic-upsert，保证 FK 完整）", file=sys.stderr)
            return 1
    cur = con.execute("SELECT * FROM s_have WHERE domain=? AND id=?", (args.domain, args.id)).fetchone()
    merged = {
        "domain": args.domain,
        "id": args.id,
        "capability": args.capability if args.capability is not None else (cur["capability"] if cur else None),
        "status": args.status,
        "topic": args.topic if args.topic is not None else (cur["topic"] if cur else None),
        "grp": args.group,
        "source": args.source,
        "added": (cur["added"] if cur else ts),   # 幂等：保留首次 added
        "note": args.note if args.note is not None else (cur["note"] if cur else None),
    }
    if merged["capability"] is None:
        print("✗ 新增条目必须给 --capability", file=sys.stderr)
        return 1
    con.execute("""
        INSERT OR REPLACE INTO s_have
        (domain,id,capability,status,topic,grp,source,added,note)
        VALUES (:domain,:id,:capability,:status,:topic,:grp,:source,:added,:note)
    """, merged)
    log(con, "s_have", f"{args.domain}/{args.id}", "update" if cur else "add", ts)
    con.commit()
    verb = "更新（幂等去重，不新增行）" if cur else "新增"
    print(f"[have-add] {verb} {args.domain}/{args.id}｜{merged['status']}｜grp={merged['grp']}｜topic={merged['topic']}")
    return 0


def _have_rows(con, args):
    q = "SELECT * FROM s_have WHERE 1=1"
    params = []
    if getattr(args, "domain", None):
        q += " AND domain IN (%s)" % ",".join("?" * len(args.domain))
        params += args.domain
    if getattr(args, "topic", None):
        q += " AND topic=?"
        params.append(args.topic)
    if getattr(args, "group", None):
        q += " AND grp=?"
        params.append(args.group)
    if getattr(args, "status", None):
        q += " AND status=?"
        params.append(args.status)
    q += " ORDER BY domain, grp, id"
    return con.execute(q, params).fetchall()


def cmd_have_query(args) -> int:
    con = connect(resolve_db(args))
    rows = _have_rows(con, args)
    if args.format == "json":
        print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))
        return 0
    if args.format == "plain":
        for r in rows:
            print(r["capability"])
        return 0
    # md（默认）：按领域分组，shaky 显式标注（→ prereq 视为"不要默认已会"，进 S_bridge）
    scope = ("domain=" + ",".join(args.domain)) if args.domain else "全部领域"
    print(f"# S_have（{scope}{('｜group=' + args.group) if args.group else ''}）— 差集 S_have 来源")
    cur_dom = None
    for r in rows:
        if r["domain"] != cur_dom:
            cur_dom = r["domain"]
            print(f"\n## {cur_dom}")
        flag = "⚠️ 仍存疑(shaky)" if r["status"] == "shaky" else "已掌握"
        print(f"- [{flag}] {r['capability']}　‹id:{r['id']}｜{r['grp']}｜topic:{r['topic']}›")
    print(f"\n（{len(rows)} 条；shaky 项 prereq 差集**不要**默认已会，遇到要补 S_bridge）")
    return 0


def cmd_have_domains(args) -> int:
    con = connect(resolve_db(args))
    rows = con.execute("""
        SELECT domain, COUNT(*) n,
               SUM(CASE WHEN status='shaky' THEN 1 ELSE 0 END) shaky
        FROM s_have GROUP BY domain ORDER BY domain
    """).fetchall()
    if not rows:
        print("(无 S_have)")
        return 0
    for r in rows:
        print(f"{r['domain']:<18} {r['n']:>3} 条（含 shaky {r['shaky']}）")
    return 0


def cmd_have_table(args) -> int:
    con = connect(resolve_db(args))
    rows = con.execute("SELECT * FROM s_have ORDER BY domain, grp, id").fetchall()
    out = ["# 能力现状表（由 background.py have-table 生成；台账为准，勿手改）", ""]
    cur_dom = None
    for r in rows:
        if r["domain"] != cur_dom:
            cur_dom = r["domain"]
            out += [f"## {cur_dom}", "", "| 能力 | 状态 | 组 | topic | 加入 |", "|---|---|---|---|---|"]
        cap = (r["capability"] or "").replace("|", "\\|")
        out.append(f"| {cap} | {r['status']} | {r['grp']} | {r['topic'] or '-'} | {r['added'] or '-'} |")
    text = "\n".join(out) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"[have-table] ✓ {args.out}")
    else:
        print(text)
    return 0


# ---------- validate ----------

def cmd_validate(args) -> int:
    con = connect(resolve_db(args))
    problems = []
    for r in con.execute("SELECT * FROM topics").fetchall():
        if r["status"] not in STATUSES:
            problems.append(f"topic {r['topic']}: 非法 status={r['status']}")
        for col in ("deps", "source_hint", "tags"):
            try:
                json.loads(r[col] or "[]")
            except json.JSONDecodeError:
                problems.append(f"topic {r['topic']}: {col} 不是合法 JSON")
    for r in con.execute("SELECT * FROM s_have").fetchall():
        ref = f"{r['domain']}/{r['id']}"
        if r["status"] not in HAVE_STATUS:
            problems.append(f"s_have {ref}: 非法 status={r['status']}")
        if r["grp"] not in GROUPS:
            problems.append(f"s_have {ref}: 非法 group={r['grp']}")
        if not r["capability"]:
            problems.append(f"s_have {ref}: capability 空")
        if r["topic"] and not con.execute("SELECT 1 FROM topics WHERE topic=?", (r["topic"],)).fetchone():
            problems.append(f"s_have {ref}: FK 悬空——topic={r['topic']} 不存在")
    fk = con.execute("PRAGMA foreign_key_check").fetchall()
    for v in fk:
        problems.append(f"FK 违例：{tuple(v)}")
    if problems:
        print(f"[validate] ✗ {len(problems)} 个问题：")
        for p in problems:
            print(f"  - {p}")
        return 1
    nt = con.execute("SELECT COUNT(*) c FROM topics").fetchone()["c"]
    nh = con.execute("SELECT COUNT(*) c FROM s_have").fetchone()["c"]
    print(f"[validate] ✓ 通过（topics {nt}｜s_have {nh}｜FK/枚举/JSON 全过）")
    return 0


# ---------- CLI ----------

def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(description="个人背景结构化机械层（SQLite：topics + s_have + changelog）")
    ap.add_argument("--db", default=None, help="DB 路径；默认 $PERSONAL_BACKGROUND/background.db")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="建表（幂等）")

    p = sub.add_parser("topic-upsert", help="新增/更新 topic（只覆盖给定字段）")
    p.add_argument("topic")
    p.add_argument("--status", default=None)
    p.add_argument("--roi", default=None)
    p.add_argument("--objective", default=None)
    p.add_argument("--align", default=None, help="与阶段定位的对齐/降级说明（source_selection 取材深度依据）")
    p.add_argument("--deps", default=None, help="逗号分隔的前置 topic")
    p.add_argument("--source-hint", dest="source_hint", default=None, help="逗号分隔的候选材料方向")
    p.add_argument("--tags", default=None, help="逗号分隔标签")
    p.add_argument("--source", default=None, help="主材料文件名主体（QA 落 {source}_qa/）")
    p.add_argument("--note", default=None)
    p.add_argument("--date", default=None, help="覆盖日期（默认今天；测试可定）")

    p = sub.add_parser("topic-status", help="切换 status（校验枚举 + 记 changelog）")
    p.add_argument("topic")
    p.add_argument("status")
    p.add_argument("--date", default=None)

    p = sub.add_parser("topic-list", help="列出 topics")
    p.add_argument("--status", default=None)

    p = sub.add_parser("topic-show", help="显示某 topic + 其 S_have")
    p.add_argument("topic")

    p = sub.add_parser("topic-render", help="渲染 {topic}_hub.md 视图（DB→视图）")
    p.add_argument("topic")
    p.add_argument("--out", default=None, help="输出路径；默认 {topic}_hub.md")

    p = sub.add_parser("board", help="渲染全 topic 进度看板")
    p.add_argument("--out", default=None)

    p = sub.add_parser("have-add", help="幂等写入一条 S_have（按 domain/id upsert）")
    p.add_argument("--domain", required=True)
    p.add_argument("--id", required=True, help="领域内稳定唯一 slug")
    p.add_argument("--capability", default=None)
    p.add_argument("--status", default="mastered", help="mastered|shaky")
    p.add_argument("--topic", default=None, help="贡献它的 topic（FK）")
    p.add_argument("--group", default="main", help="main|prereq")
    p.add_argument("--source", default="pipeline", help="pipeline|weekly|manual")
    p.add_argument("--note", default=None)
    p.add_argument("--date", default=None)

    p = sub.add_parser("have-query", help="读 S_have（prereq 差集来源）")
    p.add_argument("--domain", nargs="+", default=None, help="一个或多个领域")
    p.add_argument("--topic", default=None)
    p.add_argument("--group", default=None, help="main|prereq")
    p.add_argument("--status", default=None, help="mastered|shaky")
    p.add_argument("--format", default="md", choices=["md", "plain", "json"])

    p = sub.add_parser("have-domains", help="列出领域 + 计数")

    p = sub.add_parser("have-table", help="渲染能力现状表")
    p.add_argument("--out", default=None)

    sub.add_parser("validate", help="校验 FK/枚举/JSON")

    args = ap.parse_args(argv)
    dispatch = {
        "init": cmd_init,
        "topic-upsert": cmd_topic_upsert,
        "topic-status": cmd_topic_status,
        "topic-list": cmd_topic_list,
        "topic-show": cmd_topic_show,
        "topic-render": cmd_topic_render,
        "board": cmd_board,
        "have-add": cmd_have_add,
        "have-query": cmd_have_query,
        "have-domains": cmd_have_domains,
        "have-table": cmd_have_table,
        "validate": cmd_validate,
    }
    return dispatch[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
