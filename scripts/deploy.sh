#!/bin/bash
# ============================================
# 知识图谱问答系统 - 快速部署脚本
# 适用于 Ubuntu 22.04
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为 root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用 root 用户运行此脚本"
        exit 1
    fi
}

# 安装基础依赖
install_dependencies() {
    log_info "安装基础依赖..."
    apt update
    apt install -y git curl wget vim build-essential \
        python3 python3-pip python3-venv \
        nginx supervisor
    log_info "基础依赖安装完成"
}

# 安装 Neo4j
install_neo4j() {
    log_info "安装 Neo4j..."
    
    # 添加源
    curl -fsSL https://debian.neo4j.com/neotechnology.gpg.key | gpg --dearmor -o /usr/share/keyrings/neo4j.gpg
    echo "deb [signed-by=/usr/share/keyrings/neo4j.gpg] https://debian.neo4j.com stable latest" | tee /etc/apt/sources.list.d/neo4j.list
    
    apt update
    apt install -y neo4j
    
    # 启动 Neo4j
    systemctl start neo4j
    systemctl enable neo4j
    
    log_info "Neo4j 安装完成"
    log_warn "请稍后手动设置 Neo4j 密码: cypher-shell -u neo4j -p neo4j"
}

# 创建项目目录
setup_project() {
    log_info "创建项目目录..."
    
    mkdir -p /var/www/kg-assistant
    cd /var/www/kg-assistant
    
    log_info "项目目录创建完成: /var/www/kg-assistant"
}

# 设置 Python 环境
setup_python() {
    log_info "设置 Python 虚拟环境..."
    
    cd /var/www/kg-assistant
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        log_info "Python 依赖安装完成"
    else
        log_warn "未找到 requirements.txt，请手动安装依赖"
    fi
}

# 配置 Nginx
setup_nginx() {
    log_info "配置 Nginx..."
    
    cat > /etc/nginx/sites-available/kg-assistant << 'EOF'
server {
    listen 80;
    server_name _;

    access_log /var/log/nginx/kg-assistant.access.log;
    error_log /var/log/nginx/kg-assistant.error.log;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}
EOF
    
    ln -sf /etc/nginx/sites-available/kg-assistant /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    nginx -t
    systemctl restart nginx
    systemctl enable nginx
    
    log_info "Nginx 配置完成"
}

# 创建 Systemd 服务
setup_systemd() {
    log_info "创建 Systemd 服务..."
    
    cat > /etc/systemd/system/kg-assistant.service << 'EOF'
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
EOF
    
    systemctl daemon-reload
    log_info "Systemd 服务创建完成"
}

# 启动服务
start_service() {
    log_info "启动服务..."
    
    systemctl start kg-assistant
    systemctl enable kg-assistant
    
    log_info "服务启动完成"
}

# 显示状态
show_status() {
    echo ""
    echo "============================================"
    echo "        部署完成！"
    echo "============================================"
    echo ""
    echo "服务状态:"
    systemctl status kg-assistant --no-pager || true
    echo ""
    echo "访问地址: http://$(curl -s ifconfig.me)"
    echo ""
    echo "下一步操作:"
    echo "1. 设置 Neo4j 密码: cypher-shell -u neo4j -p neo4j"
    echo "2. 修改配置文件: vim /var/www/kg-assistant/config/settings.py"
    echo "3. 导入数据: python scripts/import_to_neo4j.py"
    echo "4. 重启服务: systemctl restart kg-assistant"
    echo ""
}

# 主函数
main() {
    echo "============================================"
    echo "  知识图谱问答系统 - 快速部署脚本"
    echo "============================================"
    echo ""
    
    check_root
    
    case "${1:-}" in
        "deps")
            install_dependencies
            ;;
        "neo4j")
            install_neo4j
            ;;
        "project")
            setup_project
            ;;
        "python")
            setup_python
            ;;
        "nginx")
            setup_nginx
            ;;
        "systemd")
            setup_systemd
            ;;
        "start")
            start_service
            ;;
        "status")
            show_status
            ;;
        "all")
            install_dependencies
            install_neo4j
            setup_project
            setup_nginx
            setup_systemd
            log_warn "请上传项目代码到 /var/www/kg-assistant 后运行: bash deploy.sh python"
            ;;
        *)
            echo "用法: $0 {deps|neo4j|project|python|nginx|systemd|start|status|all}"
            echo ""
            echo "  deps    - 安装基础依赖"
            echo "  neo4j   - 安装 Neo4j"
            echo "  project - 创建项目目录"
            echo "  python  - 设置 Python 环境（需先上传代码）"
            echo "  nginx   - 配置 Nginx"
            echo "  systemd - 创建 Systemd 服务"
            echo "  start   - 启动服务"
            echo "  status  - 显示状态"
            echo "  all     - 执行所有步骤（不含代码上传）"
            echo ""
            ;;
    esac
}

main "$@"

