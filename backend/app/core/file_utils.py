import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def safe_read_file(file_path: str, encoding: str = "utf-8") -> str:
    """安全读取文件，带异常处理"""
    try:
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return ""
        with open(file_path, "r", encoding=encoding) as f:
            return f.read()
    except UnicodeDecodeError as e:
        logger.error(f"文件编码错误: {file_path}, {e}")
        # 尝试其他编码
        try:
            with open(file_path, "r", encoding="gbk") as f:
                return f.read()
        except Exception:
            raise IOError(f"无法读取文件: {file_path}")
    except IOError as e:
        logger.error(f"文件读取错误: {file_path}, {e}")
        raise IOError(f"文件读取失败: {file_path}")


def safe_write_file(file_path: str, content: str, encoding: str = "utf-8") -> bool:
    """安全写入文件，带异常处理"""
    try:
        dir_path = os.path.dirname(file_path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(file_path, "w", encoding=encoding) as f:
            f.write(content)
        logger.info(f"文件写入成功: {file_path}")
        return True
    except IOError as e:
        logger.error(f"文件写入错误: {file_path}, {e}")
        raise IOError(f"文件写入失败: {file_path}")
