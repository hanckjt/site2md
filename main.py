#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
主程序入口文件
用于启动网站爬取转Markdown任务
'''

import sys
import platform
import shutil
import os
from pathlib import Path
from loguru import logger
from cli import parse_args


def setup_logger(debug=False, log_dir='logs'):
    '''
    配置日志记录器

    设置日志格式和输出级别

    参数:
        debug (bool): 是否启用调试模式
        log_dir (str): 日志文件目录
    '''
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # 移除默认日志处理器
    logger.remove()

    # 设置日志级别
    log_level = "DEBUG" if debug else "INFO"

    # 添加控制台处理器
    logger.add(
        sys.stderr,
        format='<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>',
        level=log_level,
    )

    # 添加文件处理器
    logger.add(
        log_path / 'web_to_markdown_{time:YYYY-MM-DD}.log', rotation='10 MB', level="DEBUG", compression='zip', enqueue=True  # 文件始终记录DEBUG级别
    )

    if debug:
        logger.info("调试模式已启用，将输出详细日志")
    else:
        logger.info("运行在正常模式，调试日志将只写入日志文件")


def main():
    '''
    主程序入口函数

    解析命令行参数并启动爬取任务
    '''
    args = parse_args()

    # 设置日志
    setup_logger(debug=args.debug)

    logger.info(f"开始执行网站爬取任务，目标URL: {args.url}")

    # 打印系统信息
    logger.info(f"系统信息: {platform.system()} {platform.release()} ({platform.architecture()[0]})")
    logger.info(f"Python版本: {platform.python_version()}")

    # 导入爬虫模块
    from crawler import WebsiteCrawler

    # 打印参数信息
    logger.info(f"参数配置: 输出目录={args.output}, 最大深度={args.depth}, 并行数={args.parallel}")

    # 创建爬虫实例
    crawler = WebsiteCrawler(
        start_url=args.url, output_dir=args.output, max_depth=args.depth, domain_limit=args.domain, parallel=args.parallel, use_browser=args.browser
    )

    try:
        # 启动爬取
        crawler.start()

        # 查看结果
        if crawler.successful_urls:
            logger.success(f"爬取完成，成功爬取了 {len(crawler.successful_urls)} 个页面")
            output_path = Path(args.output) / 'merged_content.md'
            logger.info(f"合并后的Markdown文件位于: {output_path}")
        else:
            logger.error("爬取失败，未能成功爬取任何页面")
            logger.warning("请检查URL是否正确，网站是否可访问，或尝试使用浏览器模式")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.warning('爬取任务被用户中断')
        sys.exit(1)
    except Exception as e:
        logger.exception(f'爬取过程中发生错误: {str(e)}')
        sys.exit(1)


if __name__ == '__main__':
    main()
