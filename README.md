# 简易商城 · 用户模块

FastAPI + MySQL 异步。目前完成：**注册 / 登录 / 退出 / 查看信息 / 修改信息 / 修改密码** + 一个可点击的前端。

---

##运行

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

## 前端（先弄个最小可演示案例）

单个 HTML 文件（web/index.html），FastAPI 直接托管，没有 npm、没有打包。

底部 7 个标签页：

| 标签 | 内容 | 数据来源 |
| 首页 | 搜索框 + 商品网格 |商品数据 |
| 分类 | 8 个分类，点击筛选 | 对应类型的数据 |
| 收藏 | 收藏的商品 | 浏览器 localStorage |
| 购物车 | 加减数量、合计、去结算 | 浏览器 localStorage |
| 订单 | 下单记录、取消 | 浏览器 localStorage |
| **我的** | **登录 / 注册 / 资料 / 改信息 / 改密码** | **真接口（后端）** |
| AI 助手 | 聊天界面占位 | |


---

## 后端

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
├── requestment.txt         依赖清单（建议改 requirements.txt）
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




---

## 下一步计划


| **第一段** | 商品 / 分类 / 收藏 / 购物车 / 订单（表和接口） |
| **第二段** | AI 助手：意图路由 + RAG + 流式输出 |
| **第三段** | vue前端 |

