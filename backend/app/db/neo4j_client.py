from typing import Optional
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j 数据库客户端"""

    _instance: Optional["Neo4jClient"] = None

    def __init__(self):
        self.uri = settings.NEO4J_URI
        self.user = settings.NEO4J_USER
        self.password = settings.NEO4J_PASSWORD
        self.driver = None

        # 如果未启用 Neo4j，跳过连接
        if not settings.NEO4J_ENABLED:
            logger.info("Neo4j 未启用 (NEO4J_ENABLED=False)，使用 SQLite 作为唯一数据源")
            return

        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # 测试连接
            with self.driver.session() as session:
                session.run("RETURN 1").single()
            logger.info(f"Neo4j 连接成功: {self.uri}")
        except ServiceUnavailable as e:
            logger.error(f"Neo4j 连接失败: {e}")
            self.driver = None
        except Exception as e:
            logger.warning(f"Neo4j 初始化异常: {e}")
            self.driver = None

    @classmethod
    def get_instance(cls) -> "Neo4jClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def close(self):
        if self.driver:
            self.driver.close()

    def get_session(self):
        """获取数据库会话"""
        if not self.driver:
            raise RuntimeError("Neo4j 未连接")
        return self.driver.session()

    def run(self, query: str, parameters: dict = None):
        """执行 Cypher 查询"""
        with self.get_session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]

    def run_single(self, query: str, parameters: dict = None):
        """执行查询并返回单个结果"""
        with self.get_session() as session:
            result = session.run(query, parameters or {})
            record = result.single()
            return dict(record) if record else None

    def execute_query(self, query: str, parameters: dict = None):
        """执行 Cypher 查询（run 的别名，兼容不同调用方式）"""
        return self.run(query, parameters)

    def is_available(self) -> bool:
        """检查 Neo4j 是否可用"""
        if not self.driver:
            return False
        try:
            with self.driver.session() as session:
                session.run("RETURN 1").single()
            return True
        except Exception:
            return False


# 全局客户端实例
neo4j_client = Neo4jClient.get_instance()


def get_neo4j_client() -> Neo4jClient:
    """获取 Neo4j 客户端实例（兼容函数）"""
    return neo4j_client
