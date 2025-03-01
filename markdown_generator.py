from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime
from loguru import logger
import hashlib
import re

class MarkdownGenerator:
    """处理将爬取的网站内容转换为Markdown文档"""
    
    def __init__(self, output_dir):
        """
        初始化Markdown生成器。
        
        :param output_dir: 输出目录路径
        :type output_dir: str or Path
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _create_unique_anchor(self, title, url):
        """
        为标题创建唯一的锚点ID。
        
        :param title: 页面标题
        :type title: str
        :param url: 页面URL
        :type url: str
        :return: 唯一锚点ID
        :rtype: str
        """
        # 创建锚点ID
        anchor = title.replace(' ', '-').lower()
        # 为确保唯一性，可以加入URL的哈希
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        return f"{anchor}-{url_hash}"
    
    def generate_markdown(self, pages, start_url, url_scope, depth):
        """
        将页面内容生成为Markdown文档。
        
        :param pages: 页面内容字典 {URL: (标题, 内容)}
        :type pages: dict
        :param start_url: 起始URL
        :type start_url: str
        :param url_scope: URL范围
        :type url_scope: str
        :param depth: 爬取深度
        :type depth: int
        :return: 生成的Markdown文件路径
        :rtype: Path or None
        """
        if not pages:
            logger.warning('没有可生成的页面内容')
            return None
        
        # 生成网站域名作为文件名的一部分
        domain = urlparse(start_url).netloc
        safe_domain = domain.replace('.', '_')
        
        # 创建输出文件路径
        output_md_file = self.output_dir / f'{safe_domain}_site.md'
        
        logger.info(f'开始生成Markdown文件: {output_md_file}')
        
        try:
            # 组织为单个Markdown文件
            with open(output_md_file, 'w', encoding='utf-8') as f:
                # 添加文档标题和元信息
                f.write(f'# {domain} 网站内容\n\n')
                f.write(f'源网站: [{start_url}]({start_url})\n\n')
                f.write(f'爬取时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n')
                f.write(f'爬取深度: {depth}\n\n')
                f.write(f'URL范围: {url_scope}\n\n')
                
                f.write('---\n\n')
                
                # 创建目录
                f.write('## 目录\n\n')
                
                # 首先处理首页
                if start_url in pages:
                    f.write(f'* [首页](#首页)\n')
                
                # 然后处理其他页面，按标题排序
                sorted_pages = sorted(
                    [(url, title, content) for url, (title, content) in pages.items() if url != start_url], 
                    key=lambda x: x[1]  # 按标题排序
                )
                
                for url, title, _ in sorted_pages:
                    # 创建唯一锚点ID
                    anchor = self._create_unique_anchor(title, url)
                    # 添加目录项
                    f.write(f'* [{title}](#{anchor})\n')
                
                f.write('\n---\n\n')
                
                # 首先处理首页内容
                if start_url in pages:
                    title, content = pages[start_url]
                    
                    f.write(f'## 首页\n\n')
                    f.write(f'URL: [{start_url}]({start_url})\n\n')
                    f.write(f'{content}\n\n')
                    f.write('---\n\n')
                
                # 然后处理其他页面内容
                for url, title, content in sorted_pages:
                    # 创建页面锚点
                    anchor = self._create_unique_anchor(title, url)
                    
                    # 写入页面内容
                    f.write(f'## {title}\n\n')
                    f.write(f'URL: [{url}]({url})\n\n')
                    f.write(f'{content}\n\n')
                    f.write('---\n\n')
            
            logger.info(f'Markdown文件生成完成: {output_md_file}')
            return output_md_file
            
        except Exception as e:
            logger.error(f'生成Markdown文件时出错: {str(e)}', exc_info=True)
            return None
