# 🚀 云服务器部署指南

本文档详细介绍如何将"计算机系统基础-智能学习助手"部署到阿里云/腾讯云服务器。

---

## 📋 目录

1. [服务器要求](#1-服务器要求)
2. [购买和配置云服务器](#2-购买和配置云服务器)
3. [服务器环境配置](#3-服务器环境配置)
4. [安装 Neo4j 数据库](#4-安装-neo4j-数据库)
5. [部署项目代码](#5-部署项目代码)
6. [配置文件修改](#6-配置文件修改)
7. [导入知识图谱数据](#7-导入知识图谱数据)
8. [启动服务](#8-启动服务)
9. [配置 Nginx 反向代理](#9-配置-nginx-反向代理)
10. [配置 HTTPS（可选）](#10-配置-https可选)
11. [设置开机自启](#11-设置开机自启)
12. [常见问题](#12-常见问题)

---

## 1. 服务器要求

### 最低配置
| 项目 | 要求 |
|------|------|
| CPU | 2 核 |
| 内存 | 4 GB |
| 硬盘 | 50 GB SSD |
| 系统 | Ubuntu 22.04 LTS / CentOS 7+ |
| 带宽 | 3 Mbps |

### 推荐配置
| 项目 | 要求 |
|------|------|
| CPU | 4 核 |
| 内存 | 8 GB |
| 硬盘 | 100 GB SSD |
| 系统 | Ubuntu 22.04 LTS |
| 带宽 | 5 Mbps |

### 需要开放的端口
| 端口 | 用途 |
|------|------|
| 22 | SSH 远程连接 |
| 80 | HTTP 访问 |
| 443 | HTTPS 访问 |
| 8000 | Chainlit 应用（内部） |
| 7474 | Neo4j Browser（可选，调试用） |
| 7687 | Neo4j Bolt 协议（内部） |

---

## 2. 购买和配置云服务器

### 阿里云
1. 访问 [阿里云 ECS](https://www.aliyun.com/product/ecs)
2. 选择"按量付费"或"包年包月"
3. 选择地域（建议选择离用户近的）
4. 选择配置：2核4G 或 4核8G
5. 选择系统：**Ubuntu 22.04 64位**
6. 设置安全组，开放上述端口
7. 设置登录密码或 SSH 密钥

### 腾讯云
1. 访问 [腾讯云 CVM](https://cloud.tencent.com/product/cvm)
2. 选择"按量计费"或"包年包月"
3. 选择地域和可用区
4. 选择配置：2核4G 或 4核8G
5. 选择系统：**Ubuntu 22.04 64位**
6. 配置安全组，开放端口
7. 设置登录密码或 SSH 密钥

---

## 3. 服务器环境配置

### 3.1 连接服务器

```bash
# Windows 使用 PowerShell 或 CMD
ssh root@你的服务器IP

# 或使用密钥
ssh -i ~/.ssh/your_key.pem root@你的服务器IP
```

### 3.2 更新系统

```bash
# Ubuntu
sudo apt update && sudo apt upgrade -y

# CentOS
sudo yum update -y
```

### 3.3 安装基础依赖

```bash
# Ubuntu
sudo apt install -y git curl wget vim build-essential \
    python3 python3-pip python3-venv \
    nginx supervisor

# CentOS
sudo yum install -y git curl wget vim gcc gcc-c++ make \
    python3 python3-pip python3-devel \
    nginx supervisor
```

### 3.4 安装 Python 3.10+（如果系统版本过低）

```bash
# Ubuntu 22.04 自带 Python 3.10，可跳过
python3 --version

# 如果版本低于 3.10，安装新版本
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev
```

---

## 4. 安装 Neo4j 数据库

### 4.1 添加 Neo4j 源

```bash
# 添加 Neo4j GPG key
curl -fsSL https://debian.neo4j.com/neotechnology.gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/neo4j.gpg

# 添加源
echo "deb [signed-by=/usr/share/keyrings/neo4j.gpg] https://debian.neo4j.com stable latest" | sudo tee /etc/apt/sources.list.d/neo4j.list

# 更新并安装
sudo apt update
sudo apt install -y neo4j
```

### 4.2 配置 Neo4j

```bash
# 编辑配置文件
sudo vim /etc/neo4j/neo4j.conf
```

修改以下配置：

```ini
# 允许远程连接（如果需要从本地访问 Neo4j Browser）
server.default_listen_address=0.0.0.0

# 设置初始密码（重要！）
dbms.security.auth_enabled=true

# 内存配置（根据服务器内存调整）
server.memory.heap.initial_size=512m
server.memory.heap.max_size=1G
server.memory.pagecache.size=512m
```

### 4.3 启动 Neo4j

```bash
# 启动服务
sudo systemctl start neo4j

# 设置开机自启
sudo systemctl enable neo4j

# 查看状态
sudo systemctl status neo4j
```

### 4.4 设置 Neo4j 密码

```bash
# 首次登录设置密码
cypher-shell -u neo4j -p neo4j

# 系统会提示你设置新密码，输入新密码（如：YourStrongPassword123）
# 记住这个密码，后面配置要用！
```

---

## 5. 部署项目代码

### 5.1 创建部署目录

```bash
# 创建应用目录
sudo mkdir -p /var/www/kg-assistant
sudo chown -R $USER:$USER /var/www/kg-assistant
cd /var/www/kg-assistant
```

### 5.2 上传项目代码

**方式一：使用 Git（推荐）**

```bash
# 如果项目在 GitHub/Gitee
git clone https://github.com/yourname/Knowledge-Graph-Study-Assistant.git .
```

**方式二：使用 SCP 上传**

```bash
# 在本地执行（Windows PowerShell）
scp -r D:\bysj\Knowledge-Graph-Study-Assistant\* root@你的服务器IP:/var/www/kg-assistant/
```

**方式三：使用 SFTP 工具**

使用 FileZilla、WinSCP 等工具上传整个项目文件夹。

### 5.3 创建虚拟环境

```bash
cd /var/www/kg-assistant

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

---

## 6. 配置文件修改

### 6.1 修改 config/settings.py

```bash
vim config/settings.py
```

修改以下配置：

```python
# ================= Neo4j 配置 =================
NEO4J_CONFIG = {
    "uri": "bolt://localhost:7687",  # 服务器本地连接
    "user": "neo4j",
    "password": "YourStrongPassword123"  # 改为你设置的密码
}

# ================= LLM 配置 =================
CLIENT_CONFIG = {
    "api_key": "sk-xxx",  # 你的 API Key
    "base_url": "https://api.deepseek.com/v1",  # 或其他 API 地址
    "model": "deepseek-chat"
}

# ================= OpenAI Embedding 配置 =================
OPENAI_CONFIG = {
    "api_key": "sk-xxx",  # 你的 API Key
    "base_url": "https://api.openai.com/v1",  # 或代理地址
    "embedding_model": "text-embedding-3-small",
    "embedding_dimensions": 1536
}
```

### 6.2 创建环境变量文件（推荐）

```bash
vim .env
```

```bash
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=YourStrongPassword123

# LLM API
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

# OpenAI Embedding
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
```

---

## 7. 导入知识图谱数据

### 7.1 上传数据文件

确保以下文件已上传到服务器：

```
/var/www/kg-assistant/
├── graph_data_final.json    # 最终的知识图谱数据
├── data/
│   └── chapters/           # 章节数据
└── md/                     # Markdown 源文件
```

### 7.2 导入到 Neo4j

```bash
cd /var/www/kg-assistant
source venv/bin/activate

# 运行导入脚本
python scripts/import_to_neo4j.py
```

### 7.3 构建向量索引

```bash
# 构建向量存储
python scripts/build_vector_store.py
```

### 7.4 验证数据

```bash
# 测试查询
python -c "
from src.retrieval.graph_query import get_graph_query
gq = get_graph_query()
stats = gq.get_stats()
print('节点统计:', stats.get('nodes'))
print('关系统计:', stats.get('relationships'))
"
```

---

## 8. 启动服务

### 8.1 测试启动

```bash
cd /var/www/kg-assistant
source venv/bin/activate

# 测试启动（前台运行）
chainlit run app/chainlit_app.py --host 0.0.0.0 --port 8000
```

访问 `http://你的服务器IP:8000` 测试是否正常。

### 8.2 后台运行（使用 Screen）

```bash
# 安装 screen
sudo apt install -y screen

# 创建新会话
screen -S kg-assistant

# 启动服务
cd /var/www/kg-assistant
source venv/bin/activate
chainlit run app/chainlit_app.py --host 0.0.0.0 --port 8000

# 按 Ctrl+A 然后按 D 退出会话（服务继续运行）

# 重新连接会话
screen -r kg-assistant
```

---

## 9. 配置 Nginx 反向代理

### 9.1 创建 Nginx 配置

```bash
sudo vim /etc/nginx/sites-available/kg-assistant
```

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 改为你的域名或 IP

    # 日志
    access_log /var/log/nginx/kg-assistant.access.log;
    error_log /var/log/nginx/kg-assistant.error.log;

    # 代理到 Chainlit
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 超时设置
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }

    # 静态文件（可选）
    location /public/ {
        alias /var/www/kg-assistant/public/;
        expires 7d;
    }
}
```

### 9.2 启用配置

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/kg-assistant /etc/nginx/sites-enabled/

# 删除默认配置（可选）
sudo rm /etc/nginx/sites-enabled/default

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## 10. 配置 HTTPS（可选）

### 10.1 安装 Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 10.2 获取 SSL 证书

```bash
# 自动配置（需要域名已解析到服务器）
sudo certbot --nginx -d your-domain.com
```

### 10.3 自动续期

```bash
# 测试自动续期
sudo certbot renew --dry-run

# Certbot 会自动添加定时任务
```

---

## 11. 设置开机自启

### 11.1 创建 Systemd 服务

```bash
sudo vim /etc/systemd/system/kg-assistant.service
```

```ini
[Unit]
Description=Knowledge Graph Study Assistant
After=network.target neo4j.service

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/kg-assistant
Environment="PATH=/var/www/kg-assistant/venv/bin"
ExecStart=/var/www/kg-assistant/venv/bin/chainlit run app/chainlit_app.py --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 11.2 启用服务

```bash
# 重新加载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start kg-assistant

# 设置开机自启
sudo systemctl enable kg-assistant

# 查看状态
sudo systemctl status kg-assistant

# 查看日志
sudo journalctl -u kg-assistant -f
```

---

## 12. 常见问题

### Q1: Neo4j 无法连接

```bash
# 检查 Neo4j 状态
sudo systemctl status neo4j

# 查看日志
sudo journalctl -u neo4j -n 50

# 检查端口
sudo netstat -tlnp | grep 7687
```

### Q2: 内存不足

```bash
# 查看内存使用
free -h

# 创建 Swap（如果没有）
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 永久生效
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Q3: API 调用失败

检查：
1. API Key 是否正确
2. 服务器是否能访问 API 地址（可能需要代理）
3. API 余额是否充足

```bash
# 测试 API 连通性
curl -v https://api.deepseek.com/v1/models \
  -H "Authorization: Bearer sk-xxx"
```

### Q4: Chainlit 启动失败

```bash
# 查看详细错误
cd /var/www/kg-assistant
source venv/bin/activate
python -c "import chainlit; print(chainlit.__version__)"

# 重新安装依赖
pip install --upgrade chainlit
```

### Q5: WebSocket 连接断开

检查 Nginx 配置中的 WebSocket 相关设置，确保：
- `proxy_http_version 1.1`
- `proxy_set_header Upgrade $http_upgrade`
- `proxy_set_header Connection "upgrade"`

---

## 📊 部署检查清单

| 步骤 | 状态 |
|------|------|
| ☐ 服务器购买并配置安全组 | |
| ☐ 系统更新和基础依赖安装 | |
| ☐ Neo4j 安装和配置 | |
| ☐ 项目代码上传 | |
| ☐ Python 虚拟环境和依赖安装 | |
| ☐ 配置文件修改（API Key、Neo4j 密码） | |
| ☐ 知识图谱数据导入 | |
| ☐ 向量索引构建 | |
| ☐ Chainlit 服务测试 | |
| ☐ Nginx 反向代理配置 | |
| ☐ HTTPS 配置（可选） | |
| ☐ Systemd 服务配置 | |
| ☐ 开机自启验证 | |

---

## 🔗 参考链接

- [Neo4j 安装文档](https://neo4j.com/docs/operations-manual/current/installation/linux/debian/)
- [Chainlit 部署文档](https://docs.chainlit.io/deployment/overview)
- [Nginx 配置指南](https://nginx.org/en/docs/)
- [Let's Encrypt 证书申请](https://certbot.eff.org/)

---

## 📞 技术支持

如遇到部署问题，请检查：
1. 服务器日志：`/var/log/nginx/` 和 `journalctl`
2. 应用日志：`systemctl status kg-assistant`
3. Neo4j 日志：`/var/log/neo4j/`

祝部署顺利！🎉

