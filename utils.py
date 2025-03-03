#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
通用工具模块
提供辅助功能
'''

import re
import time
import requests
from pathlib import Path
from urllib.parse import urlparse, unquote
import unicodedata
import string
from loguru import logger


def extract_domain(url):
    '''
    从URL中提取域名

    参数:
        url (str): 完整URL

    返回:
        str: 提取的域名
    '''
    try:
        parsed_url = urlparse(url)
        # 返回netloc部分（域名+端口）
        return parsed_url.netloc
    except Exception as e:
        logger.error(f"提取域名出错: {str(e)}, URL: {url}")
        return ""


def sanitize_filename(url):
    '''
    将URL转换为安全的文件名

    参数:
        url (str): URL字符串

    返回:
        str: 安全的文件名
    '''
    try:
        # 解码URL编码的字符
        url = unquote(url)

        # 移除URL协议和域名部分
        parsed_url = urlparse(url)
        path = parsed_url.path

        # 如果路径为空，使用域名
        if not path or path == '/':
            # 对于根路径，使用域名+时间戳避免冲突
            path = parsed_url.netloc + "_index"

        # 添加查询参数（如果有）
        if parsed_url.query:
            path += '_' + parsed_url.query

        # 规范化Unicode字符
        path = unicodedata.normalize('NFKD', path)

        # 替换非法字符
        valid_chars = '-_.() %s%s' % (string.ascii_letters, string.digits)
        filename = ''.join(c if c in valid_chars else '_' for c in path)

        # 替换多个连续的下划线为一个
        filename = re.sub(r'_{2,}', '_', filename)

        # 移除首尾的下划线和点
        filename = filename.strip('_.')

        # 截断过长的文件名
        if len(filename) > 100:
            filename = filename[:100]

        # 确保文件名不为空
        if not filename:
            filename = f"page_{int(time.time())}"

        return filename
    except Exception as e:
        logger.error(f"处理文件名出错: {str(e)}, URL: {url}")
        # 出错时返回时间戳文件名
        return f"error_page_{int(time.time())}"


def check_url_accessibility(url, timeout=10):
    '''
    检查URL是否可访问

    参数:
        url (str): 要检查的URL
        timeout (int): 请求超时时间（秒）

    返回:
        bool: URL是否可访问
    '''
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.head(url, timeout=timeout, headers=headers, allow_redirects=True)
        return response.status_code < 400
    except Exception:
        return False


def get_file_size_mb(file_path):
    '''
    获取文件大小（MB）

    参数:
        file_path (Path或str): 文件路径

    返回:
        float: 文件大小（MB）
    '''
    path = Path(file_path)
    if not path.exists():
        return 0

    return path.stat().st_size / (1024 * 1024)
