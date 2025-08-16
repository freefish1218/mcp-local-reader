#!/usr/bin/env python3
"""
MCP文件读取器 - 统一服务器入口点
支持stdio和HTTP两种传输模式，根据命令行参数自动选择
"""

import sys
import argparse
import asyncio
from pathlib import Path

def show_help():
    """显示帮助信息"""
    help_text = """
MCP本地文件读取器服务器

用途:
    本地文件内容读取服务，支持PDF、Office文档格式

传输模式:
    --stdio     使用标准输入输出传输 (推荐本地集成)
    --http      使用HTTP传输 (适用于远程调用)

使用示例:
    # stdio模式 - 适用于Claude Desktop等工具集成
    python run_mcp_server.py --stdio
    
    # HTTP模式 - 适用于远程调用和Web集成  
    python run_mcp_server.py --http
    
    # HTTP模式自定义端口
    python run_mcp_server.py --http --port 3002

环境变量配置:
    LLM_VISION_API_KEY          视觉模型API密钥 (图像OCR必需)
    LLM_VISION_BASE_URL         视觉模型API地址
    LLM_VISION_MODEL            视觉模型名称
    LOCAL_FILE_ALLOWED_DIRECTORIES  允许访问的目录 (逗号分隔)
    LOCAL_FILE_ALLOW_ABSOLUTE_PATHS 是否允许绝对路径访问
    FILE_READER_MAX_WORKERS     最大并发处理数
    FILE_READER_MAX_FILES_PER_REQUEST  单次请求最大文件数

支持格式:
    • PDF文档 (.pdf)
    • Office文档 (.doc, .docx, .xls, .xlsx, .ppt, .pptx)
    • OpenDocument (.odt, .ods, .odp)
    • 文本文件 (.txt, .md, .json)
    • 压缩文件 (.zip, .7z, .tar等)
"""
    print(help_text, file=sys.stderr)

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="MCP本地文件读取器服务器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False  # 禁用默认help，使用自定义help
    )
    
    # 传输模式选择
    transport_group = parser.add_mutually_exclusive_group(required=False)
    transport_group.add_argument(
        '--stdio',
        action='store_true',
        help='使用stdio传输模式 (推荐本地集成)'
    )
    transport_group.add_argument(
        '--http',
        action='store_true', 
        help='使用HTTP传输模式 (适用于远程调用)'
    )
    
    # HTTP模式相关参数
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='HTTP服务器监听地址 (默认: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=3001,
        help='HTTP服务器端口 (默认: 3001)'
    )
    
    # 帮助选项
    parser.add_argument(
        '-h', '--help',
        action='store_true',
        help='显示帮助信息'
    )
    
    args = parser.parse_args()
    
    # 处理帮助选项
    if args.help:
        show_help()
        sys.exit(0)
    
    # 如果没有指定传输模式，默认使用stdio模式
    if not args.stdio and not args.http:
        print("未指定传输模式，默认使用stdio模式", file=sys.stderr)
        print("提示: 使用 --help 查看更多选项", file=sys.stderr)
        args.stdio = True
    
    return args

async def run_stdio_server():
    """运行stdio模式服务器"""
    # stdio模式下不能输出到stdout，会干扰MCP通信
    # 所有输出都发送到stderr
    import sys
    print("启动MCP文件读取器 - stdio模式", file=sys.stderr)
    print("适用于本地集成和嵌入式部署", file=sys.stderr)
    
    # 动态导入stdio服务器模块
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    from mcp_stdio_server import main
    
    # 运行stdio服务器
    await main()

def run_http_server(host: str, port: int):
    """运行HTTP模式服务器"""
    print(f"启动MCP文件读取器 - HTTP模式", file=sys.stderr)
    print(f"服务地址: http://{host}:{port}/mcp", file=sys.stderr)
    print("适用于远程调用和Web集成", file=sys.stderr)
    
    # 动态导入HTTP服务器模块
    sys.path.insert(0, str(Path(__file__).parent / "src"))
    from mcp_http_server import SERVER_CONFIG, run_http_server as run_http
    
    # 更新服务器配置
    SERVER_CONFIG["host"] = host
    SERVER_CONFIG["port"] = port
    
    # 运行HTTP服务器
    run_http()

def main():
    """主入口函数"""
    try:
        args = parse_arguments()
        
        if args.stdio:
            # stdio模式
            asyncio.run(run_stdio_server())
        elif args.http:
            # HTTP模式
            run_http_server(args.host, args.port)
        
    except KeyboardInterrupt:
        print("\n服务器已停止", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"启动服务器失败: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()