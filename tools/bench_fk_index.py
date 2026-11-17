# -*- coding: utf-8 -*-
r"""外键列索引对比：5 万用户 / 20 万计划，测查询与级联删除。

用法：
    python tools\bench_fk_index.py

脚本自建临时库 tools\_fk_index_bench.db，跑完删除。
不需要 Alembic，也不碰 app.db。
"""
import os
import sqlite3
import statistics
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "_fk_index_bench.db")

N_USERS = 50_000
N_PLANS = 200_000
EXTRA_USERS = 40          # 前 20 个用于无索引删除，后 20 个用于有索引删除
EXTRA_PLANS = 5

DDL = """
PRAGMA foreign_keys = ON;
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    nickname TEXT NOT NULL,
    password TEXT NOT NULL
);
CREATE TABLE plan_days (
    plan_id INTEGER PRIMARY KEY,
    calender TEXT NOT NULL,
    add_date TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
"""


def timed(fn, repeat=1):
    t0 = time.perf_counter()
    for _ in range(repeat):
        fn()
    return (time.perf_counter() - t0) / repeat


def plan_rows(conn, sql, params=()):
    return [row[3] for row in conn.execute("EXPLAIN QUERY PLAN " + sql, params)]


def main():
    if os.path.exists(DB):
        os.remove(DB)
    conn = sqlite3.connect(DB)
    conn.executescript(DDL)

    print("准备数据：%d 用户 / %d 计划 …" % (N_USERS, N_PLANS))
    users = [("u%d@example.com" % i, "n%d" % i, "p") for i in range(1, N_USERS + 1)]
    conn.executemany("INSERT INTO users(email, nickname, password) VALUES (?, ?, ?)", users)

    plans = [
        ("2026-10", "2026-10-20", (i % N_USERS) + 1)
        for i in range(N_PLANS)
    ]
    conn.executemany(
        "INSERT INTO plan_days(calender, add_date, user_id) VALUES (?, ?, ?)", plans
    )

    extra_ids = list(range(N_USERS + 1, N_USERS + EXTRA_USERS + 1))
    conn.executemany(
        "INSERT INTO users(user_id, email, nickname, password) VALUES (?, ?, ?, ?)",
        [(uid, "extra%d@example.com" % uid, "x", "p") for uid in extra_ids],
    )
    conn.executemany(
        "INSERT INTO plan_days(calender, add_date, user_id) VALUES (?, ?, ?)",
        [("2026-10", "2026-10-20", uid) for uid in extra_ids for _ in range(EXTRA_PLANS)],
    )
    conn.commit()

    sample_user = 12345
    query = "SELECT COUNT(*) FROM plan_days WHERE user_id = ?"

    def run_query():
        conn.execute(query, (sample_user,)).fetchone()

    print("\n=== 查询：%s（用户 %d）===" % (query, sample_user))
    print("无索引 EXPLAIN:", plan_rows(conn, query, (sample_user,)))
    no_idx_ms = timed(run_query, 100) * 1000
    print("无索引：%8.3f ms/次（100 次平均）" % no_idx_ms)

    def delete_batch(start):
        for uid in range(start, start + 20):
            conn.execute("DELETE FROM users WHERE user_id = ?", (uid,))
        conn.commit()

    print("\n=== 级联删除：20 个用户（每人 %d 条计划）===" % EXTRA_PLANS)
    no_idx_delete_ms = timed(lambda: delete_batch(N_USERS + 1)) * 1000
    print("无索引：%8.3f ms（删除 20 个用户，含级联）" % no_idx_delete_ms)

    print("\n建立索引 idx_plan_days_user_id …")
    conn.execute("CREATE INDEX idx_plan_days_user_id ON plan_days(user_id)")
    conn.commit()

    print("\n=== 建索引后 ===")
    print("有索引 EXPLAIN:", plan_rows(conn, query, (sample_user,)))
    idx_ms = timed(run_query, 100) * 1000
    print("有索引：%8.3f ms/次（100 次平均）" % idx_ms)

    idx_delete_ms = timed(lambda: delete_batch(N_USERS + 21)) * 1000
    print("有索引：%8.3f ms（删除 20 个用户，含级联）" % idx_delete_ms)

    print("\n" + "=" * 46)
    print("查询加速：%.1f 倍" % (no_idx_ms / idx_ms if idx_ms else float("inf")))
    print("级联删除加速：%.1f 倍" % (no_idx_delete_ms / idx_delete_ms if idx_delete_ms else float("inf")))
    print("=" * 46)

    conn.close()
    os.remove(DB)


if __name__ == "__main__":
    main()