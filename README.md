# 智能商城（电商后端 + Web 前端）

> 一个**从零手写**的电商系统学习项目：FastAPI + MySQL 异步后端，配一个 Vue3 的拼多多风格前端。
> 目标是把「接口设计 / 数据库设计 / 鉴权 / 事务」这些后端基础用真实的业务场景跑一遍，**不是生产级项目**。

---

## 目录

1. [项目简介](#1-项目简介)
2. [技术栈](#2-技术栈)
3. [环境要求](#3-环境要求)
4. [快速启动](#4-快速启动)
5. [数据库说明](#5-数据库说明)
6. [项目目录结构](#6-项目目录结构)
7. [接口文档访问地址](#7-接口文档访问地址)
8. [开发规范](#8-开发规范)
9. [常见问题 FAQ](#9-常见问题-faq)
10. [作者 / 更新说明](#10-作者--更新说明)

---

## 1. 项目简介

一个可以直接点着玩的电商站点：注册登录 → 逛商品 → 搜/筛/排序 → 看详情 → 收藏 → 加购物车 → 管理收货地址。

**做这个项目的目的是练习这些后端基本功和agent学习：**

| 练的东西 | 在本项目里的落点 |
|---|---|
| 统一的响应格式与错误处理 | `{code, message, data}`，HTTP 状态码 == code，全局异常处理器 |
| 分层架构 | `models` → `schemas` → `crud` → `routers`，一层只干一件事 |
| 异步 SQLAlchemy 2.0 | `AsyncSession` + `aiomysql`，`get_db` 统一管事务 |
| 鉴权 | 数据库 token 表 + **HttpOnly Cookie**，单设备登录 |
| 数据库设计 | 7 张表、联合唯一索引、CHECK 约束、外键级联、地址拆字段 |
| 前端对接 | Vue3 + 原生 fetch，Cookie 自动携带，401 统一跳登录 |

### 1.1 已实现的功能

**后端（24 个接口，全部可用）**

| 模块 | 功能 | 状态 |
|---|---|---|
| 用户 | 注册 / 登录 / 登出 / 查信息 / 改信息 / 改密码 | ✅ |
| 用户 | HttpOnly Cookie 鉴权、**单设备登录**（新登录踢掉旧设备） | ✅ |
| 分类 | 分类列表（带在架商品数） | ✅ |
| 商品 | 列表（分类筛选 + 关键字搜索 + 3 种排序 + 分页） | ✅ |
| 商品 | 详情（**需登录**：价格、库存、完整参数） | ✅ |
| 收藏 | 添加 / 取消 / 列表 / 是否已收藏 | ✅ |
| 购物车 | 添加 / 列表 / 改数量 / 改勾选 / 批量删除 / 清空 | ✅ |
| 收货地址 | 新增 / 列表 / 修改 / 删除（物理删除）/ 设为默认 | ✅ |
| 系统 | 健康检查（服务 + 数据库 + 表清单） | ✅ |

**前端（Vue3 + Vite） ⏳**

| 页面 | 内容 | 状态 |
|---|---|---|
| 首页 | 搜索框 + 分类导航 + 排序 + 商品瀑布流 + 触底加载 | ✅ |
| 商品详情 | 独立页 + 左上返回 + 收藏 + 加购 | ✅ |
| 登录 / 注册 | 独立页，Cookie 登录态 | ✅ |
| 我的 | 资料卡片、改昵称/邮箱/手机、改密码、退出 | ✅ |
| 收藏 | 收藏列表 + 取消收藏 | ✅ |
| 购物车 | 勾选 / 全选 / 加减数量 / 实时合计 / 批量删除 | ✅ |
| 收货地址 | 列表（默认高亮）+ 四行表单 + 省市区选择器 + **高德地图 POI 搜索选点** | ✅ |
| 订单 | 本地 localStorage 模拟（后端订单接口未做） | ⏳ 占位 |
| AI 助手 | 聊天界面占位（后端 AI 模块未做） | ⏳ 占位 |

**测试数据**：8 个分类 / **400 件商品** / 400 张本地生成的商品卡图。

### 1.2 未实现的功能（展望）

按建议的实现顺序排列，前两项是**最值得做**的：

| # | 待实现 | 说明 |
|---|---|---|
| 1 | **订单模块** | `order` / `order_item` 表 + `POST /api/order/create`。核心是**下单事务**：`SELECT ... FOR UPDATE` 锁行、`UPDATE ... WHERE stock >= ?` 扣库存（靠 rowcount 判断成功）、写订单明细、清购物车，全程一个事务。**订单里存收货地址快照，不存 address_id** |
| 2 | **前端接真实订单** | 现在"去结算"是浏览器本地存 localStorage |
| 3 | 商品检索增强 | `GET /api/product/search`：关键字（MySQL LIKE）+ 向量检索（Chroma）+ **RRF 融合排序**。目前搜索走的是商品列表的 `keyword` 参数，纯 LIKE |
| 4 | AI 购物助手 | 意图路由（该查库还是该查知识库）→ RAG 检索 → **SSE 流式输出**；配套 `knowledge_document` / `ai_conversation` / `ai_message` / `ai_usage` 表 |
| 5 | AI 调用配额 | 每用户每天 N 次，配套 `ai_usage` 表 |
| 6 | 列表分页 | 收藏、地址目前不分页（数据量小），购物车按需 |
| 7 | 数据库迁移 | 目前靠 `tools/init_db.py` 的 `create_all` + 手工 `ALTER`，没接 **Alembic** |
| 8 | 自动化测试 | 目前靠 curl 手测，没有 pytest |
| 9 | 部署 | 没有 Docker / Nginx / HTTPS；`Secure` cookie 只在本地关掉，上线必须开 |
| 10 | 商品评价 / 真实销量 | `sales` 是种子数据里的随机值，没有真实成交 |

> **明确不做**：支付接口。下单即视为已支付，订单状态里没有 `pending_payment`。

---

## 2. 技术栈

**后端**

| 类别 | 选型 | 说明 |
|---|---|---|
| 语言 | Python 3.11 | |
| Web 框架 | FastAPI | 自动生成 OpenAPI 文档 |
| ASGI 服务器 | Uvicorn | 开发用 `--reload` |
| ORM | SQLAlchemy 2.0（`asyncio`） | 用 `Mapped` / `mapped_column` 新式写法 |
| 数据库驱动 | aiomysql | 异步 MySQL 驱动 |
| 数据库 | MySQL 8.0 | `utf8mb4` |
| 数据校验 | Pydantic v2 | `alias` 做驼峰转换 |
| 密码哈希 | passlib 1.7.4 + bcrypt 4.0.1 | 版本必须锁死，见 FAQ |
| 配置 | pydantic-settings + python-dotenv | 读 `.env` |

**前端**

| 类别 | 选型 |
|---|---|
| 框架 | Vue 3（`<script setup>`） |
| 构建 | Vite 6 |
| 请求 | **原生 fetch**（没用 axios） |
| 状态 | 原生 `reactive` + 模块级 store（没用 Pinia / vue-router） |
| 地图 | **高德地图 JS API 2.0**（POI 搜索、逆地理编码、行政区划） |
| 样式 | 手写 CSS（拼多多风：红色渐变顶栏 + 红价 + 底部 4 tab） |

---

## 3. 环境要求

| 依赖 | 版本要求 | 本项目验证过的版本 |
|---|---|---|
| Python | ≥ 3.10（用了 `X | None` 语法） | **3.11.0** |
| MySQL | ≥ 8.0 | **8.0.24** |
| Node.js | ≥ 18 | **24.21.0** |
| npm | ≥ 9 | **11.19.0** |
| 操作系统 | Windows 10/11（命令按 PowerShell 写）、macOS / Linux 同理 | Windows 11 |
| 网络 | 装依赖时要能访问 PyPI（建议用清华源）；地图需要能访问 `webapi.amap.com` | |

> **不需要**：Redis、Docker、消息队列、Nginx。这个项目只要 Python + MySQL + Node 就能跑。

---

## 4. 快速启动

> 全程按顺序做，两步都起起来才算跑通：**后端 8000** + **前端 5173**。

### 4.1 准备数据库

MySQL 里建库（表由脚本自动建，不用手工写代码）：

```sql
CREATE DATABASE IF NOT EXISTS ecom_app
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;
```

### 4.2 配置 `.env`

```powershell
cd C:\Users\你的用户名\Desktop\ec_platform
copy .env.example .env
notepad .env
```

至少把数据库密码改成你自己的：

```ini
db_host=localhost
db_port=3306
db_user=root
db_password=你的密码
db_name=ecom_app
debug=true
```

> `debug=true` 会打印 SQL、异常里带 traceback。**上线必须改 false。**

### 4.3 创建虚拟环境 + 装依赖

```powershell
python -m venv .venv

# 用清华源，官方源在国内很慢
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4.4 建表 + 灌数据

```powershell
# 1) 建表（导入全部 model 后 create_all）
.\.venv\Scripts\python.exe tools\init_db.py

# 2) 生成 400 件商品（写 sql\seed_products.sql）
.\.venv\Scripts\python.exe tools\gen_products.py

# 3) 生成 400 张商品卡图（写到 web\images\gen\）
.\.venv\Scripts\python.exe tools\gen_images.py

# 4) 把商品导进库
$env:MYSQL_PWD="你的密码"
D:\mysql\bin\mysql.exe -u root ecom_app -e "source sql/seed_products.sql"
```

> 商品图是**用 Pillow 在本地画出来的卡片**（分类配色 + 商品名），不依赖外网图床，所以断网也能看到图。
> 想换真图：改 `product.cover` 字段指向任意 URL 即可。

### 4.5 启动后端

```powershell
cd C:\Users\你的用户名\Desktop\ec_platform
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

看到这两行就成功了：

```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

**先验一下**：打开 <http://127.0.0.1:8000/api/health>

```json
{ "code": 200, "message": "服务正常", "data": { "database": "connected", "tables": [...7 张表...] } }
```

`tables` 里少了哪张，就是那张表的 model 没被 `tools/init_db.py` 导入。

### 4.6 启动前端

**另开一个终端**：

```powershell
cd C:\Users\你的用户名\Desktop\ec_platform\frontend
npm install
npm run dev
```

```
  VITE v6.4.5  ready in 445 ms
  ➜  Local:   http://127.0.0.1:5173/
```

打开 **<http://127.0.0.1:5173>** 就能用了。

### 4.7 演示账号

```
用户名：zhangsan
密码：  123456
```

### 4.8 启动顺序（很重要）

```
MySQL（服务） → 后端 8000 → 前端 5173
```

前端一打开就立刻请求后端，所以**后端必须先起**。顺序反了浏览器控制台会刷：

```
ECONNREFUSED 127.0.0.1:8000
```

这表示"后端没起"，不是前端坏了。

---

## 5. 数据库说明

### 5.1 表清单（7 张，全部已建）

| # | 表名 | 说明 | 关键点 |
|---|---|---|---|
| 1 | `user` | 用户 | `username` / `phone` / `email` 三个唯一索引 |
| 2 | `user_token` | 登录令牌 | **`user_id` 唯一 → 单设备登录**；`expires_at` 有索引 |
| 3 | `category` | 商品分类 | 支持 `parent_id`，本项目只用一级 |
| 4 | `product` | 商品 | **单规格，不做 SKU**；`cover`/`images`/`specs` 存 JSON 字符串 |
| 5 | `favorite` | 收藏 | `(user_id, product_id)` 联合唯一 |
| 6 | `cart` | 购物车 | `(user_id, product_id)` 联合唯一；**不存价格**（实时读商品表） |
| 7 | `address` | 收货地址 | 省/市/区/详细**拆成 4 个字段** + 经纬度 + 默认标记 |

> 计划中还有 `order` / `order_item` / `knowledge_document` / `ai_conversation` / `ai_message` / `ai_usage`，属于 1.2 的待实现项。

### 5.2 索引一览

| 表 | 索引 | 类型 | 用途 |
|---|---|---|---|
| `user` | `username` / `phone` / `email` | 唯一 | 登录查重、防重复注册 |
| `user_token` | `token` | 唯一 | 每次请求按 token 查用户 |
| `user_token` | `uniq_user_token_user_id (user_id)` | **唯一** | 一个用户只能有一条有效 token（单设备） |
| `user_token` | `idx_user_token_expires_at` | 普通 | 清理过期 token |
| `category` | `idx_category_parent_id` / `idx_category_sort` | 普通 | 树形查询、排序 |
| `product` | `idx_product_category_id` / `status` / `sales` / `price` / `name` | 普通 | 分类筛选、排序、名称搜索 |
| `favorite` | `uniq_favorite_user_product` | **唯一** | 防重复收藏 |
| `favorite` | `idx_favorite_product_id` | 普通 | 统计某商品被收藏次数 |
| `cart` | `uniq_cart_user_product` | **唯一** | 同一商品不重复成行，重复加购累加数量 |
| `cart` | `idx_cart_product_id` | 普通 | 反查 |
| `address` | `idx_address_user_id` | 普通 | 查我的地址 |
| `address` | `idx_address_user_default` | 普通 | 默认地址排前面 |

**CHECK 约束**（脏数据在数据库层就拦掉，不用等前端发现显示错乱）：

```sql
ck_address_lng : lng IS NULL OR lng BETWEEN -180 AND 180
ck_address_lat : lat IS NULL OR lat BETWEEN -90 AND 90
```

### 5.3 几个关键设计决策

**① 金额用 `DECIMAL(10,2)`，单位是元**

`FLOAT` 有精度问题（`0.1 + 0.2 != 0.3`）。但**响应体里用 `float` 序列化**——因为 Pydantic v2 会把 `Decimal` 序列化成**字符串**，前端 `toFixed` 会炸。

**② 时间/布尔字段必须有 `server_default`**

`default=` 只是 Python 侧的默认值，**原生 SQL 插入不会生效**。本项目踩过这个坑：手工 `INSERT` 时报 `Field 'created_at' doesn't have a default value`。所以所有时间字段都写了 `server_default=func.now()`，`is_default` 写了 `server_default="0"`。

**③ 订单会存地址快照，不存 `address_id`**

用户随时会改地址、删地址，而历史订单必须保持下单当时的样子。所以 `order` 表里冗余存 `receiver_name` / `receiver_phone` / `receiver_address` 三个字段（待实现）。

> 对比：购物车存 `product_id`（要显示实时价格），订单存快照（要冻结价格和地址）。**该实时的实时，该冻结的冻结。**

**④ 地址删除用物理删除，不做软删除**

曾经设计过 `deleted_at` 软删除字段，后来砍掉了，原因：

- 订单存的是地址**快照**，不引用 `address.id`，删掉地址不影响历史订单——软删除最大的理由不成立
- 没有"回收站"产品需求，也没有恢复接口，字段等于白占
- 成本却是持续的：**每多一个查询就多一次"别忘了 `deleted_at IS NULL`"的机会**（本项目已经因为这个踩了两次坑）
- 表会无限膨胀，将来想加唯一索引还会被已删的行占着键

**⑤ 地址允许重复**

同一用户可以添加两条完全一样的地址，**故意不加唯一约束**（真实场景里"给同一个地址起不同收货人"是合理的）。只限制每个用户最多 **20 条**。

**⑥ 默认地址不加数据库唯一索引**

直觉上想加 `UNIQUE(user_id, is_default)`，但**不行**——每个用户的一堆非默认地址 `is_default` 全是 0，会互相冲突。
正确做法是在同一个事务里"先全部置 0，再把目标那条置 1"。

### 5.4 迁移说明

**本项目没有用 Alembic**，改表靠两条路：

```powershell
# 路线 A：表结构大改 → 直接重建（会丢数据）
.\.venv\Scripts\python.exe tools\init_db.py

# 路线 B：小改 → 手工 ALTER
$env:MYSQL_PWD="你的密码"
D:\mysql\bin\mysql.exe -u root ecom_app -e "ALTER TABLE address DROP COLUMN deleted_at;"
```

> ⚠️ `init_db.py` 用的是 `Base.metadata.create_all()`：**只会新建不存在的表，不会改已有表**。
> 所以加了字段之后必须手工 `ALTER`，否则报 `Unknown column`。

**商品 id 说明**：`AUTO_INCREMENT` 会跨多次导入持续增长（当前在 2001–2400 区间），重新灌数据前建议先 `TRUNCATE TABLE product`。

---

## 6. 项目目录结构

```
ec_platform/
├── .env / .env.example         配置（数据库密码、AI key）
├── requirements.txt            后端依赖
├── README.md
│
├── app/
│   ├── main.py                 入口：lifespan(探活) + 异常处理器 + 挂路由 + /images 静态目录
│   ├── config/
│   │   ├── app_conf.py         读 .env（pydantic-settings）
│   │   └── db_conf.py          异步引擎 + session 工厂 + get_db（事务边界在这里）
│   ├── models/                 SQLAlchemy 表定义
│   │   ├── base.py             全局唯一的 Base
│   │   ├── users.py            User / UserToken
│   │   ├── product.py          Category / Product
│   │   ├── favorite.py         Favorite
│   │   ├── cart.py             Cart
│   │   └── address.py          Address
│   ├── schemas/                Pydantic 请求体 / 响应体（snake_case 字段 + camelCase alias）
│   │   ├── users.py  product.py  category.py  favorite.py  cart.py  address.py
│   ├── crud/                   纯数据库操作（**只 flush，不 commit**）
│   │   ├── users.py  product.py  category.py  favorite.py  cart.py  address.py
│   ├── routers/                接口层（参数校验、鉴权、调 crud、包响应）
│   │   ├── user.py          6 个接口
│   │   ├── category.py      1 个
│   │   ├── product.py       2 个
│   │   ├── favorite.py      4 个
│   │   ├── cart.py          5 个
│   │   └── address.py       5 个
│   └── untils/                 工具（目录名是历史拼写，不是 utils）
│       ├── response.py         success_response / error_response / page_response
│       ├── exception.py        全局异常处理
│       ├── security.py         bcrypt 哈希 / 校验
│       └── auth.py             get_current_user（从 Cookie 取 token）
│
├── tools/
│   ├── init_db.py              建表（★ 必须 import 全部 model，否则表不会注册）
│   ├── gen_products.py         生成 400 件商品 → sql/seed_products.sql
│   ├── gen_images.py           用 Pillow 画 400 张商品卡图 → web/images/gen/
│   └── fetch_images.py 等      早期抓网图的脚本，已废弃但保留
│
├── sql/seed_products.sql       商品种子数据
├── web/images/                 商品图片（/images 静态目录指向这里）
│
└── frontend/                   Vue3 + Vite
    ├── index.html              ★ 引入高德 JS API（key + 安全密钥）
    ├── vite.config.js          /api 和 /images 代理到 8000
    └── src/
        ├── App.vue             tab 页 / 全屏页切换
        ├── api/index.js        fetch 封装 + 各模块 API
        ├── style.css           全部样式（拼多多风）
        ├── store/              ui / user / cart / fav / order / address
        ├── components/         SearchBar CategoryNav ProductCard TabBar
        │                       RegionPicker PoiPicker MapPicker
        ├── utils/amap.js       高德 SDK / 插件加载 + 逆地理编码
        └── views/              Home Detail Login Mine Fav Cart Order AddressList AddressEdit Ai
```


---

## 7. 接口文档访问地址

后端起来后：

| 地址 | 说明 |
|---|---|
| <http://127.0.0.1:8000/docs> | **Swagger UI**，可以直接点着调接口（推荐） |
| <http://127.0.0.1:8000/redoc> | ReDoc，只读的漂亮文档 |
| <http://127.0.0.1:8000/openapi.json> | OpenAPI 原始 JSON（可导入 Postman / Apifox） |
| <http://127.0.0.1:8000/api/health> | 健康检查（服务 + 数据库 + 表清单） |
| <http://127.0.0.1:8000/api> | 纯接口入口提示 |
| <http://127.0.0.1:5173> | 前端页面 |

> 在 `/docs` 里调需要登录的接口时，先在页面里用前端登录一次（或先调 `/api/user/login`），
> 因为鉴权走的是 **Cookie**，Swagger 会自动带上。

**接口分组（24 个）**：

```
用户    /api/user      register login logout info(×2) password     6 个
分类    /api/category  list                                        1 个
商品    /api/product   list detail                                  2 个
收藏    /api/favorite  add remove list check                        4 个
购物车  /api/cart      add list update remove clear                 5 个
地址    /api/address   create list update delete set-default        5 个
系统    /api/health                                                1 个
```

**统一响应格式**（HTTP 状态码 == code）：

```json
{ "code": 200, "message": "修改成功", "data": { "id": 6, "nickname": "张三" } }
{ "code": 400, "message": "原密码错误", "data": null }
```

分页响应：

```json
{ "code": 200, "message": "success",
  "data": { "list": [...], "total": 400, "hasMore": true, "page": 1, "pageSize": 12 } }
```

---

## 8. 开发规范

### 8.1 分层与调用顺序

```
routers  →  crud  →  models
   ↕
schemas（校验入参 / 序列化出参）
```

新增一个功能的固定套路：

```
1. models/xxx.py    加表和字段
2. schemas/xxx.py   加请求体 / 响应体
3. crud/xxx.py      写数据库操作
4. routers/xxx.py   写接口（校验、鉴权、包响应）
5. main.py          app.include_router(xxx_router.router)
6. tools/init_db.py import 这个 model（★ 漏了表就不会建）
```

### 8.2 事务边界

**`crud` 里只 `flush()`，绝不 `commit()`**。commit / rollback 由 `get_db` 统一负责：

```python
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()      # 接口正常返回 → 提交
        except Exception:
            await session.rollback()    # 抛异常 → 回滚
            raise
```

好处：一个接口里调多个 crud 函数，天然在一个事务里（比如"先清默认地址再新增地址"）。

### 8.3 命名与字段

| 位置 | 风格 | 例子 |
|---|---|---|
| Python 变量 / 字段 / 列名 | `snake_case` | `receiver_name` |
| JSON 入参 / 出参 | `camelCase`（靠 `alias`） | `receiverName` |
| 表名 | 单数小写 | `user` / `product` / `address` |
| 接口路径 | `/api/模块/动作` | `/api/address/set-default` |

```python
class AddressOutSchema(BaseModel):
    receiver_name: str = Field(alias="receiverName")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
```

> `model_config` 的 **C 要大写**。写成 `model_Config` 会被**静默忽略**，不报错但配置全不生效。

### 8.4 数据库约定

- 每张表都有 `created_at` / `updated_at`，且写 `server_default=func.now()`
- 金额 `DECIMAL(10,2)`，单位元
- 外键都带 `ondelete="CASCADE"`（用户注销，他的收藏/购物车/地址一起删）
- 需要"每人只有一条"的语义 → 用**唯一索引**（如 `user_token.user_id`）
- 需要"多行里只有一条特殊"的语义（如默认地址）→ **不能用唯一索引**，用事务里先清后设

### 8.5 接口层写法

```python
@router.post("/create", description="新增收货地址")
async def req_add_address(
    body: AddressCreateSchema,
    current: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    addr = await add_address_in_table(db, current.id, body)
    logger.info("用户 %s 新增地址 %s", current.username, addr.id)
    return success_response(message="添加地址成功", data=to_out(addr))
```

三条硬规矩：

1. **所有涉及用户数据的查询都必须带 `user_id == current.id`**，只按 id 查 = 能改别人的数据
2. `db.add()` / `db.delete()` 是**同步**方法，**不能 await**；`flush` / `commit` / `execute` / `refresh` 才要 await
3. `select()` 是同步构造语句，`await db.execute(stmt)` 才是执行；拿 ORM 对象用 `result.scalars().all()`，别用 `result.all()`（那是 Row）

### 8.6 前端约定

- 请求统一走 `src/api/index.js`，不直接在组件里写 `fetch`
- `credentials: 'include'` 必须带，否则 Cookie 不会发出去
- 只判断 `code`，不判断 HTTP 状态码（两者一致，但 code 更好写）
- 401 统一由 `setUnauthorizedHandler` 清登录态、收藏、购物车、地址缓存
- 页面状态全在 `store/ui.js`（`ui.page` 决定显示哪个全屏页）

---

## 9. 常见问题 FAQ


**Q1：后端启动报 `password authentication failed` 或 `Authentication plugin 'caching_sha2_password'`**

- 前一种：`.env` 里 `db_password` 写错了
- 后一种：缺 `cryptography`，`pip install cryptography` 即可（requirements.txt 里已经有）

**Q2：`passlib` 报 `module 'bcrypt' has no attribute '__about__'`**

bcrypt 版本太新。必须锁死：

```
passlib==1.7.4
bcrypt==4.0.1
```

**Q3：登录返回 200，但浏览器没收到 Cookie，下次请求还是 401**

经典坑：`response.set_cookie()` 加到了**注入的 `Response` 对象**上，但接口实际 `return success_response(...)`（一个 `JSONResponse`）。FastAPI 会原样发出这个新对象，注入对象上的 cookie 全丢。

```python
# ✅ 把 cookie 设在"真正返回的那个对象"上
resp = success_response(message="登录成功", data={...})
return _set_token_cookie(resp, token)
```

**Q4：`/api/health` 显示表少了一张**

`tools/init_db.py` 没 import 那个 model。`Base.metadata.create_all()` 只认识**已经被 import 过**的类。

**Q5：手工 `INSERT` 报 `Field 'created_at' doesn't have a default value`**

`default=` 只是 Python 侧默认值。手工 SQL 要靠 `server_default`，检查模型里有没有写 `server_default=func.now()`。

**Q6：`UPDATE` 报 `ERROR 1093 (HY000): You can't specify target table ...`**

MySQL 不允许在 `UPDATE` 的子查询里读同一张表。把子查询改成 `ORDER BY ... LIMIT 1` 的形式，或用临时表。

**Q7：商品图片是 404**

图片目录在 `web/images/`，`main.py` 把它挂成 `/images`。检查：

```powershell
Test-Path web\images\gen\1_00_0.jpg      # 图片在不在
```

不在就重跑 `python tools\gen_images.py`。

**Q18：地址页地图区域显示"地图加载失败"**

按顺序排查：

1. **Key 类型不对** —— 必须是「Web端 (JS API)」，不能用「Web服务」的 Key
2. **安全密钥没配对** —— 2021-12-02 之后申请的 Key 必须带 `securityJsCode`，且要在 SDK 脚本**之前**赋值
3. **域名白名单** —— 白名单留空 = 不限制；如果填了，要加 `127.0.0.1` 和 `localhost`
4. 浏览器装了广告拦截插件，把 `webapi.amap.com` 拦了

> 地图挂了**不影响功能**：省市区可以手动选，地址照样能保存（`lng/lat` 允许为空）。

**Q9：地址最多能加几个？**

每个用户 **20 个**。删掉一个就腾出一个名额（物理删除，删了不占额度）。



## 10. 作者 / 更新说明

**作者**：个人学习项目（[@lovewithxx](https://github.com/lovewithxx)）

**仓库**：<https://github.com/lovewithxx/ecommerce-backend>

**定位**：**不是生产级项目**。为了练习后端和agent基础而手写，刻意不引入 Redis / 消息队列 / 微服务，也不做支付。

### 更新记录

| 版本 | 内容 |
|---|---|
| v0.1 | 项目骨架：统一响应、全局异常、异步 DB 会话、健康检查 |
| v0.2 | 用户模块：注册 / 登录 / Cookie 鉴权 / 单设备登录 / 改资料 / 改密码 |
| v0.3 | 商品与分类：分类列表、商品列表（筛选 + 搜索 + 排序 + 分页）、商品详情 |
| v0.4 | 收藏模块：添加 / 取消 / 列表 / 是否已收藏 |
| v0.5 | 购物车模块：加购 / 改数量 / 改勾选 / 批量删除 / 清空 |
| v0.6 | 收货地址：表设计（省市区拆字段 + 经纬度 + CHECK 约束）、5 个接口、物理删除 |
| v0.7 | Vue3 前端：首页 / 详情 / 登录 / 我的 / 收藏 / 购物车 / **地址（高德地图 POI 搜索）** |
| 下一步 | **订单模块（下单事务 + 库存扣减 + 地址快照）** → 前端接真实订单 → 混合检索 → AI 助手 |

### 许可

学习项目，随便看随便抄，出问题概不负责。
