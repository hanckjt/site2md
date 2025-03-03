#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
爬虫核心逻辑模块
负责网站爬取和URL管理
'''

import re
import time
from pathlib import Path
from urllib.parse import urlparse, urljoin
from collections import deque
from tqdm import tqdm
from loguru import logger
from botasaurus.browser import browser, Driver
from utils import extract_domain, sanitize_filename
from markdown_converter import convert_to_markdown, merge_markdown_files


class WebsiteCrawler:
    '''
    网站爬虫类

    负责管理爬取过程、URL队列和已访问URL集合
    '''

    def __init__(self, start_url, output_dir='output', max_depth=3, domain_limit=None, parallel=10, use_browser=True):
        '''
        初始化网站爬虫

        参数:
            start_url (str): 起始URL
            output_dir (str): 输出目录路径
            max_depth (int): 最大爬取深度
            domain_limit (str): 限制爬取的域名，None表示使用起始URL的域名
            parallel (int): 并行爬取数量
            use_browser (bool): 是否使用浏览器模式爬取
        '''
        self.start_url = start_url
        self.output_dir = Path(output_dir)
        self.pages_dir = self.output_dir / 'pages'
        self.max_depth = max_depth
        self.parallel = parallel
        self.use_browser = use_browser

        # 如果未指定域名限制，使用起始URL的域名
        if domain_limit:
            self.domain_limit = domain_limit
        else:
            self.domain_limit = extract_domain(start_url)

        logger.info(f'域名限制设置为: {self.domain_limit}')

        # 待爬取的URL队列 (url, depth)
        self.url_queue = deque([(start_url, 0)])

        # 已访问的URL集合
        self.visited_urls = set()

        # 成功爬取的URL集合
        self.successful_urls = set()

        # 待处理的批次 - 用于并行处理
        self.batch_pending = []

        # 进度条
        self.pbar = None

    def start(self):
        '''
        开始爬取网站
        '''
        logger.info(f'开始爬取网站: {self.start_url}')
        logger.info(f'最大深度: {self.max_depth}')
        logger.info(f'并行数量: {self.parallel}')

        # 确保输出目录存在
        self.pages_dir.mkdir(parents=True, exist_ok=True)

        # 创建进度条
        self.pbar = tqdm(desc='爬取进度', unit='页', position=0, leave=True)

        # 爬取网站
        self._crawl_with_browser()

        logger.info(f'爬取完成，共爬取 {len(self.successful_urls)} 个页面')

        # 如果成功爬取了页面，则合并markdown文件
        if self.successful_urls:
            self._merge_markdown_files()
        else:
            logger.warning('没有成功爬取任何页面，跳过合并步骤')

        # 关闭进度条
        self.pbar.close()

    def _crawl_with_browser(self):
        '''
        使用浏览器模式爬取网站
        '''
        @browser(parallel=self.parallel, cache=True, close_on_crash=True, block_images_and_css=True, max_retry=3)
        def scrape_single_page(driver: Driver, data):
            '''
            爬取单个页面
            
            参数:
                driver: 浏览器驱动
                data: 包含 url 和 depth 的元组
            '''
            url, depth = data
            result = self._crawl_single_url(driver, url, depth)
            return {"url": url, "result": result}
        
        # 处理队列中的URL，单个爬取
        while self.url_queue:
            url, depth = self.url_queue.popleft()
            if url not in self.visited_urls:
                self.visited_urls.add(url)
                logger.info(f'爬取页面: {url} (深度: {depth})')
                scrape_single_page((url, depth))

    def _crawl_single_url(self, driver, url, depth):
        '''
        爬取单个URL
        
        参数:
            driver: 浏览器驱动
            url: 要爬取的URL
            depth: 当前深度
            
        返回:
            bool: 爬取是否成功
        '''
        try:
            logger.debug(f'开始爬取 {url} (深度: {depth})')

            # 通过Google引用方式访问，避免一些防爬虫措施
            driver.google_get(url, bypass_cloudflare=True)

            # 等待页面加载完成
            driver.short_random_sleep()

            # 获取HTML内容
            html = driver.page_html
            logger.debug(f'成功获取 {url} 的HTML内容，大小: {len(html)} 字节')

            # 如果深度未超过最大深度，提取链接
            next_depth = depth + 1
            if next_depth <= self.max_depth:
                new_urls = self._extract_links(url, html)
                logger.debug(f'从 {url} 提取了 {len(new_urls)} 个新链接')
                self._add_urls_to_queue(new_urls, next_depth)

            # 转换为Markdown并保存
            markdown_file = self._save_as_markdown(url, html)
            if markdown_file:
                self.successful_urls.add(url)
                self.pbar.update(1)

            return True
        except Exception as e:
            logger.error(f'爬取 {url} 时发生错误: {str(e)}')
            return False

    def _extract_links(self, base_url, html):
        '''
        从HTML中提取链接

        参数:
            base_url (str): 基础URL，用于解析相对路径
            html (str): 网页HTML内容

        返回:
            list: 提取的URL列表
        '''
        try:
            # 确保有内容可处理
            if not html or len(html.strip()) == 0:
                logger.warning(f'从 {base_url} 提取链接失败: HTML内容为空')
                return []

            # 使用正则表达式提取链接
            links_pattern = r'<a[^>]+href=["\'](.*?)["\']'
            raw_urls = re.findall(links_pattern, html)

            # 如果没有找到链接，尝试使用BeautifulSoup
            if not raw_urls:
                logger.debug(f'在 {base_url} 中未通过正则表达式找到链接，尝试使用BeautifulSoup')
                from bs4 import BeautifulSoup

                try:
                    soup = BeautifulSoup(html, 'html.parser')
                    raw_urls = [a.get('href') for a in soup.find_all('a', href=True)]
                except Exception as e:
                    logger.error(f'使用BeautifulSoup提取链接失败: {str(e)}')
                    return []

            # 处理相对路径和过滤非目标域名
            processed_urls = []
            for url in raw_urls:
                # 跳过None和空链接
                if not url:
                    continue

                # 跳过锚点链接、JavaScript链接
                if url.startswith('#') or url.startswith('javascript:'):
                    continue

                # 跳过邮件链接
                if url.startswith('mailto:'):
                    continue

                # 转换为绝对路径
                try:
                    absolute_url = urljoin(base_url, url)
                except Exception as e:
                    logger.warning(f'转换URL {url} 为绝对路径时出错: {str(e)}')
                    continue

                # 确保URL格式正确
                parsed_url = urlparse(absolute_url)
                if not parsed_url.scheme or not parsed_url.netloc:
                    continue

                # 只保留指定域名的URL
                if self.domain_limit in extract_domain(absolute_url):
                    processed_urls.append(absolute_url)

            # 去重
            unique_urls = list(set(processed_urls))
            logger.debug(f'从 {base_url} 提取了 {len(unique_urls)} 个有效链接')
            return unique_urls
        except Exception as e:
            logger.error(f'提取链接时发生错误: {str(e)}')
            return []

    def _add_urls_to_queue(self, urls, depth):
        '''
        将URL添加到队列

        参数:
            urls (list): URL列表
            depth (int): URL的深度
        '''
        added_count = 0
        for url in urls:
            # 规范化URL
            url = url.split('#')[0]  # 移除锚点部分

            if url not in self.visited_urls:
                self.url_queue.append((url, depth))
                added_count += 1

        logger.debug(f'添加了 {added_count} 个新URL到队列，当前队列长度: {len(self.url_queue)}')

    def _save_as_markdown(self, url, html):
        '''
        将HTML转换为Markdown并保存

        参数:
            url (str): 页面URL
            html (str): 页面HTML内容

        返回:
            Path: 保存的文件路径，失败则返回None
        '''
        try:
            # 检查HTML内容
            if not html or len(html.strip()) < 50:  # 假设少于50个字符的HTML内容可能是无效的
                logger.warning(f'页面 {url} HTML内容过少 ({len(html) if html else 0} 字节)，可能爬取失败')
                failed_file = self.output_dir / 'failed_pages.txt'
                with open(failed_file, 'a', encoding='utf-8') as f:
                    f.write(f'{url}\n')
                return None

            # 生成文件名
            filename = sanitize_filename(url)
            filepath = self.pages_dir / f'{filename}.md'

            # 转换为Markdown
            markdown_content = convert_to_markdown(url, html)

            # 检查Markdown内容
            if not markdown_content or len(markdown_content.strip()) < 10:
                logger.warning(f'页面 {url} 转换后的Markdown内容过少，可能转换失败')
                return None

            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            logger.debug(f'已保存 {url} 到 {filepath}')
            return filepath
        except Exception as e:
            logger.error(f'保存 {url} 为Markdown时发生错误: {str(e)}')
            return None

    def _merge_markdown_files(self):
        '''
        合并所有Markdown文件为一个文件
        '''
        logger.info('开始合并Markdown文件...')
        try:
            output_file = self.output_dir / 'merged_content.md'
            merge_markdown_files(self.pages_dir, output_file, self.start_url)
            logger.info(f'合并完成，文件保存至: {output_file}')
        except Exception as e:
            logger.error(f'合并Markdown文件时发生错误: {str(e)}')

