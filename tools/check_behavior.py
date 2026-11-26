# -*- coding: utf-8 -*-
r"""行为验收：不看语法，只看这套表能不能真的用。

用法（在 项目-学习助手 目录下）：
    python tools\check_behavior.py

它把 docs\schema.sql 建进一个内存库，然后按 8 个真实场景插数据：
  1. 重复邮箱
  2. 两个人用同一个昵称
  3. 只登记网址（或只登记文件）的资料
  4. 同一用户同一天两条计划
  5. 同一道题答两次
  6. 删用户看级联
  7. 题目表有没有地方存题干
  8. 答题记录能不能说清是谁答的

输出三档：PASS / FAIL / 待决定。
这个脚本不改你的文件，也不落盘。
"""
import os
import sqlite3
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_schema import SCHEMA_PATH, split_statements

results = []


def rec(status, name, detail):
    results.append((status, name, detail))


def build():
    sql = open(SCHEMA_PATH, encoding="utf-8").read()
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    for _line, text, _semi in split_statements(sql):
        conn.execute(text)
    return conn


def cols(conn, table):
    return [r[1] for r in conn.execute("PRAGMA table_info(%s)" % table)]


def add_user(conn, email, nickname, password="hash"):
    cur = conn.execute(
        "INSERT INTO users (email, nickname, password) VALUES (?, ?, ?)",
        (email, nickname, password),
    )
    return cur.lastrowid


def required_cols(conn, table):
    """非空、非主键、无默认值的列 —— 插数据时必须给值的那些。"""
    return [r[1] for r in conn.execute("PRAGMA table_info(%s)" % table)
            if r[3] and not r[5] and r[4] is None]


FILL = {
    "que": "以下哪个是主键？", "system_answer": 1,
    "answer_time": "2026-10-18T21:00:00", "user_answer": "A",
    "costtime": 10, "scores": "1", "plan": "背 20 个词",
    "calender": "week", "add_date": "2026-10-18",
    "documents_name": "资料", "docments": "notes.pdf",
    "websites": "https://example.com", "email": "a@x.com",
    "nickname": "A", "password": "h",
}


def ins_row(conn, table, **kw):
    """按表当前的真实必填列插一行 —— schema 改列名后测试不用跟着改。"""
    cols = required_cols(conn, table)
    sql = "INSERT INTO %s (%s) VALUES (%s)" % (
        table, ", ".join(cols), ", ".join("?" for _ in cols))
    try:
        conn.execute(sql, tuple(kw.get(c, FILL.get(c, "x")) for c in cols))
        return None
    except sqlite3.Error as exc:
        return str(exc)


def ins_answer(conn, que_id, owner_id, user_answer="A", scores="1"):
    """按 answer 表实际的必填列插一条作答记录，列名变了也不用改测试。"""
    preset = {
        "que_id": que_id, "user_answer": user_answer, "scores": scores,
        "costtime": 10, "answer_time": "2026-10-18T21:00:00",
        "owner_id": owner_id, "user_id": owner_id,
    }
    cols = required_cols(conn, "answer")
    sql = "INSERT INTO answer (%s) VALUES (%s)" % (
        ", ".join(cols), ", ".join("?" for _ in cols))
    try:
        conn.execute(sql, tuple(preset.get(c, "x") for c in cols))
        return None
    except sqlite3.Error as exc:
        return str(exc)


def try_insert(conn, sql, params):
    try:
        conn.execute(sql, params)
        return None
    except sqlite3.Error as exc:
        return str(exc)


def check_email_unique():
    conn = build()
    add_user(conn, "a@x.com", "A")
    err = try_insert(
        conn,
        "INSERT INTO users (email, nickname, password) VALUES (?, ?, ?)",
        ("a@x.com", "B", "hash"),
    )
    if err:
        rec("PASS", "重复邮箱被拦住", err)
    else:
        rec("FAIL", "重复邮箱没被拦住", "同一个邮箱能注册两次 —— 登录时认不出是谁")
    conn.close()


def check_nickname_repeat():
    conn = build()
    e1 = try_insert(conn, "INSERT INTO users (email, nickname, password) VALUES (?, ?, ?)",
                    ("a@x.com", "同名", "h"))
    e2 = try_insert(conn, "INSERT INTO users (email, nickname, password) VALUES (?, ?, ?)",
                    ("b@x.com", "同名", "h"))
    if e1 is None and e2 is None:
        rec("PASS", "两人可以同名昵称", "昵称没有加唯一约束，符合预期")
    else:
        rec("FAIL", "两人不能同名昵称", "昵称被加了唯一约束：%s" % (e1 or e2))
    conn.close()


def check_document_partial():
    conn = build()
    uid = add_user(conn, "a@x.com", "A")
    e1 = try_insert(conn,
        "INSERT INTO documents (documents_name, websites, user_id) VALUES (?, ?, ?)",
        ("只登记网址", "https://example.com", uid))
    e2 = try_insert(conn,
        "INSERT INTO documents (documents_name, docments, user_id) VALUES (?, ?, ?)",
        ("只登记文件", "notes.pdf", uid))
    bad = []
    if e1:
        bad.append("只给网址（docments 留空）存不进去")
    if e2:
        bad.append("只给文件（websites 留空）存不进去")
    if bad:
        rec("FAIL", "资料只填一半", "；".join(bad) + " —— 两列都写了 NOT NULL")
    else:
        rec("PASS", "资料可以只填一半", "文件和网址都能空着")
    conn.close()


