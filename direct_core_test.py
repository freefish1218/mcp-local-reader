

import asyncio
import sys
from pathlib import Path
import os

# 将项目根目录添加到Python路径中，以便导入src模块
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.file_reader import FileReader, LocalReadRequest
from src.file_reader.utils import get_logger

# 初始化日志记录器
logger = get_logger("direct_core_test")

async def main():
    """
    直接调用FileReader来测试文件解析。
    """
    logger.info("开始直接调用FileReader进行测试...")

    # 1. 初始化FileReader
    # 使用默认配置，它将创建一个LocalFileStorageClient
    try:
        file_reader = FileReader()
        logger.info("FileReader初始化成功。")
    except Exception as e:
        logger.error(f"FileReader初始化失败: {e}")
        return

    # 2. 准备要解析的文件路径
    # 使用os.path.join来确保路径在不同操作系统上的兼容性
    file_to_parse = os.path.join(project_root, "AIBT作业缴交表.pdf")
    
    if not os.path.exists(file_to_parse):
        logger.error(f"测试文件未找到，请确保文件存在于: {file_to_parse}")
        return
        
    logger.info(f"目标解析文件: {file_to_parse}")

    # 3. 创建文件读取请求
    # LocalReadRequest需要一个包含file_paths的列表
    request = LocalReadRequest(file_paths=[file_to_parse])
    logger.info("LocalReadRequest创建成功。")

    # 4. 调用read_file方法
    try:
        logger.info("调用 read_file 方法...")
        response = await file_reader.read_file(request)
        logger.info("read_file 方法调用完成。")
    except Exception as e:
        logger.error(f"调用read_file时发生异常: {e}")
        return

    # 5. 打印结果
    print("\n" + "="*20 + " 解析结果 " + "="*20)
    if response.contents:
        logger.info("文件解析成功。")
        content = response.contents[0].content
        print("成功提取的内容:")
        print(content)
    elif response.failed:
        logger.warning("文件解析失败。")
        failed_info = response.failed[0]
        print("失败详情:")
        print(f"  - 资源ID: {failed_info.resource_id}")
        print(f"  - 失败类型: {failed_info.type.value}")
        print(f"  - 错误信息: {failed_info.error_message}")
    else:
        logger.error("未返回任何内容或错误信息，这是一个异常情况。")
        print("响应为空，没有成功内容也没有失败信息。")
    print("="*50 + "\n")


if __name__ == "__main__":
    # 在Windows上，需要设置正确的事件循环策略以避免与Proactor相关的错误
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # 运行异步主函数
    asyncio.run(main())
