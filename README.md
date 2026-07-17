# BOM Impact Analyzer（BIA）

面向企业内部的 BOM 智能管理与元器件影响分析系统。当前仓库已按[架构设计](./BOM智能管理系统架构设计.md)完成 MVP 系统骨架，包含 Excel BOM 导入、结构化存储、IC 精确影响查询、基础风险分级及 Web 工作台。

## 当前能力

- FastAPI REST API 与自动生成的 OpenAPI 文档
- Product、Component、BomItem、ImpactAnalysis 核心数据模型
- `.xlsx` / `.xlsm` BOM 导入和常见中英文列名映射
- 同一产品再次导入时更新 BOM，元器件按型号复用
- 按 `part_number` 查询所有受影响产品
- Active / NRND / EOL 生命周期风险分级骨架
- 基于安全结构化条件的自然语言查询基础实现
- React + TypeScript 响应式管理工作台
- PostgreSQL + 前后端 Docker Compose 部署
- 本地开发默认使用 SQLite，降低启动门槛

## 目录结构

```text
.
├── backend/
│   ├── app/
│   │   ├── api/routes/       # HTTP 接口
│   │   ├── core/             # 配置与数据库连接
│   │   ├── models/           # SQLAlchemy 数据模型
│   │   ├── schemas/          # Pydantic 请求/响应模型
│   │   └── services/         # 导入、查询、分析业务逻辑
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── .env.example
```

## Docker 一键启动

需要 Docker Desktop 或 Docker Engine：

```bash
docker compose up --build
```

启动后访问：

- Web 工作台：<http://localhost:3000>
- API 文档：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/api/health>

## 本地开发

后端需要 Python 3.11+：

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

默认数据库为 `backend/data/bom.db`。如需 PostgreSQL，可复制 `.env.example` 到 `backend/.env` 并修改 `BIA_DATABASE_URL`。

前端需要 Node.js 20+：

```bash
cd frontend
npm install
npm run dev
```

开发服务器地址为 <http://localhost:5173>，`/api` 自动代理到本机 8000 端口。

## BOM 模板

至少需要一个型号列。当前可识别字段示例：

| 标准字段 | 可识别列名示例 |
| --- | --- |
| `part_number` | 型号、器件型号、编号、物料编号、物料编码、料号、Part Number、MPN、元件编号 |
| `quantity` | 数量、Qty、Quantity、用量 |
| `reference` | 位号、Reference、Ref、Designator |
| `manufacturer` | 制造商、Manufacturer、厂商、品牌 |
| `description` | 描述、器件描述、Description、名称 |
| `is_critical` | 关键器件、是否关键、is_critical |

产品型号可在上传时填写；留空则使用文件名。建议先用标准列名建立统一 BOM 模板。

导入时会扫描 Excel 中的全部工作表，并自动寻找前 40 行内的 BOM 表头。列名允许常见前后缀和轻微文字差异；没有 BOM 表头的说明页会跳过并在导入结果中提示。同一编号出现在多个工作表时按同一物料合并，并累加数量、合并位号。

## API 概览

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/health` | 服务健康检查 |
| POST | `/api/bom/upload` | 上传单个 BOM |
| POST | `/api/bom/batch-upload` | 上传多个 BOM |
| GET | `/api/impact/{part_number}` | 精确影响查询 |
| GET | `/api/impact/analyze/{part_number}` | 风险分析 |
| POST | `/api/query/natural` | 自然语言结构化查询 |

## 后续迭代

当前自然语言查询采用白名单字段与参数化 ORM 条件，尚未调用 LLM。下一阶段可接入受约束的实体提取器，但不应允许模型直接执行任意 SQL。其他计划包括 Alembic 正式迁移、Celery/Redis 异步批量导入、生命周期数据源、权限审计和报表导出。
