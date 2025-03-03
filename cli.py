#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
命令行接口模块
处理命令行参数解析
'''

import argparse
import sys
from pathlib import Path
from utils import check_url_accessibility
import shutil


def parse_args():
    '''
    解析命令行参数

    返回:
        argparse.Namespace: 解析后的命令行参数
    '''
    parser = argparse.ArgumentParser(
        description='爬取网站并转换为Markdown文档',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s https://example.com -o output_dir -d 2
  %(prog)s https://blog.example.com -o blog_markdown --domain blog.example.com
  %(prog)s https://docs.example.com -o docs --browser -p 5
  %(prog)s https://example.com --test  # 只爬取测试页面
        ''',
    )

    parser.add_argument('url', help='要爬取的网站起始URL')

    parser.add_argument('-o', '--output', default='output', help='输出目录，默认为"output"')

    parser.add_argument('-d', '--depth', type=int, default=3, help='爬取深度，默认为3')

    parser.add_argument('--domain', help='限制爬取的域名，不指定则使用起始URL的域名')

    parser.add_argument('-p', '--parallel', type=int, default=10, help='并行爬取的数量，默认为10')

    parser.add_argument('-b', '--browser', action='store_true', help='使用浏览器模式爬取，适用于JavaScript渲染网站和有防爬虫机制的网站')

    parser.add_argument('--debug', action='store_true', help='启用调试模式，输出更详细的日志')

    parser.add_argument('--test', action='store_true', help='测试模式，只爬取起始页面')

    parser.add_argument('-f', '--force', action='store_true', help='强制覆盖现有的输出目录')

    args = parser.parse_args()

    # 检查URL是否可访问
    if not check_url_accessibility(args.url):
        print(f"警告: URL '{args.url}' 似乎无法访问。请检查URL是否正确，或者网站可能阻止了访问。")
        answer = input("是否仍然继续? (y/n): ")
        if answer.lower() != 'y':
            print("爬取已取消。")
            sys.exit(0)

    # 测试模式下设置深度为0
    if args.test:
        args.depth = 0
        print("测试模式: 只爬取起始页面")

    # 检查输出目录是否已存在
    output_path = Path(args.output)
    if output_path.exists() and not args.force:
        print(f"警告：输出目录'{args.output}'已存在。")
        answer = input("是否覆盖现有目录? (y/n): ")
        if answer.lower() != 'y':
            print("爬取已取消。")
            sys.exit(0)
        else:
            # 清空已存在的目录
            print(f"正在清空目录：{args.output}")
            shutil.rmtree(output_path)
            output_path.mkdir(exist_ok=True)
            print(f"目录已重新创建：{args.output}")

    return args
