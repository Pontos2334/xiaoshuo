"""
GraphRAG 服务

提供基于 GraphRAG 风格的知识图谱构建功能
"""

from .novel_ontology_generator import NovelOntologyGenerator
from .novel_entity_extractor import NovelEntityExtractor
from .novel_graph_builder import NovelGraphBuilder

__all__ = [
    'NovelOntologyGenerator',
    'NovelEntityExtractor',
    'NovelGraphBuilder'
]
