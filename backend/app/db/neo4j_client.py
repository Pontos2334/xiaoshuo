import os
from typing import Optional
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable
import logging
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j 数据库客户端"""

    _instance: Optional["Neo4jClient"] = None

    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "10001026")

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


# 全局客户端实例
neo4j_client = Neo4jClient.get_instance()
