# 🧠 知识图谱智能助手

基于知识图谱的生成式学习助手，结合大语言模型实现智能问答。

## 📁 项目结构

```
├── config/                 # 配置模块
│   ├── settings.py        # 全局配置
│   └── prompts.py         # Prompt 模板
│
├── data/                   # 数据目录
│   ├── raw/               # 原始文档 (PDF/Markdown)
│   ├── processed/         # 处理后的文件
│   └── exports/           # 导出的图谱数据
│
├── src/                    # 源代码
│   ├── pipeline/          # 知识构建流水线
│   │   ├── parser.py      # 文档解析
│   │   └── extractor.py   # LLM 知识抽取
│   │
│   ├── models/            # 数据模型
│   │   └── schema.py      # Pydantic 模型定义
│   │
│   ├── retrieval/         # 检索模块 (待开发)
│   └── agent/             # Agent 模块 (待开发)
│
├── scripts/               # 脚本工具
│   ├── build_kg.py        # 构建知识图谱
│   ├── test_api.py        # API 测试
│   └── retry_failed.py    # 重试失败块
│
├── app/                   # 应用入口 (待开发)
├── .env.example           # 环境变量模板
└── requirements.txt       # Python 依赖
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
```

### 3. 测试 API 连接

```bash
python scripts/test_api.py
```

### 4. 构建知识图谱

```bash
# 将教材文件放入 data/raw/ 目录
# 运行构建脚本
python scripts/build_kg.py --input data/raw/教材.md --output data/exports/graph.json
```

## 📖 开发指南

### 知识抽取流程

1. **文档解析** (`src/pipeline/parser.py`)
   - 支持 Markdown 格式
   - 按章节切分，保留层级上下文

2. **LLM 抽取** (`src/pipeline/extractor.py`)
   - 使用 instructor 库实现结构化输出
   - 提取实体（概念、硬件、指令等）和关系

3. **数据模型** (`src/models/schema.py`)
   - 基于 Pydantic 定义节点和关系类型
   - 支持自定义扩展

### 配置说明

在 `.env` 文件中配置：

| 变量 | 说明 | 示例 |
|------|------|------|
| `LLM_API_KEY` | API 密钥 | `sk-xxx` |
| `LLM_BASE_URL` | API 地址 | `https://api.deepseek.com/v1` |
| `LLM_MODEL` | 模型名称 | `deepseek-chat` |
| `NEO4J_URI` | Neo4j 地址 | `bolt://localhost:7687` |
| `NEO4J_PASSWORD` | Neo4j 密码 | `your-password` |

## 🛠️ 待开发功能

- [ ] PDF 文档解析
- [ ] Neo4j 存储模块
- [ ] 向量检索模块
- [ ] 混合检索模块
- [ ] Agent 问答模块
- [ ] Streamlit 前端界面
- [ ] 知识图谱动态更新

## 📚 技术栈

- **LLM**: DeepSeek / OpenAI 兼容 API
- **结构化输出**: instructor + Pydantic
- **图数据库**: Neo4j (待集成)
- **向量数据库**: ChromaDB (待集成)
- **Agent 框架**: LangChain (待集成)

## 📄 许可证

MIT License
