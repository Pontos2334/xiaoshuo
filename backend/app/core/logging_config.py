import logging
import sys

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "INFO"):
    """配置应用日志"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # 降低第三方库日志级别
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return logging.getLogger("app")


def get_logger(name: str) -> logging.Logger:
    """获取logger实例"""
    return logging.getLogger(name)
