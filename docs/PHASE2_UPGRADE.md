# Phase 2 升级说明

## 🚀 新增功能

### 1. LangChain Agent 支持
- 使用 LangChain 框架重构 Agent
- 支持自动工具选择和调用
- 更智能的对话流程控制

### 2. 多轮对话记忆
- 基于 `InMemoryChatMessageHistory` 的会话管理
- 每个会话独立维护上下文
- 支持代词解析和追问

### 3. 知识图谱可视化
- 使用 Pyvis 生成交互式图谱
- 支持概念邻域可视化
- 学习路径可视化
- 章节结构可视化
- 图谱统计信息展示

### 4. 问题澄清机制
- 检测模糊问题
- 自动请求澄清
- 提供问题选项

### 5. 升级的 UI 界面
- 现代化设计风格
- 图谱探索面板
- 工具调用透明展示
- 调试模式开关

## 📁 新增文件

```
src/agent/
├── langchain_tools.py     # LangChain 工具定义
└── langchain_agent.py     # LangChain Agent 实现

src/visualization/
├── __init__.py
└── graph_viz.py           # 图谱可视化组件

app/
├── streamlit_app.py       # Phase 1 版本 (保留)
└── streamlit_app_v2.py    # Phase 2 版本 (新增)
```

## 🛠 使用方式

### 启动 Phase 2 应用
```bash
# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 运行新版应用
streamlit run app/streamlit_app_v2.py
```

### 访问地址
- 本地: http://localhost:8502

## 📌 功能说明

### 侧边栏功能
1. **快速提问**: 点击示例问题直接提问
2. **图谱探索**: 
   - 输入概念名称，点击"查看图谱"可视化
   - 点击"统计信息"查看图谱概览
3. **调试模式**: 开启后显示工具调用详情

### 支持的问题类型
- **概念解释**: 什么是补码？
- **组成结构**: CPU由什么组成？
- **学习路径**: 学虚拟内存需要什么基础？
- **概念对比**: SRAM和DRAM有什么区别？
- **关系查询**: CPU和ALU有什么关系？
- **通用问答**: 流水线冒险怎么解决？
- **追问深入**: 继续上面的话题...

### 图谱可视化
1. 在侧边栏输入概念名称（如：CPU、缓存）
2. 点击"查看图谱"按钮
3. 交互操作：
   - 拖拽节点调整位置
   - 滚轮缩放
   - 双击节点固定位置
   - 悬停查看详情

## 🔧 技术栈

| 组件 | 技术 |
|------|------|
| Agent 框架 | LangChain |
| LLM | DeepSeek/Qwen |
| 图数据库 | Neo4j |
| 向量存储 | Neo4j Vector Index |
| 可视化 | Pyvis |
| Web 框架 | Streamlit |

## ⚠️ 注意事项

1. **确保 Neo4j 运行**: 启动前确保 Neo4j 数据库已启动
2. **API 配额**: LangChain Agent 会进行多次 API 调用，注意配额
3. **兼容性**: Phase 1 版本 (`streamlit_app.py`) 仍可正常使用

## 🔄 版本对比

| 特性 | Phase 1 | Phase 2 |
|------|---------|---------|
| 多轮对话 | ✅ 基础 | ✅ 增强 |
| 工具调用 | 手动路由 | 自动选择 |
| 对话记忆 | 简单历史 | 会话级别 |
| 图谱可视化 | ❌ | ✅ |
| 问题澄清 | ❌ | ✅ |
| UI 设计 | 基础 | 现代化 |

