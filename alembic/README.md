# Alembic 使用说明（本项目）

> 数据库表结构的**版本化迁移**。改表不用再手写 `ALTER TABLE`，也不用重建库。

## 一、一次性检查（每次拉代码后）

```powershell
cd C:\Users\lyt2001\Desktop\ec_platform
.\.venv\Scripts\python.exe -m alembic current    # 当前库在哪个版本
.\.venv\Scripts\python.exe -m alembic upgrade head   # 升到最新
```

## 二、日常改表流程

```
1. 改 model
      app/models/xxx.py 里加/改字段

2. 生成迁移脚本（不执行）
      alembic revision --autogenerate -m "给 user 加 last_login_at"

3. ★ 打开生成的文件看一遍 ★
      alembic/versions/xxxx_给_user_加_last_login_at.py
      确认 upgrade() 里只有你要的改动，没有意外删表/删索引

4. 执行
      alembic upgrade head

5. 出问题就回滚
      alembic downgrade -1
```

## 三、常用命令

| 命令 | 作用 |
|---|---|
| `alembic current` | 当前库的版本号（带 `(head)` 表示最新） |
| `alembic history` | 所有迁移历史，从旧到新 |
| `alembic upgrade head` | 升到最新 |
| `alembic upgrade +1` | 只升一个版本 |
| `alembic downgrade -1` | 回退一个版本 |
| `alembic downgrade base` | 全部回退（**会删表，慎用**） |
| `alembic check` | 检查「模型」和「数据库」是否一致，一致会打印 `No new upgrade operations detected.` |
| `alembic upgrade head --sql` | 不连库，只打印要执行的 SQL（给 DBA 审） |
| `alembic stamp head` | **只记录版本号、不执行 SQL**（给已有库打基线用） |

## 四、三个必须知道的坑

### 坑 1：所有 model 都要 import（`alembic/env.py` 里）

少 import 一张表，autogenerate 就会认为「这张表不该存在」，生成 `DROP TABLE`。
本项目 `env.py` 顶部已经把 6 个 model 文件全 import 了，**新增 model 时记得加一行**。

### 坑 2：autogenerate 只是草稿，必须人工看

它不保证能跑通、也不保证符合你的意图。本项目基线迁移就踩过：

```
ERROR 1553: Cannot drop index 'idx_order_item_order_id':
            needed in a foreign key constraint
```

原因是 autogenerate 的 `downgrade()` 会「先 drop_index 再 drop_table」，
而 MySQL 不允许删掉被外键依赖的索引。修法：**降级时只删表**（索引会跟着表一起消失），
按外键依赖倒序删：`order_item → cart → favorite → order → address → user_token → product → category → user`。

```

## 五、环境变量覆盖连接串（在测试库上试迁移）

```powershell
$env:ALEMBIC_DATABASE_URL = "mysql+aiomysql://root:密码@127.0.0.1:3306/test_db?charset=utf8mb4"
.\.venv\Scripts\python.exe -m alembic upgrade head

# 用完记得清掉，否则会一直连测试库
Remove-Item Env:\ALEMBIC_DATABASE_URL
```

## 六、本项目的现状

| 项 | 状态 |
|---|---|
| 迁移目录 | `alembic/` |
| 配置文件 | `alembic.ini`（连接串**不写在这里**，由 `env.py` 从 `.env` 读） |
| 基线版本 | `0e514502488a`（9 张表全量建表） |
| 真实库状态 | 已 `stamp` 到基线，`alembic check` 显示与模型一致 |
| 版本表 | `alembic_version`（Alembic 自己维护，不要手动改） |

## 七、如果要给队友/部署环境初始化

```powershell
# 空库（已建 ecom_app 但没表）
alembic upgrade head

# 已有表的老库（第一次接入 Alembic）
alembic stamp head
```

区别：`upgrade` 会**执行建表 SQL**，`stamp` 只**记录版本号**。
