# Site2MD - 网站爬取转Markdown工具

Site2MD是一个强大的网站爬取工具，可以将整个网站或网站的某一部分爬取并转换为Markdown格式，方便阅读、存档和内容提取。该工具特别适用于将技术文档、博客和其他基于文本的网站内容转换为易于管理的Markdown文档。

## 主要特性

- 🌐 **多页面爬取**：可以递归爬取网站，支持设置爬取深度
- 🚀 **并行处理**：支持多线程并行爬取，加快处理速度
- 🔒 **域名限制**：可以限制只爬取指定域名的内容
- 🌍 **浏览器模式**：基于Botasaurus实现真实浏览器环境爬取，支持JavaScript渲染的网站
- 🧹 **智能清理**：自动提取页面主要内容，过滤广告和导航等无关元素
- 📄 **内容合并**：将所有爬取的页面合并为一个完整的Markdown文档，包含目录和页面链接

## 安装

1. 克隆本仓库：

```bash
git clone https://github.com/yourusername/site2md.git
cd site2md
```

2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 确保已安装Chrome浏览器（用于浏览器模式爬取）

## 使用方法

### 基本用法

```bash
python main.py https://example.com -o output_dir
```

### 高级选项

```bash
python main.py https://example.com -o output_dir -d 2 --domain example.com -p 5 --browser
```

### 命令行参数

- `url`：要爬取的网站URL（必需）
- `-o, --output`：输出目录，默认为"output"
- `-d, --depth`：爬取深度，默认为3
- `--domain`：限制爬取的域名，不指定则使用起始URL的域名
- `-p, --parallel`：并行爬取的数量，默认为10
- `-b, --browser`：使用浏览器模式爬取，适用于JavaScript渲染网站和防爬虫机制
- `--debug`：启用调试模式，输出更详细的日志
- `--test`：测试模式，只爬取起始页面
- `-f, --force`：强制覆盖现有的输出目录

### 示例

1. 爬取网站并限制深度为2：

   ```bash
   python main.py https://example.com -o output -d 2
   ```
2. 爬取特定域名下的内容：

   ```bash
   python main.py https://blog.example.com -o blog_markdown --domain blog.example.com
   ```
3. 使用浏览器模式爬取JavaScript渲染网站：

   ```bash
   python main.py https://docs.example.com -o docs --browser -p 5
   ```
4. 测试模式，只爬取单个页面：

   ```bash
   python main.py https://example.com --test
   ```

## 输出结果

爬取完成后，将生成以下文件和目录：

- `output/`（输出根目录）
  - `pages/`（包含所有爬取页面的单独Markdown文件）
  - `merged_content.md`（所有页面合并后的完整文档）
  - `logs/`（包含运行日志）

## 项目结构

```
site2md/
├── main.py          # 主程序入口
├── crawler.py       # 爬虫核心逻辑
├── markdown_converter.py  # HTML到Markdown转换
├── utils.py         # 工具函数
├── cli.py           # 命令行接口
├── requirements.txt # 依赖列表
└── README.md        # 项目说明
```

## 依赖项

主要依赖：

- botasaurus (浏览器自动化)
- markitdown (HTML到Markdown转换)
- beautifulsoup4 (HTML解析)
- loguru (日志记录)
- tqdm (进度条显示)

详细依赖请查看 `requirements.txt`文件。

## 注意事项

- 请遵守网站的robots.txt规则和使用条款
- 适当设置爬取深度和并行数量，避免对目标网站造成过大负担
- 对于大型网站，建议使用测试模式先尝试单个页面的爬取效果

## 许可证

MIT License
