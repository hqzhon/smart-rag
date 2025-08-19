#!/bin/bash
# 医疗RAG系统部署脚本

# 设置颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查环境
check_environment() {
    print_message "检查环境..."
    
    # 检查Python版本
    python_version=$(python3 --version 2>&1 | awk '{print $2}')
    print_message "Python版本: $python_version"
    
    # 检查pip
    pip_version=$(pip --version 2>&1 | awk '{print $2}')
    print_message "pip版本: $pip_version"
    
    # 检查虚拟环境
    if [ -d "venv" ]; then
        print_message "发现虚拟环境: venv"
    else
        print_message "创建虚拟环境: venv"
        python3 -m venv venv
    fi
    
    # 激活虚拟环境
    print_message "激活虚拟环境..."
    source venv/bin/activate || { print_error "激活虚拟环境失败"; exit 1; }
}

# 安装依赖
install_dependencies() {
    print_message "安装依赖..."
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装依赖
    if [ "$1" == "full" ]; then
        print_message "安装完整依赖..."
        pip install -r requirements.txt || { print_error "安装完整依赖失败"; exit 1; }
    else
        print_message "安装基础依赖..."
        pip install -r requirements-simple.txt || { print_error "安装基础依赖失败"; exit 1; }
    fi
    
    print_message "依赖安装完成"
}

# 配置环境变量
configure_environment() {
    print_message "配置环境变量..."
    
    if [ ! -f ".env" ]; then
        print_message "创建环境变量文件..."
        cp .env.example .env || { print_error "创建环境变量文件失败"; exit 1; }
        print_warning "请编辑 .env 文件配置必要的参数"
    else
        print_message "环境变量文件已存在"
    fi
}

# 创建必要的目录
create_directories() {
    print_message "创建必要的目录..."
    
    mkdir -p data/raw data/processed data/chroma_db logs
    
    print_message "目录创建完成"
}

# 启动服务
start_service() {
    print_message "启动服务..."
    
    # 检查是否已有服务运行
    if pgrep -f "python run.py" > /dev/null; then
        print_warning "服务已在运行，正在重启..."
        pkill -f "python run.py"
        sleep 2
    fi
    
    # 启动服务
    if [ "$1" == "daemon" ]; then
        print_message "以守护进程方式启动服务..."
        nohup python run.py > logs/app.log 2>&1 &
        echo $! > .pid
        print_message "服务已启动，PID: $(cat .pid)"
    else
        print_message "以前台方式启动服务..."
        python run.py
    fi
}

# 停止服务
stop_service() {
    print_message "停止服务..."
    
    if [ -f ".pid" ]; then
        pid=$(cat .pid)
        if ps -p $pid > /dev/null; then
            kill $pid
            print_message "服务已停止，PID: $pid"
        else
            print_warning "服务未运行"
        fi
        rm .pid
    else
        print_warning "找不到PID文件，尝试查找进程..."
        if pgrep -f "python run.py" > /dev/null; then
            pkill -f "python run.py"
            print_message "服务已停止"
        else
            print_warning "服务未运行"
        fi
    fi
}

# 显示帮助信息
show_help() {
    echo "医疗RAG系统部署脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  setup       设置环境和安装依赖"
    echo "  start       启动服务"
    echo "  stop        停止服务"
    echo "  restart     重启服务"
    echo "  status      查看服务状态"
    echo "  --full      安装完整依赖（与setup一起使用）"
    echo "  --daemon    以守护进程方式启动（与start或restart一起使用）"
    echo "  --help      显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 setup --full     设置环境并安装完整依赖"
    echo "  $0 start --daemon   以守护进程方式启动服务"
    echo "  $0 restart          重启服务"
}

# 检查服务状态
check_status() {
    print_message "检查服务状态..."
    
    if [ -f ".pid" ]; then
        pid=$(cat .pid)
        if ps -p $pid > /dev/null; then
            print_message "服务正在运行，PID: $pid"
            return 0
        else
            print_warning "服务未运行，但PID文件存在"
            rm .pid
            return 1
        fi
    else
        if pgrep -f "python run.py" > /dev/null; then
            pid=$(pgrep -f "python run.py")
            print_message "服务正在运行，PID: $pid"
            echo $pid > .pid
            return 0
        else
            print_warning "服务未运行"
            return 1
        fi
    fi
}

# 主函数
main() {
    # 检查参数
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi
    
    # 解析参数
    command=$1
    shift
    
    full=false
    daemon=false
    
    while [ $# -gt 0 ]; do
        case "$1" in
            --full)
                full=true
                ;;
            --daemon)
                daemon=true
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                print_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
        shift
    done
    
    # 执行命令
    case "$command" in
        setup)
            check_environment
            if [ "$full" = true ]; then
                install_dependencies "full"
            else
                install_dependencies
            fi
            configure_environment
            create_directories
            print_message "设置完成"
            ;;
        start)
            if [ "$daemon" = true ]; then
                start_service "daemon"
            else
                start_service
            fi
            ;;
        stop)
            stop_service
            ;;
        restart)
            stop_service
            sleep 2
            if [ "$daemon" = true ]; then
                start_service "daemon"
            else
                start_service
            fi
            ;;
        status)
            check_status
            ;;
        *)
            print_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"