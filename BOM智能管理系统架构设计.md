
```markdown
# BOM智能管理系统——产品架构设计文档


## 一、系统概述

### 1.1 业务背景

企业在日常研发和生产中积累了数千份Excel格式的BOM（物料清单）文件，分散在不同产品的文件夹中。当某颗IC芯片停产（EOL，End of Life）时，采购和研发团队需要快速定位：这颗IC被用在了哪些产品的BOM中？这些产品是否面临停产风险？

传统做法是人工打开一个个Excel文件搜索，效率极低且容易遗漏。本系统旨在通过**结构化数据管理 + 大模型智能查询**的方式，彻底解决这一问题。

### 1.2 核心功能

| 功能模块 | 说明 |
|---------|------|
| **BOM数据录入** | 批量上传数千份Excel文件，自动解析并存入后端数据库 |
| **IC影响查询** | 输入IC型号（如"STM32F103C8T6"），系统返回所有使用了该IC的产品型号列表 |
| **大模型智能查询** | 支持自然语言提问（如"哪些产品的BOM中包含TI的电源管理芯片？"），由LLM理解意图并返回结果 |
| **停产影响分析** | 结合IC生命周期状态，自动评估停产影响的产品的范围与风险等级 |

### 1.3 设计原则

- **结构化是AI的基础**：AI在没有结构化上下文数据的情况下，不过是猜测而已。因此，系统首先要把Excel数据转化为结构化的、可查询的关系型数据。
- **精确查询优先**：对于"某IC影响哪些产品"这类精确查询，采用SQL精确检索；对于模糊/语义查询，采用LLM辅助。
- **大模型作为"翻译官"** ：大模型负责将自然语言转化为可执行的查询或分析任务，而非直接"编造"答案。


## 二、总体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              前端展示层                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  BOM上传界面 │  │  IC精确查询 │  │  自然语言   │  │  影响分析报告   │  │
│  │  (批量导入)  │  │  (型号搜索) │  │  对话查询   │  │  (可视化展示)   │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            API网关层                                        │
│           RESTful API  │  WebSocket  │  统一鉴权  │  限流/日志             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           业务逻辑层                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  BOM导入    │  │  IC-产品    │  │  自然语言   │  │  影响分析引擎   │  │
│  │  服务       │  │  关联服务   │  │  查询服务   │  │  (风险评估)     │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LLM集成层                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                   大模型API（OpenAI / 国产大模型）                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐ │  │
│  │  │ Text-to-SQL │  │  实体识别   │  │  自然语言→查询条件转换      │ │  │
│  │  │  Agent      │  │  (IC型号)   │  │  (意图理解 + 参数抽取)      │ │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────┘ │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           数据层                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌───────────────────┐  │
│  │   关系型数据库       │  │   向量数据库         │  │   文件存储        │  │
│  │  (PostgreSQL)       │  │  (PgVector/Pinecone) │  │  (原始Excel存档)  │  │
│  │  - Products表       │  │  - IC描述向量        │  │                   │  │
│  │  - Components表     │  │  - BOM语义向量       │  │                   │  │
│  │  - BOM_Items表      │  │                      │  │                   │  │
│  └─────────────────────┘  └─────────────────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```


## 三、数据模型设计

### 3.1 核心实体关系图

```
┌──────────────┐          ┌──────────────┐          ┌──────────────┐
│   Product    │          │   BOM_Item   │          │  Component   │
│  (产品表)    │1───────┏━┷━━━━━━━━━━━━┓│N───────1│  (元器件表)   │
├──────────────┤         │              │          ├──────────────┤
│ id           │         │ id           │          │ id           │
│ product_name │         │ product_id   │          │ component_   │
│ product_code │         │ component_id │          │   name       │
│ description  │         │ quantity     │          │ manufacturer │
│ created_at   │         │ reference    │          │ part_number  │
│ updated_at   │         │ (位号)       │          │ description  │
└──────────────┘         │ is_critical  │          │ lifecycle    │
          │               └──────────────┘          │ (Active/EOL) │
          │                                         │ datasheet_url│
          │                                         └──────────────┘
          │
          ▼
┌──────────────┐
│ ImpactAnalysis│
│ (影响分析记录)│
├──────────────┤
│ id           │
│ component_id │
│ affected_    │
│   product_ids│
│ risk_level   │
│ analyzed_at  │
└──────────────┘
```

### 3.2 表结构详细设计

