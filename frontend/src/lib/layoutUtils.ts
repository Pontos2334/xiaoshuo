import dagre from 'dagre';
import { Node, Edge } from '@xyflow/react';

export interface LayoutConfig {
  nodeWidth: number;
  nodeHeight: number;
  direction: 'TB' | 'LR' | 'BT' | 'RL';
  nodesep: number;
  ranksep: number;
}

const DEFAULT_CONFIG: LayoutConfig = {
  nodeWidth: 150,
  nodeHeight: 80,
  direction: 'LR',
  nodesep: 100,
  ranksep: 150,
};

/**
 * 使用 dagre 算法对节点和边进行自动布局
 */
export function getLayoutedElements<T extends Record<string, unknown>>(
  nodes: Node<T>[],
  edges: Edge[],
  config: Partial<LayoutConfig> = {}
): { nodes: Node<T>[]; edges: Edge[] } {
  const finalConfig = { ...DEFAULT_CONFIG, ...config };

  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  dagreGraph.setGraph({
    rankdir: finalConfig.direction,
    nodesep: finalConfig.nodesep,
    ranksep: finalConfig.ranksep,
  });

  // 添加节点
  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, {
      width: finalConfig.nodeWidth,
      height: finalConfig.nodeHeight,
    });
  });

  // 添加边
  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  // 执行布局计算
  dagre.layout(dagreGraph);

  // 应用计算后的位置
  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - finalConfig.nodeWidth / 2,
        y: nodeWithPosition.y - finalConfig.nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}

/**
 * 提取章节号，用于情节节点排序
 */
export function extractChapterNumber(chapter: string): number {
  if (!chapter) return 999;
  const match = chapter.match(/(\d+)/);
  return match ? parseInt(match[1], 10) : 999;
}
