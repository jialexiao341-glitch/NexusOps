# NexusOps

## 后端启动

安装 Docker Desktop 并启动 Docker 引擎，在项目根目录运行 `docker compose up --build`。启动后访问 http://localhost:8887/docs，健康检查为 `/health`。数据库迁移需手动执行；MySQL 数据保存在 Docker volume 中。Compose 中的密码仅供本地开发。

本地开发：进入 `backend`，复制 `env/.env.dev.example` 为 `env/.env.dev` 并填写配置，运行 `uv sync`，然后在 `backend` 目录使用 `uv run main.py --env=dev` 启动开发环境；生产环境填写 `env/.env.prod` 后使用 `uv run python -m app --env prod --host 0.0.0.0`。迁移使用 `NEXUSOPS_ENV` 选择环境（PowerShell 示例：`$env:NEXUSOPS_ENV="dev"; uv run alembic upgrade head`），执行前须确认目标数据库和迁移内容。进程环境变量优先于环境文件。运行测试：`uv run pytest`。

商户、商品提供创建、分页列表、详情、部分更新与删除。商户有商品时禁止删除。当前 CRUD 尚未接入认证、租户隔离及审计，仅用于本地开发，不能暴露到公网或用于真实数据。健康检查仅表示 API 进程存活，不检查依赖服务。

前端参考源码位于 `references/`，不属于项目应用代码。

## 环境与数据库

配置统一位于 `backend/env/`，`NEXUSOPS_ENV` 可取 `dev`、`test`、`prod`，进程环境变量优先。开发库为 `nexusops`，测试库为 `nexusops_test`；生产配置须在实际部署时填写。环境文件含凭据，不纳入版本控制。

现有 `uv run pytest` 使用独立的内存 SQLite，不会清空 MySQL。需要执行 MySQL 测试或迁移时，明确选择测试环境：PowerShell 中执行 `$env:NEXUSOPS_ENV="test"`；执行任何破坏性操作前检查连接目标。迁移前须确认数据库模型；不要把未确认的旧迁移应用到任何环境。

## 开发环境模拟登录

开发和测试环境可调用 `POST /api/v1/auth/codes`，传入手机号及 `register` 或 `login` 用途，在响应中获取模拟验证码；不会发送真实短信。验证码只保存在当前进程内，重启失效，不支持多进程共享，生产环境禁用模拟发送。随后可通过 `/api/v1/auth/register`、`/api/v1/auth/login` 或 `/api/v1/auth/login/sms` 完成注册和登录。`/docs` 提供交互式接口文档。

JWT_SECRET 必须使用足够长的随机值；开发及测试环境各自使用独立密钥。当前刷新令牌为无状态令牌，在有效期内不能主动撤销，正式部署前需实现令牌撤销和登录频率限制。商户和商品接口尚未接入鉴权。

## 管理端前端

启动后端后，在 `frontend/apps/management-web` 运行 `npm install`，然后在 `frontend` 运行 `npm run dev`，浏览器打开 http://127.0.0.1:3001。开发服务器将 `/api` 请求代理到 `127.0.0.1:8887`。页面提供账号登录、模拟验证码登录和注册；当前登录成功页面仅用于联调，不代表已获得管理权限。




## 分类、规格与库存

管理台的“分类与规格”支持按商户管理商品分类、按商品管理规格及可售库存；商品编辑可填写所属分类编号。原商品价格继续对应编号最小的默认规格，默认规格不能单独删除。分类与商品须属于同一商户，有商品的分类不能删除。列表一次最多展示 100 个分类。

库存设置为可售数量的绝对值，预留数量不通过此接口修改；交易并发扣减等逻辑尚未实现。以上接口尚未接入鉴权和租户隔离，仅供本地开发。现有数据库须已应用包含分类、SKU、库存表的迁移，迁移前请确认目标数据库及迁移内容。