**Products（产品表）**
```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    product_code VARCHAR(100) UNIQUE NOT NULL,  -- 产品型号，如 "PSU-100W-V2"
    product_name VARCHAR(200) NOT NULL,
    description TEXT,
    file_path VARCHAR(500),                     -- 原始Excel文件路径
    uploaded_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Components（元器件表）**
```sql
CREATE TABLE components (
    id SERIAL PRIMARY KEY,
    part_number VARCHAR(200) UNIQUE NOT NULL,   -- IC型号，如 "STM32F103C8T6"
    manufacturer VARCHAR(100),
    description TEXT,
    lifecycle_status VARCHAR(20) DEFAULT 'Active', -- Active / EOL / NRND
    datasheet_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**BOM_Items（BOM明细表——核心关联表）**
```sql
CREATE TABLE bom_items (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    component_id INTEGER REFERENCES components(id) ON DELETE CASCADE,
    quantity INTEGER DEFAULT 1,
    reference VARCHAR(200),                     -- 位号，如 "U1, U2"
    is_critical BOOLEAN DEFAULT FALSE,          -- 是否关键器件
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(product_id, component_id)            -- 防止重复
);
```

**Impact_Analysis（影响分析记录表）**
```sql
CREATE TABLE impact_analysis (
    id SERIAL PRIMARY KEY,
    component_id INTEGER REFERENCES components(id),
    affected_product_ids INTEGER[],             -- 受影响的产品ID列表
    risk_level VARCHAR(20),                     -- HIGH / MEDIUM / LOW
    analysis_detail JSONB,                      -- 详细分析结果
    analyzed_at TIMESTAMP DEFAULT NOW()
);
```

### 3.3 索引设计

```sql
-- 加速IC型号查询
CREATE INDEX idx_components_part_number ON components(part_number);

-- 加速按产品查BOM
CREATE INDEX idx_bom_items_product_id ON bom_items(product_id);

-- 加速按元器件查产品（核心查询）
CREATE INDEX idx_bom_items_component_id ON bom_items(component_id);

-- 支持模糊搜索
CREATE INDEX idx_components_part_number_trgm ON components 
    USING GIN (part_number gin_trgm_ops);
```


## 四、数据导入模块设计

### 4.1 导入流程

```
┌────────────────┐
│  用户上传Excel  │
│  (批量/单文件)  │
└───────┬────────┘
        ▼
┌────────────────┐
│  文件校验      │
│  (格式/大小)   │
└───────┬────────┘
        ▼
┌────────────────┐
│  Excel解析     │
│  (pandas/openpyxl)│
└───────┬────────┘
        ▼
┌────────────────┐
│  数据标准化    │  ← 大模型辅助：识别列名、统一格式
│  (列映射/清洗) │
└───────┬────────┘
        ▼
┌────────────────┐
│  数据入库      │
│  (Product/     │
│   Component/   │
│   BOM_Item)    │
└───────┬────────┘
        ▼
┌────────────────┐
│  生成向量索引  │  ← 为IC描述生成向量，支持语义搜索
└────────────────┘
```

### 4.2 列映射策略

不同Excel文件的列名可能不一致（如"型号" vs "Part Number" vs "器件编号"）。系统采用**三层映射机制**：

1. **预定义映射表**：维护常见列名到标准字段的映射
2. **大模型辅助识别**：对于未知列名，调用LLM判断其语义含义
3. **人工确认**：对于置信度低的映射，提示用户确认

```python
# 列映射示例
COLUMN_MAPPING = {
    # 元器件型号字段
    "part_number": ["型号", "器件型号", "Part Number", "MPN", "Mfr Part #", "元件编号"],
    # 数量字段
    "quantity": ["数量", "Qty", "Quantity", "用量"],
    # 位号字段
    "reference": ["位号", "Reference", "Ref", "Designator"],
    # 制造商字段
    "manufacturer": ["制造商", "Manufacturer", "厂商", "品牌"],
}
```

### 4.3 Excel解析实现要点

```python
import pandas as pd
from openpyxl import load_workbook

def parse_bom_excel(file_path: str) -> dict:
    """
    解析BOM Excel文件，返回产品信息和BOM明细
    """
    # 1. 读取Excel
    df = pd.read_excel(file_path)
    
    # 2. 提取产品信息（从文件名或特定单元格）
    product_code = extract_product_code(file_path)
    
    # 3. 列名标准化
    df = normalize_columns(df)
    
    # 4. 提取元器件列表
    components = []
    for _, row in df.iterrows():
        comp = {
            "part_number": row.get("part_number"),
            "quantity": row.get("quantity", 1),
            "reference": row.get("reference", ""),
            "manufacturer": row.get("manufacturer", ""),
        }
        components.append(comp)
    
    return {
        "product_code": product_code,
        "components": components
    }
```


## 五、LLM集成层设计

### 5.1 设计思路

大模型在本系统中扮演**"智能查询翻译官"** 的角色，而非答案生成器。核心逻辑是：

1. 用户输入自然语言查询
2. LLM理解意图，提取关键实体（IC型号、制造商、条件等）
3. LLM将意图转化为结构化的查询条件或SQL
4. 系统执行精确查询，返回确定性的结果

这样可以避免大模型"幻觉"导致的错误答案。

### 5.2 三种查询模式

| 模式 | 触发条件 | 处理方式 | 示例 |
|------|---------|---------|------|
| **精确查询** | 用户输入明确的IC型号 | 直接SQL查询 | "STM32F103C8T6影响哪些产品？" |
| **模糊查询** | 用户输入部分型号或通配符 | SQL LIKE + 全文检索 | "所有STM32F1系列的IC" |
| **自然语言查询** | 用户输入描述性语句 | LLM → 结构化条件 → SQL | "哪些产品的BOM中有TI的电源芯片？" |

### 5.3 Text-to-SQL实现

采用LangChain的SQL Agent实现自然语言到SQL的转换：

```python
from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain_openai import ChatOpenAI

def setup_sql_agent():
    """初始化SQL Agent"""
    db = SQLDatabase.from_uri("postgresql://user:pass@localhost/bom_db")
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    
    agent = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=True,
        handle_parsing_errors=True
    )
    return agent

def natural_language_query(question: str):
    """自然语言查询入口"""
    agent = setup_sql_agent()
    
    # 添加系统提示，约束查询范围
    prompt = f"""
    你是一个BOM数据库查询助手。请根据以下问题生成SQL查询：
    问题：{question}
    
    注意事项：
    1. 只查询BOM相关的表（products, components, bom_items）
    2. 返回结果必须是确定性的数据，不要编造
    3. 如果问题涉及IC型号，优先在components.part_number字段中匹配
    """
    
    result = agent.invoke({"input": prompt})
    return result
```

### 5.4 实体识别

对于"TI的电源管理芯片"这类查询，需要先识别：
- **制造商**："TI" → Texas Instruments
- **器件类型**："电源管理芯片" → 在description中匹配

```python
def extract_entities_with_llm(query: str) -> dict:
    """
    使用LLM从自然语言中提取查询实体
    """
    prompt = f"""
    从以下查询中提取关键实体：
    查询：{query}
    
    输出JSON格式：
    {{
        "manufacturer": "制造商名称（如有）",
        "part_number": "具体型号（如有）",
        "part_type": "器件类型（如有）",
        "keywords": ["关键词列表"]
    }}
    """
    # 调用LLM API获取结构化输出
    response = llm.invoke(prompt)
    return json.loads(response.content)
```

### 5.5 大模型API选型建议

| 方案 | 优势 | 适用场景 |
|------|------|---------|
| **OpenAI GPT-4** | 能力最强，Text-to-SQL准确率高 | 对准确性要求高的场景 |
| **国产大模型（通义千问/文心一言/DeepSeek）** | 数据不出境，成本更低 | 数据敏感型场景 |
| **开源模型本地部署（Qwen/Llama）** | 完全自主可控 | 私有化部署需求 |


## 六、核心查询流程

### 6.1 IC影响产品查询（核心功能）

```
┌─────────────────────────────────────────────────────────────────┐
│ 用户输入："STM32F103C8T6"                                       │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: 实体识别                                                │
│ → 识别为IC型号: STM32F103C8T6                                  │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: 精确查询（SQL）                                         │
│ SELECT p.product_code, p.product_name                          │
│ FROM products p                                                │
│ JOIN bom_items bi ON p.id = bi.product_id                      │
│ JOIN components c ON bi.component_id = c.id                    │
│ WHERE c.part_number = 'STM32F103C8T6'                          │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: 返回结果                                                │
│ → 产品1: PSU-100W-V2                                           │
│ → 产品2: MOTOR-DRIVER-V3                                       │
│ → 产品3: SENSOR-HUB-V1                                         │
│ → 共3个产品受影响                                               │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 自然语言查询流程

```
┌─────────────────────────────────────────────────────────────────┐
│ 用户输入："哪些产品的BOM中包含了TI的电源管理芯片？"              │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: LLM意图理解                                             │
│ → 制造商: TI (Texas Instruments)                               │
│ → 器件类型: 电源管理芯片 (power management IC)                   │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: 生成SQL                                                 │
│ SELECT DISTINCT p.product_code, p.product_name                 │
│ FROM products p                                                │
│ JOIN bom_items bi ON p.id = bi.product_id                      │
│ JOIN components c ON bi.component_id = c.id                    │
│ WHERE c.manufacturer ILIKE '%TI%'                              │
│   AND c.description ILIKE '%power%management%'                 │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: 执行查询并返回结果                                       │
└─────────────────────────────────────────────────────────────────┘
```


## 七、技术栈推荐

### 7.1 后端

| 组件 | 推荐技术 | 说明 |
|------|---------|------|
| Web框架 | **FastAPI** (Python) | 高性能、自动生成API文档、异步支持 |
| 数据库 | **PostgreSQL** | 关系型数据存储，支持JSONB和全文检索 |
| 向量扩展 | **PgVector** | PostgreSQL的向量扩展，支持语义搜索 |
| ORM | **SQLAlchemy** | Python最成熟的ORM |
| Excel解析 | **pandas + openpyxl** | 成熟稳定的Excel处理方案 |
| LLM集成 | **LangChain** | 统一的LLM应用开发框架 |
| 任务队列 | **Celery + Redis** | 处理大批量BOM导入任务 |

### 7.2 前端

| 组件 | 推荐技术 | 说明 |
|------|---------|------|
| 框架 | **React / Vue 3** | 主流前端框架 |
| UI组件 | **Ant Design / Element Plus** | 企业级UI组件库 |
| 状态管理 | **Redux / Pinia** | 状态管理 |
| 图表 | **ECharts** | 影响分析可视化 |

### 7.3 部署

| 组件 | 推荐技术 | 说明 |
|------|---------|------|
| 容器化 | **Docker + Docker Compose** | 标准化部署 |
| 编排 | **Kubernetes**（可选） | 大规模部署 |
| 反向代理 | **Nginx** | 负载均衡+静态文件服务 |


## 八、API接口设计

### 8.1 核心接口

**1. BOM导入接口**
```
POST /api/bom/upload
Content-Type: multipart/form-data

Request:
  - file: Excel文件
  - product_code: 产品型号（可选，默认从文件名提取）

Response:
  {
    "success": true,
    "product_id": 123,
    "components_imported": 45,
    "duplicates_skipped": 2
  }
```

**2. 批量导入接口**
```
POST /api/bom/batch-upload
Content-Type: multipart/form-data

Request:
  - files: 多个Excel文件（zip或直接多文件）

Response:
  {
    "total": 100,
    "success": 95,
    "failed": 5,
    "failed_list": ["file1.xlsx", "file2.xlsx"]
  }
```

**3. IC影响查询接口（精确）**
```
GET /api/impact/{part_number}

Response:
  {
    "part_number": "STM32F103C8T6",
    "manufacturer": "STMicroelectronics",
    "lifecycle_status": "Active",
    "affected_products": [
      {
        "product_code": "PSU-100W-V2",
        "product_name": "100W电源模块",
        "quantity": 2,
        "reference": "U1, U3"
      }
    ],
    "total_affected": 3,
    "risk_level": "LOW"
  }
```

**4. 自然语言查询接口**
```
POST /api/query/natural
Content-Type: application/json

Request:
  {
    "question": "哪些产品的BOM中包含了TI的电源管理芯片？"
  }

Response:
  {
    "question": "哪些产品的BOM中包含了TI的电源管理芯片？",
    "interpreted_as": {
      "manufacturer": "TI",
      "part_type": "电源管理芯片"
    },
    "sql_used": "SELECT ...",
    "results": [...],
    "total": 12
  }
```

**5. 停产影响分析接口**
```
GET /api/impact/analyze/{part_number}

Response:
  {
    "part_number": "STM32F103C8T6",
    "lifecycle_status": "EOL",
    "affected_products": [...],
    "total_affected": 3,
    "risk_assessment": {
      "level": "HIGH",
      "reason": "该芯片已停产，影响3款主力产品，建议立即启动替代方案评估"
    },
    "recommendations": [
      "推荐替代型号：STM32F103CBT6",
      "建议联系原厂确认最后购买日期（LTB）"
    ]
  }
```


## 九、实施路线图

### 第一阶段：MVP（2-3周）
- [ ] 搭建PostgreSQL数据库，创建核心表结构
- [ ] 实现Excel单文件导入功能（pandas解析 + 入库）
- [ ] 实现IC精确查询接口（按part_number查产品）
- [ ] 提供简单的Web界面（上传 + 查询）

### 第二阶段：批量导入优化（1-2周）
- [ ] 实现批量上传功能（支持zip打包或文件夹扫描）
- [ ] 增加导入进度展示和错误日志
- [ ] 实现去重逻辑（同一产品多次导入自动更新）
- [ ] 增加列名智能映射（预定义映射表）

### 第三阶段：LLM集成（2-3周）
- [ ] 接入大模型API（OpenAI或国产模型）
- [ ] 实现Text-to-SQL自然语言查询
- [ ] 实现实体识别（从自然语言中提取IC型号、制造商等）
- [ ] 实现智能搜索建议（输入部分型号自动补全）

### 第四阶段：影响分析增强（1-2周）
- [ ] 集成IC生命周期数据（手动维护或对接第三方API）
- [ ] 实现停产影响自动评估和风险分级
- [ ] 生成影响分析报告（PDF/Excel导出）
- [ ] 增加邮件/企微通知（当检测到某IC停产时自动推送受影响产品列表）

### 第五阶段：生产就绪（1-2周）
- [ ] 完善权限管理和操作审计
- [ ] Docker容器化部署
- [ ] 性能测试和优化（索引、查询缓存）
- [ ] 编写用户手册和运维文档


## 十、注意事项与最佳实践

### 10.1 数据质量

Excel文件质量参差不齐是最大的挑战。建议：
- 建立**BOM模板标准**，引导用户按标准格式填写
- 对历史数据采用**"先解析、后人审"** 的策略，由LLM辅助标注可疑数据
- 建立**数据质量看板**，展示各产品的BOM完整度

### 10.2 LLM幻觉防控

在结构化数据场景中，LLM的"幻觉"代价很高。建议：
- **LLM只做"翻译"不做"生成"** ：LLM将自然语言转为SQL，由数据库执行精确查询
- 对LLM输出的SQL进行**语法校验和安全审查**（防止SQL注入）
- 在返回结果时**标注数据来源**，增强可信度

### 10.3 性能优化

- 对`bom_items`表的`component_id`和`product_id`建立**复合索引**
- 对`components.part_number`建立**GIN三元组索引**支持模糊搜索
- 对高频查询（如热门IC的影响分析）增加**Redis缓存**
- 大批量导入时使用**批量插入**（`INSERT ... ON CONFLICT`）而非逐条插入

### 10.4 扩展性考虑

- 数据库设计预留**JSONB字段**，便于后续扩展元器件属性（如封装、温度等级等）
- API设计遵循**RESTful规范**，便于后续对接其他系统（PLM/ERP）
- 预留**Webhook机制**，当检测到IC停产时可自动通知下游系统


## 十一、附录：示例代码片段

### A. 核心查询SQL

```sql
-- 查询某IC影响的所有产品（含BOM明细）
SELECT 
    p.product_code,
    p.product_name,
    bi.quantity,
    bi.reference,
    c.part_number,
    c.manufacturer,
    c.lifecycle_status
FROM components c
JOIN bom_items bi ON c.id = bi.component_id
JOIN products p ON bi.product_id = p.id
WHERE c.part_number = 'STM32F103C8T6'
ORDER BY p.product_code;
```

### B. FastAPI端点示例

```python
from fastapi import FastAPI, UploadFile, File, Query
from sqlalchemy.orm import Session

app = FastAPI()

@app.post("/api/bom/upload")
async def upload_bom(
    file: UploadFile = File(...),
    product_code: str = None
):
    """上传单个BOM Excel文件"""
    # 1. 保存临时文件
    # 2. 解析Excel
    # 3. 提取产品和元器件信息
    # 4. 写入数据库
    # 5. 返回导入结果
    pass

@app.get("/api/impact/{part_number}")
async def get_impact(part_number: str, db: Session):
    """查询IC影响的产品"""
    # 1. 查询元器件
    # 2. 查询关联产品
    # 3. 组装返回结果
    pass

@app.post("/api/query/natural")
async def natural_query(question: str, db: Session):
    """自然语言查询"""
    # 1. 调用LLM解析意图
    # 2. 生成SQL
    # 3. 执行查询
    # 4. 返回结果
    pass
```


## 十二、版本记录

| 版本 | 日期 | 作者 | 修改说明 |
|------|------|------|---------|
| v1.0 | 2026-07-17 | - | 初始版本，完成整体架构设计 |
```

