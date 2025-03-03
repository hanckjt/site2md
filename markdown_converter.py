#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Markdown转换模块
负责HTML到Markdown的转换和Markdown文件合并
'''

import io
import re
import tempfile
from pathlib import Path
from loguru import logger
from markitdown import MarkItDown
from bs4 import BeautifulSoup
import html2text


def convert_to_markdown(url, html):
    '''
    将HTML转换为Markdown

    参数:
        url (str): 页面URL
        html (str): 页面HTML内容

    返回:
        str: 转换后的Markdown内容
    '''
    logger.debug(f"开始转换页面: {url}, HTML大小: {len(html)} 字节")

    try:
        # 提取标题
        try:
            soup = BeautifulSoup(html, 'html.parser')
            title = soup.title.string.strip() if soup.title else url
            logger.debug(f"页面标题: {title}")
        except Exception as e:
            logger.warning(f"提取标题失败: {str(e)}")
            title = url

        # 直接使用html2text进行转换
        try:
            logger.debug("使用html2text进行转换")
            converter = html2text.HTML2Text()
            converter.ignore_links = False
            converter.ignore_images = False
            converter.ignore_tables = False
            converter.body_width = 0  # 不限制宽度
            markdown_content = converter.handle(html)

            logger.debug(f"html2text转换成功，生成了 {len(markdown_content)} 字节的Markdown内容")
        except Exception as e:
            logger.error(f"html2text转换失败: {str(e)}")

            # 如果html2text失败，尝试MarkItDown
            try:
                logger.debug("尝试使用MarkItDown进行转换")
                md = MarkItDown()

                # 创建一个临时文件
                with tempfile.NamedTemporaryFile(suffix='.html', mode='w+', encoding='utf-8', delete=False) as temp:
                    temp.write(html)
                    temp_name = temp.name

                # 转换HTML到Markdown
                result = md.convert(temp_name)

                # 删除临时文件
                Path(temp_name).unlink()

                if result and hasattr(result, 'text_content') and result.text_content:
                    markdown_content = result.text_content
                    logger.debug(f"MarkItDown转换成功，生成了 {len(markdown_content)} 字节的Markdown内容")
                else:
                    raise ValueError('MarkItDown返回了空结果')
            except Exception as e:
                logger.error(f"MarkItDown也转换失败: {str(e)}")
                # 如果两种方法都失败，返回基本内容
                markdown_content = f"# {title}\n\n**Source URL:** {url}\n\n**Error:** 无法转换内容\n\n"
                logger.warning("使用基本内容作为转换结果")

        # 添加页面标题和URL作为元数据
        metadata = f'# {title}\n\n**Source URL:** {url}\n\n---\n\n'

        full_content = metadata + markdown_content
        logger.debug(f"转换完成，最终Markdown大小: {len(full_content)} 字节")

        return full_content
    except Exception as e:
        logger.error(f'转换 {url} 为Markdown时发生错误: {str(e)}')
        # 如果转换失败，返回基本内容
        return f'# Failed to convert {url}\n\n**Source URL:** {url}\n\n**Error:** {str(e)}\n'


def merge_markdown_files(input_dir, output_file, root_url):
    '''
    合并目录下的所有Markdown文件

    参数:
        input_dir (Path或str): Markdown文件目录
        output_file (Path或str): 输出文件路径
        root_url (str): 网站根URL
    '''
    input_path = Path(input_dir)
    output_path = Path(output_file)
    
    try:
        # 列出所有Markdown文件
        files = list(input_path.glob('*.md'))

        if not files:
            logger.warning(f"合并失败: {input_path} 目录中没有找到Markdown文件")
            with open(output_path, 'w', encoding='utf-8') as outfile:
                outfile.write(f'# Website: {root_url}\n\n')
                outfile.write('*No content was successfully scraped.*\n\n')
            return

        logger.info(f"找到 {len(files)} 个Markdown文件，开始合并")

        with open(output_path, 'w', encoding='utf-8') as outfile:
            # 写入标题
            outfile.write(f'# Website: {root_url}\n\n')
            outfile.write(f'*Generated Markdown content from {len(files)} pages*\n\n')
            outfile.write('## Table of Contents\n\n')

            # 创建目录
            for i, file_path in enumerate(files, 1):
                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        # 读取第一行作为标题（假设是# 标题格式）
                        first_line = infile.readline().strip()
                        title = first_line[1:].strip() if first_line.startswith('#') else file_path.name

                        # 添加到目录
                        outfile.write(f'{i}. [{title}](#{i})\n')
                except Exception as e:
                    logger.warning(f'处理文件 {file_path} 目录条目时出错: {str(e)}')
                    outfile.write(f'{i}. [Error reading file: {file_path.name}](#{i})\n')

            outfile.write('\n---\n\n')

            # 写入内容
            for i, file_path in enumerate(files, 1):
                outfile.write(f'\n\n<a id="{i}"></a>\n\n')  # 添加锚点

                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        content = infile.read()
                        outfile.write(content)
                except Exception as e:
                    logger.warning(f'读取文件 {file_path} 内容时出错: {str(e)}')
                    outfile.write(f'# Error reading file: {file_path.name}\n\n**Error:** {str(e)}\n')

                outfile.write('\n\n---\n\n')

        logger.success(f'已将 {len(files)} 个Markdown文件合并到 {output_path}')
    except Exception as e:
        logger.error(f'合并Markdown文件时发生错误: {str(e)}')
        raise
