-- 学习助手 · 表结构
--
-- 这个文件是可选的。两种交付方式，二选一即可：
--   A. 用文字写设计  -> docs\0001-schema-design.md 的「四、设计区」
--   B. 直接用 SQL 写 -> 就写在这个文件里
--
-- 写在这里的好处是能真跑：写完存盘，然后在 项目-学习助手 目录下执行
--   python tools\run_schema.py
-- 它会执行你的语句，并把「每张表的字段 / 主键 / 外键 / 唯一约束」打成一张清单，
-- 有语法错会直接报出来。
--
-- 下面的语句只是示例，删掉换成你自己的（或者整段删掉，改用方式 A）。
--表 1 用户信息/用来存储和调用用户信息/id,email,nickname,password NOT NULL 存哈希串/主键是id/无键/id email只能出现一次
CREATE TABLE users (
    user_id       INTEGER PRIMARY KEY,
    email    TEXT NOT NULL UNIQUE,
    nickname TEXT NOT NULL,
    password text NOT NULL
);
--表 2目标天信息/用来存储用户的计划日历/id（主键），日历，新日期date，user_id（外键）
CREATE TABLE plan_days(
    plan_id INTEGER PRIMARY KEY,
    calender Text not null,
    add_date text not null,
    user_id INTEGER not null,
    FOREIGN KEY(user_id) REFERENCES users(user_id)on delete cascade
);
--表3 clock时刻，id(主键)，计划，计划的id(外键ondeletecascade)
CREATE TABLE newplan(
    plan_id INTEGER not null,
    id INTEGER PRIMARY KEY,
    plan Text not null,
    FOREIGN KEY(plan_id) REFERENCES plan_days(plan_id)on delete cascade
);
--表 4 资料信息/资料id(主键)唯一，name资料名字，文件，网址，userid(外键)
CREATE TABLE documents(
    id INTEGER PRIMARY KEY,
    documents_name text not null,
    docments Text,
    websites text,
    user_id INTEGER not null,
    constraint chk_contact_at_least_one
        CHECK (docments is not null or websites is not null),
    FOREIGN KEY(user_id)  REfERENCES users(user_id)on delete cascade
);
--表 5 系统出题/资料id(外键on delete cascade)，，id（主键），答题时间
CREATE TABLE question(
    doc_id INTEGER not null,
    id INTEGER PRIMARY KEY,
    que text not null,
    system_answer INTEGER not null,
    Foreign key(doc_id) REFERENCES documents(id)on delete cascade
);
--表6 题目id（外键），用户答案，答题时间，判的成绩，id（主键）
CREATE table answer(
    owner_id integer not null,
    que_id INTEGER not null,
    id INTEGER PRIMARY key,
    answer_time text not null,
    user_answer  text not null,
    costtime INTEGER not null,
    scores text not null,
    Foreign key(que_id) REFERENCES question(id)on delete cascade,
    foreign key(owner_id) references users(user_id)on delete cascade
);