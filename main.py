import argparse
import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse
from tqdm.asyncio import tqdm
from loguru import logger
import shutil

# 引入自定义类
from logger_setup import LoggerSetup
from crawler import WebsiteCrawler
from markdown_generator import MarkdownGenerator

async def async_main(args):
    """
    异步主函数，处理命令行参数并执行网站爬取和Markdown生成流程。

    :param args: 命令行参数
    :type args: argparse.Namespace
    :return: 退出码，0表示成功
    :rtype: int
    """
    # 检查输出目录是否存在
    output_dir = Path(args.output)
    if output_dir.exists() and not args.force:
        # 目录存在且未指定强制覆盖
        if not args.quiet:
            print(f"输出目录 '{output_dir}' 已存在。")
            choice = input("覆盖目录内容? [y/N]: ").strip().lower()
            if choice != 'y':
                print("操作已取消。")
                return 0
        else:
            logger.warning(f"输出目录 '{output_dir}' 已存在，操作已取消。使用 --force 参数覆盖。")
            return 0
        
        # 用户同意覆盖，先清空目录
        try:
            if output_dir.exists():
                for item in output_dir.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
        except Exception as e:
            logger.error(f"清空目录失败: {str(e)}")
            return 1
    
    # 配置日志系统
    log_dir = output_dir / 'logs'
    log_file = LoggerSetup.setup(log_dir, args.verbose)
    
    # 使用pathlib创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f'输出目录: {output_dir}')
    logger.debug(f'爬取配置 - URL: {args.url}, 深度: {args.depth}, 超时: {args.timeout}秒')
    
    # 处理URL范围限制
    url_scope = args.scope
    if not url_scope:
        # 如果没有明确指定范围，使用URL本身
        url_parsed = urlparse(args.url)
        url_scope = f'{url_parsed.scheme}://{url_parsed.netloc}'
    
    logger.info(f'URL范围限制: {url_scope}')

    try:
        # 创建爬虫实例
        crawler = WebsiteCrawler(
            max_depth=args.depth,
            timeout=args.timeout,
            verbose=args.verbose,
            url_scope=url_scope,
            output_dir=output_dir,
            max_concurrency=args.concurrency
        )
        
        # 爬取网站内容并直接转换为Markdown
        logger.info(f'开始爬取网站: {args.url}')
        pages = await crawler.crawl_website(args.url)

        # 处理爬取结果
        if pages:
            # 创建Markdown生成器
            markdown_gen = MarkdownGenerator(output_dir)
            
            # 生成Markdown文件
            logger.info('爬取完成，正在生成Markdown文件...')
            output_md_file = markdown_gen.generate_markdown(
                pages, 
                args.url, 
                url_scope, 
                args.depth
            )
            
            if output_md_file:
                logger.success(f'完成! Markdown文件已保存到: {output_md_file.absolute()}')
                logger.info(f'日志文件: {log_file}')
            else:
                logger.warning('生成Markdown文件失败')
        else:
            logger.warning('未找到可转换的页面')

    except Exception as e:
        logger.exception(f'处理过程中发生错误: {str(e)}')
        return 1

    return 0


def main():
    """
    程序入口点，解析命令行参数并启动异步主函数。
    
    :return: 退出码，0表示成功
    :rtype: int
    """
    parser = argparse.ArgumentParser(description='将整个网站内容保存为Markdown文档')
    parser.add_argument('url', help='要爬取的网站URL')
    parser.add_argument('-o', '--output', default='output', help='输出目录，默认为"output"')
    parser.add_argument('-d', '--depth', type=int, default=2, help='爬取深度，默认为2')
    parser.add_argument('-t', '--timeout', type=int, default=30, help='请求超时时间(秒)，默认为30')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细日志')
    parser.add_argument('-s', '--scope', help='URL范围限制，只爬取该前缀下的URL')
    parser.add_argument('-c', '--concurrency', type=int, default=5, help='并行爬取的任务数，默认为5')
    parser.add_argument('-f', '--force', action='store_true', help='强制覆盖输出目录')
    parser.add_argument('-q', '--quiet', action='store_true', help='静默模式，不询问确认')

    # 如果没有提供参数，显示帮助信息
    if len(sys.argv) == 1:
        parser.print_help()
        return 0

    args = parser.parse_args()

    # 运行异步主函数
    return asyncio.run(async_main(args))


if __name__ == '__main__':
    sys.exit(main())
