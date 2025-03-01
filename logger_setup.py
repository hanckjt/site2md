import sys
from pathlib import Path
from datetime import datetime
from loguru import logger

class LoggerSetup:
    """配置和管理日志系统"""
    
    @staticmethod
    def setup(log_dir, verbose=False):
        """
        配置loguru日志系统
        
        :param log_dir: 日志文件目录
        :type log_dir: str or Path
        :param verbose: 是否显示详细日志
        :type verbose: bool
        :return: 日志文件路径
        :rtype: Path
        """
        # 创建日志目录
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置日志格式
        log_format = '<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>(<cyan>{file}</cyan>:<cyan>{line}</cyan>) - <level>{message}</level>'
        
        # 清除默认处理器
        logger.remove()
        
        # 添加控制台处理器，根据verbose设置级别
        logger.add(
            sys.stderr, 
            format=log_format, 
            level='DEBUG' if verbose else 'INFO',
            colorize=True
        )
        
        # 添加文件处理器，记录所有级别的日志
        log_file = log_dir / f'site2md_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        logger.add(
            log_file,
            format=log_format,
            level='DEBUG',
            rotation='10 MB',  # 每10MB轮换一次
            retention='1 week'  # 保留1周的日志
        )
        
        logger.info(f'日志系统初始化完成，日志文件: {log_file}')
        return log_file