def check_two_plans_same_day():
    conn = build()
    uid = add_user(conn, "a@x.com", "A")
    e1 = try_insert(conn,
        "INSERT INTO plan_days (calender, add_date, user_id) VALUES (?, ?, ?)",
        ("week", "2026-10-18", uid))
    e2 = try_insert(conn,
        "INSERT INTO plan_days (calender, add_date, user_id) VALUES (?, ?, ?)",
        ("week", "2026-10-18", uid))
    if e1 is None and e2 is None:
        rec("待决定", "同一天两条计划", "现在允许。如果一天只该有一条，需要 UNIQUE(user_id, add_date)")
    else:
        rec("PASS", "同一天两条计划被拦住", e1 or e2)
    conn.close()


def check_answer_twice():
    conn = build()
    uid = add_user(conn, "a@x.com", "A")
    conn.execute("INSERT INTO documents (documents_name, docments, websites, user_id)\n                 VALUES (?, ?, ?, ?)",
                 ("资料", "notes.pdf", "https://example.com", uid))
    ins_row(conn, "question", doc_id=1)
    e1 = ins_answer(conn, 1, uid, "A", "1")
    e2 = ins_answer(conn, 1, uid, "B", "0")
    has_time = [c for c in cols(conn, "answer") if "time" in c.lower() or "date" in c.lower()]
    if e1 is None and e2 is None:
        detail = "现在允许同一题答多次"
        if not has_time:
            detail += "，但 answer 表没有作答时间列，分不清哪次是新答的"
        rec("待决定", "同一题答两次", detail)
    else:
        rec("PASS", "同一题只能答一次", str(e1 or e2))
    conn.close()


def check_cascade():
    conn = build()
    uid = add_user(conn, "a@x.com", "A")
    conn.execute("INSERT INTO plan_days (calender, add_date, user_id) VALUES (?, ?, ?)",
                 ("week", "2026-10-18", uid))
    conn.execute("INSERT INTO newplan (plan_id, plan) VALUES (?, ?)", (1, "背 20 个词"))
    conn.execute("INSERT INTO documents (documents_name, docments, websites, user_id)\n                 VALUES (?, ?, ?, ?)",
                 ("资料", "notes.pdf", "https://example.com", uid))
    ins_row(conn, "question", doc_id=1)
    ins_answer(conn, 1, uid, "A", "1")
    conn.execute("DELETE FROM users WHERE user_id = ?", (uid,))
    conn.commit()
    left = {}
    for t in ("users", "plan_days", "newplan", "documents", "question", "answer"):
        left[t] = conn.execute("SELECT count(*) FROM %s" % t).fetchone()[0]
    empties = [t for t, n in left.items() if n == 0]
    if len(empties) == len(left):
        rec("PASS", "删用户级联", "删掉用户后六张表全部清空")
    else:
        rec("FAIL", "删用户后留了孤儿", "还剩：%s" % left)
    conn.close()


def check_question_stem():
    conn = build()
    c = cols(conn, "question")
    info_cols = [x for x in c if x not in ("id", "doc_id", "answer_time", "system_answer")]
    if info_cols:
        rec("PASS", "题目表有题干位", "多出来的列：%s" % info_cols)
    else:
        rec("FAIL", "题目表没有题干位", "现在只能存 doc_id / answer_time / system_answer，没地方放题目本身")
    conn.close()


def check_answer_owner():
    conn = build()
    c = cols(conn, "answer")
    if "user_id" in c or "owner_id" in c:
        rec("PASS", "答题记录有 owner 列", "answer 里有 %s" % ("user_id" if "user_id" in c else "owner_id"))
    else:
        rec("FAIL", "答题记录没有 owner 列",
            "answer 只有 que_id，谁答的只能靠 question→documents→users 三跳推出来；"
            "用户 B 答 A 的题，记录会算到 A 名下")
    conn.close()


def main():
    if not os.path.exists(SCHEMA_PATH):
        print("还没找到 %s" % SCHEMA_PATH)
        return 2
    try:
        build().close()
    except sqlite3.Error as exc:
        print("建表就失败了，8 个场景都没法跑：%s" % exc)
        print("先把 tools/run_schema.py 跑到全部通过，再回来跑这个。")
        return 2
    for fn in (check_email_unique, check_nickname_repeat, check_document_partial,
               check_two_plans_same_day, check_answer_twice, check_cascade,
               check_question_stem, check_answer_owner):
        try:
            fn()
        except sqlite3.Error as exc:
            rec("FAIL", fn.__name__, "场景跑不下去：%s" % exc)

    width = max(len(n) for _s, n, _d in results)
    for status, name, detail in results:
        print("[%s] %s  %s" % (status, name.ljust(width), detail))
    print("-" * 60)
    fails = sum(1 for s, _n, _d in results if s == "FAIL")
    asks = sum(1 for s, _n, _d in results if s == "待决定")
    print("PASS %d / FAIL %d / 待决定 %d" % (len(results) - fails - asks, fails, asks))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
