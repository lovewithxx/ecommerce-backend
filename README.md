# 简易商城 · 用户模块

FastAPI + MySQL 异步。目前完成：**注册 / 登录 / 退出 / 查看信息 / 修改信息 / 修改密码** + 一个可点击的前端。

---

## 怎么跑

```powershell
cd C:\Users\lyt2001\Desktop\ec_platform
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

打开 **http://127.0.0.1:8000/**

**演示账号**：`zhangsan` / `123456`

其他地址：
- `http://127.0.0.1:8000/docs` 接口文档
- `http://127.0.0.1:8000/api/health` 健康检查

---

## 前端有什么

单个 HTML 文件（`web/index.html`），FastAPI 直接托管，没有 npm、没有打包。

底部 7 个标签页：

| 标签 | 内容 | 数据来源 |
|---|---|---|
| 首页 | 搜索框 + 商品网格 | 假数据（前端写死 23 个商品） |
| 分类 | 8 个分类，点击筛选 | 假数据 |
| 收藏 | 收藏的商品 | 浏览器 localStorage |
| 购物车 | 加减数量、合计、去结算 | 浏览器 localStorage |
| 订单 | 下单记录、取消 | 浏览器 localStorage |
| **我的** | **登录 / 注册 / 资料 / 改信息 / 改密码** | **真接口（后端）** |
| AI 助手 | 聊天界面占位 | 第二阶段做 |

**为什么要说清"假数据"**：商品、购物车、订单的后端接口还没写（那是第二阶段）。
所以这些页面用的是浏览器本地数据，刷新不丢但换设备就没了。
只有「我的」这一页真的在调后端。

---

## 后端有什么

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/api/health` | — | 服务 + 数据库 + 表清单 |
| POST | `/api/user/register` | — | 注册（成功即登录） |
| POST | `/api/user/login` | — | 登录 |
| POST | `/api/user/logout` | 🔒 | 退出（删掉这个用户唯一的 token） |
| GET | `/api/user/info` | 🔒 | 当前用户信息 |
| PUT | `/api/user/info` | 🔒 | 修改信息（只改传了的字段） |
| PUT | `/api/user/password` | 🔒 | 改密码（踢掉所有设备） |

响应格式统一，**HTTP 状态码 == code**：

```json
{ "code": 200, "message": "修改成功", "data": { ... } }
{ "code": 400, "message": "原密码错误", "data": null }
```

---

## 目录结构

```
ec_platform/
├── .env                    配置（数据库密码等）
├── requestment.txt         依赖清单（文件名拼错了，建议改 requirements.txt）
├── app/
│   ├── main.py             入口：生命周期 + 异常处理器 + 静态页
│   ├── config/
│   │   ├── app_conf.py     读 .env
│   │   └── db_conf.py      引擎 + get_db
│   ├── models/
│   │   ├── base.py         Base（全局唯一）
│   │   └── users.py        User / UserToken
│   ├── schemas/users.py    请求体 / 响应体
│   ├── crud/users.py       数据库操作
│   ├── routers/user.py     6 个接口
│   └── untils/
│       ├── response.py     统一响应
│       ├── exception.py    全局异常处理
│       ├── security.py     bcrypt
│       └── auth.py         get_current_user
├── web/index.html          前端
└── tools/init_db.py        建表脚本
```

---

## 四个关键点（面试会问）

**① crud 只 flush，不 commit**

注册 = 建用户 + 发 token，两步必须同生共死。提交统一交给 `get_db`，
任何一步失败整体回滚，不会留下"有用户但没 token"的脏数据。

**② 请求体就是白名单**

`UserUpdateRequest` 里只有 nickname/avatar/gender/bio/phone/email。
body 里塞 `username` / `status` / `password` 会被 Pydantic 直接丢弃，
所以越权字段改不进去。**靠"不写进 schema"挡，比写 if 判断可靠。**

**③ 单设备登录：一个用户只有一条 token**

`user_token.user_id` 上是**唯一索引**，所以登录时不是"新增一条"，而是"更新那一条"。

```python
row = result.scalars().first()
if row is None:
    db.add(UserToken(user_id=user_id, token=token, expires_at=expires_at))
else:
    row.token = token          # 覆盖旧 token
    row.expires_at = expires_at
```

效果：设备 A 先登录拿到 token1，设备 B 再登录拿到 token2，
**设备 A 的 token1 立刻失效**（库里已经没有这个字符串了），下次请求直接 401。

好处是逻辑简单、永远只有一条；代价是手机和电脑不能同时在线。

**④ 改密码要删 token**

```python
await crud_users.revoke_all_tokens(db, current.id)
```

改密码的语义是"我不再信任已登录的会话"。单设备下也就一条，删掉即可。

**⑤ 登录失败不区分原因**

统一返回"用户名或密码错误"。返"该用户不存在"会告诉攻击者哪些用户名有效，方便撞库。

**⑥ 认证靠 HttpOnly Cookie，前端拿不到 token**

登录/注册成功后，后端把 token 写进 Cookie，**响应体里不返回 token**：

```
set-cookie: access_token=...; HttpOnly; Max-Age=604800; Path=/; SameSite=lax
```

- `HttpOnly`：JS 读不到，XSS 偷不走
- `SameSite=lax`：跨站的 POST/PUT 不携带，挡住 CSRF
- `secure=False`：本地 HTTP 必须 False；**上线 HTTPS 必须改 True**

前端只需要在 fetch 里加 `credentials: "include"`，浏览器就会自动带上 cookie。
判断"有没有登录"的做法是调 `GET /api/user/info`：200 已登录，401 未登录。

**⑦ ★ 一个很容易踩的坑：Set-Cookie 加到了"错误的 Response"上 ★**

FastAPI 里注入 `response: Response`，只在接口**返回普通数据（dict / Pydantic 模型）**时生效。

本项目接口是 `return success_response(...)`，返回的是 `JSONResponse` 对象，
FastAPI 会原样把它发出去，**注入对象上设的 Cookie 会全部丢失**。

表现：登录接口返回 200，但浏览器没收到 `Set-Cookie`，下次请求仍然 401 —— 而且日志里看不出任何错误。

正确写法是**先建响应，再把 Cookie 设在它身上**：

```python
resp = success_response(message="登录成功", data={...})
return _set_token_cookie(resp, token)
```

同理，退出登录和改密码都用 `return _clear_token_cookie(resp)`。

---

## 数据库

只有一个库 `ecom_app`，两张表 `user`、`user_token`。

重建表：

```powershell
.\.venv\Scripts\python.exe -m tools.init_db
```

---

## 下一步

| 阶段 | 内容 |
|---|---|
| **第二段** | 商品 / 分类 / 收藏 / 购物车 / 订单（表和接口） |
| **第三段** | AI 助手：意图路由 + RAG + 流式输出 |

商品测试数据已经准备好：`DS-Workspace\电商数据\` 里 4 个 SQL 文件，共 120 个商品。
