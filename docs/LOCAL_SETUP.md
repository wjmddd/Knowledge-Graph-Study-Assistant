# 🖥️ 本地部署指南

本文档详细介绍如何在新电脑上部署"计算机系统基础-智能学习助手"。

---

## 📋 目录

1. [环境要求](#1-环境要求)
2. [安装 Python](#2-安装-python)
3. [安装 Neo4j](#3-安装-neo4j)
4. [获取项目代码](#4-获取项目代码)
5. [安装依赖](#5-安装依赖)
6. [配置文件](#6-配置文件)
7. [导入数据](#7-导入数据)
8. [启动服务](#8-启动服务)
9. [常见问题](#9-常见问题)

---

## 1. 环境要求

### 硬件要求
| 项目 | 最低 | 推荐 |
|------|------|------|
| CPU | 双核 | 四核 |
| 内存 | 8 GB | 16 GB |
| 硬盘 | 10 GB 可用空间 | 20 GB SSD |

### 软件要求
| 软件 | 版本 |
|------|------|
| Python | 3.10+ |
| Neo4j Desktop | 5.x |
| Git | 任意版本 |

---

## 2. 安装 Python

### Windows

1. **下载 Python**
   - 访问：https://www.python.org/downloads/
   - 下载 Python 3.11 或 3.12

2. **安装时注意**
   - ✅ 勾选 **"Add Python to PATH"**
   - 选择 "Customize installation"
   - ✅ 勾选 "pip"
   - ✅ 勾选 "Add Python to environment variables"

3. **验证安装**
   ```powershell
   python --version
   # 输出: Python 3.11.x
   
   pip --version
   # 输出: pip 23.x.x
   ```

### macOS

```bash
# 使用 Homebrew 安装
brew install python@3.11

# 验证
python3 --version
pip3 --version
```

### Linux (Ubuntu)

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# 验证
python3 --version
pip3 --version
```

---

## 3. 安装 Neo4j

### 方式一：Neo4j Desktop（推荐，图形界面）

1. **下载**
   - 访问：https://neo4j.com/download/
   - 点击 "Download Neo4j Desktop"
   - 注册账号获取激活码

2. **安装**
   - Windows: 双击安装包，按提示安装
   - macOS: 拖到 Applications 文件夹

3. **创建数据库**
   - 打开 Neo4j Desktop
   - 点击 "New" → "Create project"
   - 点击 "Add" → "Local DBMS"
   - 设置密码（**记住这个密码！**）
   - 版本选择 5.x
   - 点击 "Create"

4. **启动数据库**
   - 点击 "Start" 启动数据库
   - 状态变为 "Running" 即可

5. **记录连接信息**
   ```
   URI: bolt://localhost:7687
   User: neo4j
   Password: 你设置的密码
   ```

### 方式二：Neo4j Community Server（命令行）

#### Windows

1. 下载：https://neo4j.com/download-center/#community
2. 解压到 `C:\neo4j`
3. 运行：
   ```powershell
   cd C:\neo4j\bin
   .\neo4j console
   ```

#### macOS / Linux

```bash
# 下载并解压
wget https://dist.neo4j.org/neo4j-community-5.15.0-unix.tar.gz
tar -xzf neo4j-community-5.15.0-unix.tar.gz
cd neo4j-community-5.15.0

# 启动
./bin/neo4j console
```

4. **首次设置密码**
   - 访问：http://localhost:7474
   - 默认用户名：neo4j
   - 默认密码：neo4j
   - 系统会要求设置新密码

---

## 4. 获取项目代码

### 方式一：从 U盘/硬盘 复制

直接复制整个项目文件夹到新电脑：

```
Knowledge-Graph-Study-Assistant/
├── app/
├── config/
├── data/
├── docs/
├── md/
├── scripts/
├── src/
├── graph_data_final.json      # 知识图谱数据（重要！）
├── requirements.txt
└── ...
```

### 方式二：从 Git 仓库克隆

```bash
git clone https://github.com/yourname/Knowledge-Graph-Study-Assistant.git
cd Knowledge-Graph-Study-Assistant
```

### 方式三：从压缩包解压

```bash
# Windows PowerShell
Expand-Archive -Path "Knowledge-Graph-Study-Assistant.zip" -DestinationPath "D:\projects\"

# macOS / Linux
unzip Knowledge-Graph-Study-Assistant.zip -d ~/projects/
```

---

## 5. 安装依赖

### Windows

```powershell
# 进入项目目录
cd D:\bysj\Knowledge-Graph-Study-Assistant

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 如果报错"无法加载文件"，先执行：
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 升级 pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

### macOS / Linux

```bash
# 进入项目目录
cd ~/projects/Knowledge-Graph-Study-Assistant

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

### 验证安装

```bash
# 检查关键包
pip list | grep -E "chainlit|langchain|neo4j|openai"
```

应该看到：
```
chainlit             1.x.x
langchain            0.3.x
langchain-openai     0.2.x
neo4j                5.x.x
openai               1.x.x
```

---

## 6. 配置文件

### 6.1 编辑 config/settings.py

```python
# ================= Neo4j 配置 =================
NEO4J_CONFIG = {
    "uri": "bolt://localhost:7687",      # 本地 Neo4j
    "user": "neo4j",
    "password": "你的Neo4j密码"           # ⬅️ 修改这里
}

# ================= LLM 配置 =================
CLIENT_CONFIG = {
    "api_key": "sk-xxx",                  # ⬅️ 你的 API Key
    "base_url": "https://api.deepseek.com/v1",  # 或其他 API
    "model": "deepseek-chat"
}

# ================= OpenAI Embedding 配置 =================
OPENAI_CONFIG = {
    "api_key": "sk-xxx",                  # ⬅️ 你的 API Key
    "base_url": "https://api.openai.com/v1",
    "embedding_model": "text-embedding-3-small",
    "embedding_dimensions": 1536
}
```

### 6.2 API Key 获取

| API | 获取地址 | 说明 |
|-----|----------|------|
| DeepSeek | https://platform.deepseek.com | 国产，便宜 |
| OpenAI | https://platform.openai.com | 需要国际支付 |
| 代理 API | 各种第三方 | 如 SiliconFlow |

---

## 7. 导入数据

### 7.1 确保 Neo4j 正在运行

- Neo4j Desktop: 检查状态为 "Running"
- 命令行: 确保 `neo4j console` 在运行

### 7.2 导入知识图谱

```powershell
# Windows
cd D:\bysj\Knowledge-Graph-Study-Assistant
.\venv\Scripts\Activate.ps1

# 导入数据
python scripts/import_to_neo4j.py
```

```bash
# macOS / Linux
cd ~/projects/Knowledge-Graph-Study-Assistant
source venv/bin/activate

python scripts/import_to_neo4j.py
```

预期输出：
```
正在导入节点... 100%
正在导入关系... 100%
✅ 导入完成！
   节点: 1234 个
   关系: 5678 条
```

### 7.3 构建向量索引

```bash
python scripts/build_vector_store.py
```

预期输出：
```
正在生成 Embedding... 100%
✅ 向量索引构建完成！
```

### 7.4 验证数据

```bash
python -c "
from src.retrieval.graph_query import get_graph_query
gq = get_graph_query()
if gq.is_connected():
    stats = gq.get_stats()
    print('✅ Neo4j 连接成功')
    print('节点:', stats.get('nodes'))
    print('关系:', stats.get('relationships'))
else:
    print('❌ Neo4j 连接失败')
"
```

---

## 8. 启动服务

### 8.1 启动 Chainlit（推荐）

```powershell
# Windows
cd D:\bysj\Knowledge-Graph-Study-Assistant
.\venv\Scripts\Activate.ps1
chainlit run app/chainlit_app.py --port 8000
```

```bash
# macOS / Linux
cd ~/projects/Knowledge-Graph-Study-Assistant
source venv/bin/activate
chainlit run app/chainlit_app.py --port 8000
```

访问：**http://localhost:8000**

### 8.2 启动 Streamlit（备选）

```bash
streamlit run app/streamlit_app_v2.py --server.port 8501
```

访问：**http://localhost:8501**

### 8.3 命令行模式

```bash
python src/agent/langchain_agent.py
```

---

## 9. 常见问题

### Q1: PowerShell 无法激活虚拟环境

**错误**: `无法加载文件...因为在此系统上禁止运行脚本`

**解决**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q2: Neo4j 连接失败

**检查项**:
1. Neo4j 是否已启动？
2. 密码是否正确？
3. 端口 7687 是否被占用？

```powershell
# 检查端口
netstat -an | findstr "7687"
```

### Q3: pip 安装依赖失败

**尝试**:
```bash
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q4: Chainlit 启动报错

**检查**:
```bash
# 确认 Chainlit 已安装
pip show chainlit

# 重新安装
pip uninstall chainlit
pip install chainlit
```

### Q5: API 调用失败

**检查**:
1. API Key 是否正确？
2. 网络是否能访问 API 地址？
3. API 余额是否充足？

```bash
# 测试 API（替换你的 Key）
curl https://api.deepseek.com/v1/models \
  -H "Authorization: Bearer sk-xxx"
```

### Q6: 内存不足

**Neo4j 占用过大时**，编辑 Neo4j 配置：
```ini
# neo4j.conf
server.memory.heap.initial_size=512m
server.memory.heap.max_size=1G
```

---

## 📁 项目结构说明

```
Knowledge-Graph-Study-Assistant/
├── app/
│   ├── chainlit_app.py      # Chainlit 前端
│   └── streamlit_app_v2.py  # Streamlit 前端
├── config/
│   └── settings.py          # ⭐ 配置文件（需修改）
├── data/
│   └── chapters/            # 章节数据
├── md/
│   └── *.md                 # Markdown 源文件
├── scripts/
│   ├── import_to_neo4j.py   # 导入数据脚本
│   ├── build_vector_store.py # 构建向量索引
│   └── ...
├── src/
│   ├── agent/               # Agent 逻辑
│   ├── models/              # 数据模型
│   ├── pipeline/            # 知识抽取流水线
│   ├── retrieval/           # 检索模块
│   └── visualization/       # 可视化
├── graph_data_final.json    # ⭐ 知识图谱数据
├── requirements.txt         # Python 依赖
└── venv/                    # 虚拟环境（不用复制）
```

### 换电脑时需要复制的文件

**必须复制**:
- `config/settings.py` (含你的配置)
- `graph_data_final.json` (知识图谱数据)
- `data/` 目录 (章节数据)
- 其他所有源代码

**不需要复制**:
- `venv/` (虚拟环境，重新创建)
- `.chainlit/` (会自动生成)
- `__pycache__/` (Python 缓存)

---

## ⚡ 快速部署命令汇总

```powershell
# Windows 一键部署（假设已安装 Python 和 Neo4j）

# 1. 进入项目目录
cd D:\bysj\Knowledge-Graph-Study-Assistant

# 2. 创建并激活虚拟环境
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. 安装依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 修改配置（手动编辑 config/settings.py）

# 5. 导入数据
python scripts/import_to_neo4j.py
python scripts/build_vector_store.py

# 6. 启动服务
chainlit run app/chainlit_app.py --port 8000
```

---

## 📞 检查清单

| 步骤 | 状态 |
|------|------|
| ☐ Python 3.10+ 已安装 | |
| ☐ Neo4j 已安装并运行 | |
| ☐ 项目代码已复制 | |
| ☐ 虚拟环境已创建 | |
| ☐ 依赖已安装 | |
| ☐ config/settings.py 已配置 | |
| ☐ 知识图谱数据已导入 | |
| ☐ 向量索引已构建 | |
| ☐ 服务启动成功 | |

祝部署顺利！🎉

