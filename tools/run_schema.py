# -*- coding: utf-8 -*-
r"""跑一遍你的建表语句，一次报出所有问题。

用法（在 项目-学习助手 目录下）：
    python tools\run_schema.py

做四件事：
  1. 检查有没有「不是 SQL 注释」的行（比如 # 开头）
  2. 检查有没有漏掉语句结尾的分号
  3. 把语句拆开逐条执行 —— 一次列出全部错误，不是只报第一个
  4. 跑通后打印每张表的字段、主键、外键、唯一约束

这个脚本不改你的文件，也不会生成数据库文件。
"""
import os
import re
import sqlite3
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCHEMA_PATH = os.path.join(ROOT, "docs", "schema.sql")

VERB_RE = re.compile(
    r"(?im)^[ \t]*(CREATE|DROP|ALTER|INSERT|UPDATE|DELETE|PRAGMA|BEGIN|COMMIT|ROLLBACK)\b"
)


def split_statements(sql):
    """按「行首的 SQL 动词」拆语句。返回 (起始行号, 语句文本, 是否以分号结尾) 列表。

    按动词拆而不是按分号拆 —— 漏了分号时也能正确分开，便于逐条报错。
    """
    starts = [m.start() for m in VERB_RE.finditer(sql)]
    chunks = []
    for k, pos in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(sql)
        text = sql[pos:end].strip()
        # 末尾的空行/注释行不算语句内容，否则「上一条语句 + 下一条的表注释」会被误判成漏分号
        body = text
        while True:
            lines = body.rstrip().splitlines()
            if lines and (not lines[-1].strip() or lines[-1].lstrip().startswith("--")):
                body = "\n".join(lines[:-1])
                continue
            break
        has_semicolon = body.rstrip().endswith(";")
        if text.endswith(";"):
            text = text[:-1].rstrip()
        if text:
            chunks.append((sql.count("\n", 0, pos) + 1, text, has_semicolon))
    return chunks


def check_hash_lines(sql):
    return [(n, l.strip()) for n, l in enumerate(sql.splitlines(), 1) if l.strip().startswith("#")]


FULLWIDTH = {
    "，": ",", "；": ";", "：": ":", "（": "(", "）": ")",
    "　": " ", "“": "\"", "”": "\"", "‘": "'", "’": "'",
}


def check_fullwidth(sql):
    """中文输入法打出来的全角标点，SQL 一个都不认。注释里的不算。"""
    hits = []
    for n, line in enumerate(sql.splitlines(), 1):
        code = line.split("--")[0]
        for ch, repl in FULLWIDTH.items():
            if ch in code:
                hits.append((n, ch, repl))
    return hits


def check_semicolons(sql):
    """提示漏分号的语句（不报错，只是提醒）。"""
    missing = []
    for line, text, has_semicolon in split_statements(sql):
        if not has_semicolon:
            missing.append(line)
    return missing


def describe(conn, table):
    out = ["=== %s ===" % table]
    rows = conn.execute("PRAGMA table_info(%s)" % table).fetchall()
    out.append("  %-18s %-9s %s" % ("列名", "类型", "约束"))
    for cid, col, ctype, notnull, dflt, pk in rows:
        flags = []
        if pk:
            flags.append("主键（自动编号，不可为空）" if (ctype or "").upper() == "INTEGER" else "主键")
        else:
            flags.append("NOT NULL" if notnull else "可为空")
        if dflt is not None:
            flags.append("默认 %s" % dflt)
        out.append("  %-18s %-9s %s" % (col, ctype or "（没写类型！）", "、".join(flags)))
    fks = conn.execute("PRAGMA foreign_key_list(%s)" % table).fetchall()
    if fks:
        for fk in fks:
            out.append("  -> 外键 %s 指向 %s(%s)，ON DELETE %s" % (fk[3], fk[2], fk[4], fk[6]))
    else:
        out.append("  -> 没有外键")
    for idx in conn.execute("PRAGMA index_list(%s)" % table):
        if idx[2]:
            cols_in = [r[2] for r in conn.execute("PRAGMA index_info(%s)" % idx[1])]
            out.append("  -> 唯一约束：%s" % " + ".join(cols_in))
    out.append("")
    return out


SEMANTIC_HINTS = [
    "提醒（脚本查不出语义，这几点只能靠你想）：",
    "  · 题目表里有「题干」这一列吗？存题目的表没有题干，只是半个表。",
    "  · 属于「一次作答」的列（用户答案 / 答题时间 / 对错）应该在答题记录表；标准答案应该跟题目走。",
    "  · 外键上写 ON DELETE CASCADE 了吗？没写的话，删用户时下游数据会变成孤儿。",
]


def main():
    if not os.path.exists(SCHEMA_PATH):
        print("还没找到 %s" % SCHEMA_PATH)
        return 2

    with open(SCHEMA_PATH, encoding="utf-8") as f:
        sql = f.read()

    problems = 0

    bad = check_hash_lines(sql)
    if bad:
        problems += len(bad)
        print("【问题 1】下面这些行不是 SQL 注释，数据库会报 unrecognized token: \"#\"")
        for num, text in bad:
            print("  第 %d 行：%s" % (num, text[:64]))
        print("  SQL 的注释是 --（两个减号）。整行前面加 --，或者直接删掉。")
        print()

    full = check_fullwidth(sql)
    if full:
        problems += len(full)
        print("【问题 2】这些行里有中文全角标点，SQL 只认半角")
        for num, ch, repl in full:
            print("  第 %d 行：%s（U+%04X）应该写成 %s" % (num, ch, ord(ch), repl))
        print("  最常踩的是逗号 ， 和分号 ； —— 切到英文输入法再打。")
        print()

    stmts = split_statements(sql)
    if not stmts:
        print("%s 里没有可执行的语句（只有注释？）。" % SCHEMA_PATH)
        return 2

    missing_semi = check_semicolons(sql)
    if missing_semi:
        problems += len(missing_semi)
        print("【问题 3】这些语句结尾漏了分号（起始行 %s）" % "、".join(str(x) for x in missing_semi))
        print("  每条语句结尾都要有 ; —— 加了之后，文件才能整段执行。")
        print()

    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    failed, ok_count = [], 0
    for start_line, text, _has_semi in stmts:
        try:
            conn.execute(text)
            ok_count += 1
        except sqlite3.Error as exc:
            failed.append((start_line, " ".join(text.split())[:64], exc))

    print("【问题 4】逐条执行：%d 条语句，%d 条成功，%d 条失败" % (len(stmts), ok_count, len(failed)))
    if failed:
        problems += len(failed)
        for start_line, head, exc in failed:
            print("  第 %d 行  %s" % (start_line, head))
            print("     -> %s" % exc)
        print()
        print("  常见原因：① 列名后面漏了类型（要跟 INTEGER / TEXT）")
        print("            ② 最后一条列定义后面多了逗号（紧跟 ) 的那个）")
        print("            ③ 关键字拼错（REFERENCES）")
        print("            ④ 外键指向的表名和实际建出来的表名不一致")
        print()

    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]
    if tables:
        print("【结构清单】已成功建出 %d 张表：%s" % (len(tables), "、".join(tables)))
        print()
        for name in tables:
            for line in describe(conn, name):
                print(line)

    print("=" * 52)
    if problems == 0:
        print("全部通过：%d 条语句、%d 张表。" % (len(stmts), len(tables)))
        print()
        for hint in SEMANTIC_HINTS:
            print(hint)
        return 0
    print("共发现 %d 个问题，改完存盘再跑一次。" % problems)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())