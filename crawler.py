import json
import hashlib
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin, urldefrag
from loguru import logger
from tqdm.asyncio import tqdm
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.async_dispatcher import MemoryAdaptiveDispatcher, RateLimiter, CrawlerMonitor, DisplayMode


class WebsiteCrawler:
    """
    网站爬虫类，负责爬取网站内容并转换为Markdown格式。
    """
    
    def __init__(self, max_depth=2, timeout=30, verbose=False, batch_size=10, url_scope=None, output_dir=None, max_concurrency=5):
        """
        初始化网站爬虫。
        
        :param max_depth: 最大爬取深度
        :type max_depth: int
        :param timeout: 请求超时时间(秒)
        :type timeout: int
        :param verbose: 是否显示详细日志
        :type verbose: bool
        :param batch_size: 每批处理的页面数
        :type batch_size: int
        :param url_scope: URL范围限制，只爬取该前缀下的URL
        :type url_scope: str
        :param output_dir: 输出目录
        :type output_dir: str or Path
        :param max_concurrency: 最大并行任务数
        :type max_concurrency: int
        """
        self.max_depth = max_depth
        self.timeout = timeout
        self.verbose = verbose
        self.batch_size = batch_size
        self.url_scope = url_scope
        self.output_dir = Path(output_dir) if output_dir else Path('output')
        self.max_concurrency = max_concurrency
        self.pages_dir = None
        self.progress_bar = None
        
        # 内容指纹缓存，用于检测重复内容
        self.content_fingerprints = set()
        # 规范化URL映射表，用于识别实际上相同的URL
        self.canonical_urls = {}
    
    def setup_pages_directory(self, start_url):
        """
        设置页面存储目录。
        
        :param start_url: 起始URL
        :type start_url: str
        :return: 页面存储目录路径
        :rtype: Path
        """
        domain = urlparse(start_url).netloc
        safe_domain = domain.replace('.', '_')
        
        self.pages_dir = self.output_dir / 'pages'
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f'页面存储目录: {self.pages_dir}')
        return self.pages_dir
    
    def get_safe_filename(self, url):
        """
        将URL转换为安全的文件名。
        
        :param url: 要转换的URL
        :type url: str
        :return: 安全的文件名
        :rtype: str
        """
        # 使用URL的MD5哈希值作为文件名，避免路径过长问题
        url_hash = hashlib.md5(url.encode()).hexdigest()
        parsed = urlparse(url)
        path = parsed.path
        if not path or path == '/':
            path = 'index'
        else:
            # 去除前导和尾随斜杠，替换剩余斜杠
            path = path.strip('/').replace('/', '_')
        
        # 裁剪路径长度，防止文件名过长
        if len(path) > 50:
            path = path[:50]
        
        return f'{path}_{url_hash}.json'

    def normalize_url(self, url):
        """
        规范化URL，去除URL片段并标准化路径
        
        :param url: 要规范化的URL
        :type url: str
        :return: 规范化后的URL
        :rtype: str
        """
        # 去除URL片段(#部分)
        url_no_frag = urldefrag(url)[0]
        
        # 解析URL
        parsed = urlparse(url_no_frag)
        
        # 处理路径，确保路径以/结尾，如果是目录的话
        path = parsed.path
        if not path:
            path = '/'
        
        # 重建URL，不包含查询参数等
        normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
        
        # 去除重复的斜杠
        while '//' in normalized:
            normalized = normalized.replace('//', '/')
        
        # 确保有正确的协议分隔符
        normalized = normalized.replace('://', ':/').replace(':/', '://')
        
        return normalized
    
    def get_content_fingerprint(self, content):
        """
        生成内容的指纹，用于检测重复内容
        
        :param content: 页面内容
        :type content: str
        :return: 内容指纹
        :rtype: str
        """
        # 使用MD5计算内容哈希值
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    async def save_page(self, url, title, content):
        """
        将页面保存到输出目录。
        
        :param url: 页面URL
        :type url: str
        :param title: 页面标题
        :type title: str
        :param content: 页面内容（Markdown格式）
        :type content: str
        :return: 保存的文件路径或None（如果检测到重复内容）
        :rtype: Path or None
        :raises ValueError: 如果页面目录未设置
        """
        if not self.pages_dir:
            raise ValueError('Pages directory not set up')
        
        # 检查内容重复
        fingerprint = self.get_content_fingerprint(content)
        if fingerprint in self.content_fingerprints:
            logger.warning(f'检测到重复内容，跳过保存: {url}')
            return None
        
        # 添加到指纹集合
        self.content_fingerprints.add(fingerprint)
        
        # 规范化URL
        normalized_url = self.normalize_url(url)
        self.canonical_urls[url] = normalized_url
        
        filename = self.get_safe_filename(normalized_url)
        filepath = self.pages_dir / filename
        
        # 创建页面数据结构
        page_data = {
            'url': url,
            'normalized_url': normalized_url,
            'title': title,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'fingerprint': fingerprint
        }
        
        # 保存为JSON文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(page_data, f, ensure_ascii=False, indent=2)
        
        logger.debug(f'页面保存到: {filepath}')
        return filepath
    
    async def read_all_pages(self):
        """
        读取所有保存的页面文件。
        
        :return: 所有页面内容的字典 {URL: (标题, 内容)}
        :rtype: dict
        """
        if not self.pages_dir or not self.pages_dir.exists():
            logger.error('页面存储目录不存在')
            return {}
        
        all_pages = {}
        unique_fingerprints = set()  # 用于防止重复内容
        
        for page_file in self.pages_dir.glob('*.json'):
            logger.debug(f'读取页面文件: {page_file}')
            try:
                with open(page_file, 'r', encoding='utf-8') as f:
                    page_data = json.load(f)
                    url = page_data.get('url')
                    title = page_data.get('title')
                    content = page_data.get('content')
                    fingerprint = page_data.get('fingerprint')
                    
                    # 检查是否已有相同内容
                    if fingerprint and fingerprint not in unique_fingerprints:
                        unique_fingerprints.add(fingerprint)
                        if url and title and content:
                            # 使用规范化URL作为键，避免相同内容的不同URL版本
                            normalized_url = page_data.get('normalized_url', url)
                            all_pages[normalized_url] = (title, content)
                    else:
                        logger.debug(f'跳过重复内容: {url}')
            except Exception as e:
                logger.error(f'读取页面文件 {page_file} 失败: {str(e)}')
        
        return all_pages
    
    async def process_result(self, result):
        """
        处理爬取结果并保存页面。
        
        :param result: 爬取结果对象
        :type result: crawl4ai.CrawlerResult
        :return: 处理结果元组 (URL, 标题, 内容, 链接) 或 None
        :rtype: tuple or None
        """
        if not result.success:
            logger.warning(f'爬取页面失败: {result.url}, 错误: {result.error_message}')
            return None
        
        # 从结果中提取标题和Markdown内容
        if not result.markdown_v2:
            logger.warning(f'页面未返回Markdown内容: {result.url}')
            return None
        
        page_title = result.metadata.get('title', '无标题') if result.metadata else '无标题'
        
        # 提取Markdown内容，优先使用fit_markdown（更精简的内容）
        md_content = result.markdown_v2.fit_markdown or result.markdown_v2.raw_markdown
        
        # 创建页面的完整Markdown内容
        page_content = f'### 页面内容\n\n{md_content}'
        
        # 添加图片部分
        if result.media and 'images' in result.media and result.media['images']:
            page_content += '\n\n### 页面图片\n\n'
            for img in result.media['images']:
                src = img.get('src', '')
                alt = img.get('alt', '图片') or '图片'
                if src:
                    page_content += f'![{alt}]({src})\n\n'
        
        # 添加参考链接
        if result.links:
            page_content += '\n\n## 参考链接\n\n'
            
            # 处理内部链接
            links_processed = set()
            counter = 1
            
            for link_type in ['internal', 'external']:
                if link_type in result.links:
                    for link in result.links[link_type]:
                        href = link.get('href', '')
                        text = link.get('text', href) or href
                        
                        if href and href not in links_processed:
                            links_processed.add(href)
                            page_content += f'\n\n⟨{counter}⟩ {href}: {text}'
                            counter += 1
        
        # 直接保存到文件中，自动处理重复内容检测
        saved_path = await self.save_page(result.url, page_title, page_content)
        
        # 更新进度条
        if self.progress_bar:
            self.progress_bar.update(1)
        
        # 如果内容重复，则不返回结果
        if not saved_path:
            return None
            
        return result.url, page_title, page_content, result.links
    
    async def collect_links(self, processed_result, current_depth, to_crawl, visited, url_scope, base_domain):
        """
        从处理结果中收集链接。
        
        :param processed_result: 处理结果元组 (URL, 标题, 内容, 链接)
        :type processed_result: tuple
        :param current_depth: 当前爬取深度
        :type current_depth: int
        :param to_crawl: 待爬取URL列表
        :type to_crawl: list
        :param visited: 已访问URL集合
        :type visited: set
        :param url_scope: URL范围限制
        :type url_scope: str
        :param base_domain: 基础域名
        :type base_domain: str
        :return: 新收集的URL列表
        :rtype: list
        """
        if processed_result and current_depth < self.max_depth:
            _, _, _, links = processed_result
            
            if links and 'internal' in links:
                new_urls = []
                
                for link in links['internal']:
                    next_url = link.get('href', '')
                    
                    # 跳过空URL
                    if not next_url:
                        continue
                    
                    # 规范化URL，防止不同形式但实际相同的URL被重复爬取
                    normalized_url = self.normalize_url(next_url)
                    
                    # 如果规范化URL已处理过，跳过
                    if normalized_url in visited:
                        continue
                        
                    # 检查URL是否在允许范围内
                    url_parsed = urlparse(normalized_url)
                    
                    # 检查是否同一域名
                    if url_parsed.netloc != base_domain:
                        logger.debug(f'跳过非同域URL: {normalized_url}')
                        continue
                    
                    # 检查是否在URL范围内
                    if url_scope and not normalized_url.startswith(url_scope):
                        logger.debug(f'URL不在指定范围内，跳过: {normalized_url}')
                        continue
                    
                    # 添加规范化URL到待爬取队列
                    if normalized_url not in to_crawl:
                        new_urls.append(normalized_url)
                        to_crawl.append(normalized_url)
                        visited.add(normalized_url)
                        # 记录规范化映射
                        self.canonical_urls[next_url] = normalized_url
                
                return new_urls
        
        return []
    
    async def crawl_website(self, start_url):
        """
        使用crawl4ai爬取网站并生成Markdown内容。
        
        :param start_url: 起始URL
        :type start_url: str
        :return: 所有页面内容的字典 {URL: (标题, 内容)}
        :rtype: dict
        """
        # 设置页面存储目录
        self.setup_pages_directory(start_url)
        
        # 如果未指定URL范围，使用起始URL的域名
        if not self.url_scope:
            # 默认情况下，使用起始URL的域名作为范围
            base_parsed = urlparse(start_url)
            self.url_scope = f'{base_parsed.scheme}://{base_parsed.netloc}'
            logger.info(f'未指定URL范围，默认限制在: {self.url_scope}')
        else:
            logger.info(f'URL范围限制为: {self.url_scope}')
        
        # 获取基础域名，用于过滤非同域链接
        base_domain = urlparse(start_url).netloc
        
        # 配置浏览器 - 修正参数
        browser_config = BrowserConfig(
            headless=True, 
            text_mode=False,  # 允许加载图片
            verbose=self.verbose
        )

        # 创建Markdown生成策略
        markdown_generator = DefaultMarkdownGenerator(
            options={
                'citations': True,  # 使用学术风格的引用
                'image_desc_min_words': 30  # 图片描述的最小字数
            }
        )
        
        # 创建爬虫运行配置
        base_config = CrawlerRunConfig(
            word_count_threshold=50,  # 最小字数阈值
            wait_until='networkidle',  # 等待网络空闲后再处理
            markdown_generator=markdown_generator,
            exclude_external_links=False,  # 不排除外部链接，以便收集所有参考
            check_robots_txt=True,  # 遵守robots.txt规则
            verbose=self.verbose,
            cache_mode=CacheMode.ENABLED,  # 启用缓存以提高性能
            page_timeout=self.timeout * 1000  # 毫秒为单位
        )
        
        # 创建爬虫调度器，启用内存自适应并设置并行任务数
        dispatcher = MemoryAdaptiveDispatcher(
            memory_threshold_percent=80.0,  # 内存使用率超过80%时暂停
            check_interval=1.0,  # 每秒检查一次内存使用情况
            max_session_permit=self.max_concurrency,  # 最大并行任务数
            rate_limiter=RateLimiter(  # 设置请求频率限制
                base_delay=(0.5, 1.5),  # 请求间隔0.5到1.5秒
                max_delay=20.0,  # 最大延迟20秒
                max_retries=2  # 最多重试2次
            ),
            # 禁用监控显示，避免与进度条冲突
            monitor=None
        )
        
        # 规范化起始URL
        normalized_start_url = self.normalize_url(start_url)
        self.canonical_urls[start_url] = normalized_start_url
        
        # 已访问的URL集合（使用规范化URL）
        visited = set([normalized_start_url])
        # 待爬取的URL队列（使用规范化URL）
        to_crawl = [normalized_start_url]
        # 当前深度的URL队列
        current_level_urls = [normalized_start_url]
        # 当前深度
        current_depth = 0
        # 爬取成功的页面 {URL: (标题, 内容)}
        all_pages = {}
        
        # 统计数据
        total_urls = 1  # 至少有起始URL
        processed_urls = 0
        
        # 创建爬虫实例并开始爬取
        async with AsyncWebCrawler(config=browser_config) as crawler:
            while current_level_urls and current_depth <= self.max_depth:
                logger.info(f'开始爬取深度 {current_depth} 的页面，URL数量: {len(current_level_urls)}')
                
                # 创建进度条
                self.progress_bar = tqdm(
                    desc=f'深度 {current_depth} 爬取进度',
                    total=len(current_level_urls),
                    unit='页面',
                    colour='green'
                )
                
                # 使用crawl4ai的arun_many并启用streaming模式，实时处理结果
                run_config = base_config.clone()
                run_config.stream = True  # 开启流式处理
                
                # 爬取当前深度的所有URL
                next_level_urls = []
                
                # 使用arun_many进行并行爬取
                async for result in await crawler.arun_many(
                    urls=current_level_urls,
                    config=run_config,
                    dispatcher=dispatcher
                ):
                    processed_urls += 1
                    
                    # 处理爬取结果
                    processed_result = await self.process_result(result)
                    
                    if processed_result:
                        url, title, content, _ = processed_result
                        # 使用规范化URL作为key
                        normalized_url = self.canonical_urls.get(url, url)
                        all_pages[normalized_url] = (title, content)
                        
                        # 收集下一层的链接
                        new_urls = await self.collect_links(
                            processed_result, 
                            current_depth, 
                            to_crawl, 
                            visited,
                            self.url_scope,
                            base_domain
                        )
                        next_level_urls.extend(new_urls)
                        total_urls += len(new_urls)
                
                # 关闭当前深度的进度条
                self.progress_bar.close()
                self.progress_bar = None
                
                # 准备下一深度的爬取
                current_level_urls = next_level_urls
                current_depth += 1
        
        logger.info(f'爬取完成，总共处理 {processed_urls}/{total_urls} 个URL，成功获取 {len(all_pages)} 个页面')
        
        # 读取所有保存的页面
        return await self.read_all_pages()
