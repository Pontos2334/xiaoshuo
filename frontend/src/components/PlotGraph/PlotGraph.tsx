'use client';

import { useCallback, useMemo, useState, useRef, useEffect } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  useReactFlow,
  Panel,
  Controls,
} from '@xyflow/react';
import dagre from 'dagre';
import '@xyflow/react/dist/style.css';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { usePlotStore } from '@/stores';
import { PlotNode as PlotNodeType, PlotConnection } from '@/types';
import { RefreshCw, Edit2, Trash2, Loader2 } from 'lucide-react';
import { PlotNodeComponent } from './PlotNode';

interface PlotGraphProps {
  onAnalyze?: () => void;
  isAnalyzing?: boolean;
}

const nodeTypes = {
  plotNode: PlotNodeComponent,
};

// Dagre 布局配置
const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const nodeWidth = 180;
const nodeHeight = 100;

// 辅助函数：从章节字符串中提取数字用于排序
function extractChapterNumber(chapter: string): number {
  if (!chapter) return 999;
  const match = chapter.match(/\d+/);
  return match ? parseInt(match[0], 10) : 999;
}

function getLayoutedElements(nodes: Node[], edges: Edge[], direction = 'LR') {
  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({ rankdir: direction, nodesep: 120, ranksep: 180 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}

// 辅助函数：通过标题或ID找到真正的情节ID
function findPlotId(ref: string, nodes: PlotNodeType[]): string | null {
  if (!ref || !nodes.length) return null;

  // 直接匹配ID
  const directMatch = nodes.find(n => n.id === ref);
  if (directMatch) return directMatch.id;

  // 通过标题匹配
  const titleMatch = nodes.find(n => n.title === ref);
  if (titleMatch) return titleMatch.id;

  // 模糊匹配
  for (const node of nodes) {
    if (node.title && (node.title.includes(ref) || ref.includes(node.title))) {
      return node.id;
    }
  }

  return null;
}

export function PlotGraph({ onAnalyze, isAnalyzing }: PlotGraphProps) {
  const { plotNodes, plotConnections, selectedPlotNode, setSelectedPlotNode, deletePlotNode } = usePlotStore();
  const plotNodesRef = useRef(plotNodes);

  useEffect(() => {
    plotNodesRef.current = plotNodes;
  }, [plotNodes]);

  // 转换为 React Flow 格式并应用布局
  const { initialNodes, initialEdges } = useMemo(() => {
    if (plotNodes.length === 0) {
      return { initialNodes: [], initialEdges: [] };
    }

    // 按章节排序
    const sortedNodes = [...plotNodes].sort((a, b) =>
      extractChapterNumber(a.chapter) - extractChapterNumber(b.chapter)
    );

    const nodes: Node[] = sortedNodes.map((node) => ({
      id: node.id,
      type: 'plotNode',
      position: { x: 0, y: 0 },
      data: node,
    }));

    // 连接样式
    const connectionStyles: Record<string, { stroke: string; label: string }> = {
      'cause': { stroke: '#ef4444', label: '因果' },
      'parallel': { stroke: '#22c55e', label: '并行' },
      'foreshadow': { stroke: '#f59e0b', label: '伏笔' },
      'flashback': { stroke: '#8b5cf6', label: '闪回' },
      'next': { stroke: '#3b82f6', label: '后续' },
    };

    // 过滤有效的边
    const validEdges: Edge[] = [];

    // 首先添加数据库中的连接
    plotConnections.forEach((conn) => {
      let sourceId = conn.sourceId || (conn as PlotConnection & { source_id?: string }).source_id;
      let targetId = conn.targetId || (conn as PlotConnection & { target_id?: string }).target_id;

      // 如果不是有效的ID，尝试通过引用查找
      if (sourceId && !plotNodes.find(n => n.id === sourceId)) {
        const found = findPlotId(sourceId, plotNodes);
        if (found) sourceId = found;
      }
      if (targetId && !plotNodes.find(n => n.id === targetId)) {
        const found = findPlotId(targetId, plotNodes);
        if (found) targetId = found;
      }

      // 只有当两个ID都有效时才添加边
      if (sourceId && targetId &&
          plotNodes.find(n => n.id === sourceId) &&
          plotNodes.find(n => n.id === targetId) &&
          sourceId !== targetId) {
        const connType = conn.connectionType || (conn as PlotConnection & { connection_type?: string }).connection_type || 'next';
        const style = connectionStyles[connType] || { stroke: '#94a3b8', label: '关联' };

        validEdges.push({
          id: conn.id,
          source: sourceId,
          target: targetId,
          label: style.label,
          style: { stroke: style.stroke, strokeWidth: 2 },
          labelStyle: { fill: style.stroke, fontWeight: 500, fontSize: 11 },
          labelBgStyle: { fill: '#fff', fillOpacity: 0.9 },
          labelBgPadding: [4, 2] as [number, number],
          markerEnd: { type: MarkerType.ArrowClosed, color: style.stroke },
        });
      }
    });

    // 如果没有连接数据，自动生成主线连接（虚线）
    if (validEdges.length === 0 && sortedNodes.length >= 2) {
      for (let i = 0; i < sortedNodes.length - 1; i++) {
        validEdges.push({
          id: `auto-${sortedNodes[i].id}-${sortedNodes[i + 1].id}`,
          source: sortedNodes[i].id,
          target: sortedNodes[i + 1].id,
          label: '时间线',
          style: { stroke: '#94a3b8', strokeWidth: 2, strokeDasharray: '5,5' },
          labelStyle: { fill: '#94a3b8', fontWeight: 500, fontSize: 11 },
          labelBgStyle: { fill: '#fff', fillOpacity: 0.9 },
          labelBgPadding: [4, 2] as [number, number],
          markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
        });
      }
    }

    // 应用 dagre 布局（从左到右，符合时间线）
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      nodes,
      validEdges,
      'LR'
    );

    return { initialNodes: layoutedNodes, initialEdges: layoutedEdges };
  }, [plotNodes, plotConnections]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // 当数据变化时更新节点和边
  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const plotNode = plotNodesRef.current.find((p) => p.id === node.id);
      if (plotNode) {
        setSelectedPlotNode(plotNode);
      }
    },
    [setSelectedPlotNode]
  );

  const handleDelete = useCallback(
    (id: string) => {
      if (confirm('确定要删除这个情节节点吗？')) {
        deletePlotNode(id);
      }
    },
    [deletePlotNode]
  );

  return (
    <div className="h-full flex gap-4">
      {/* 情节图谱区域 */}
      <Card className="flex-1">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>情节关联图</CardTitle>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={onAnalyze} disabled={isAnalyzing}>
              {isAnalyzing ? (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-1" />
              )}
              {isAnalyzing ? '分析中...' : 'AI分析'}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="h-[500px]">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              nodeTypes={nodeTypes}
              fitView
              minZoom={0.3}
              maxZoom={2}
            >
              <Controls showInteractive={false} />
              <MiniMap
                pannable
                zoomable
                nodeColor={(node) => {
                  const emotions: Record<string, string> = {
                    '紧张': '#fecaca',
                    '温馨': '#fbcfe8',
                    '悲伤': '#bfdbfe',
                    '欢乐': '#fef08a',
                    '愤怒': '#fed7aa',
                    '平静': '#bbf7d0',
                  };
                  const data = node.data as PlotNodeType;
                  return emotions[data?.emotion] || '#e5e7eb';
                }}
              />
              <Background gap={16} size={1} />
            </ReactFlow>
          </div>
        </CardContent>
      </Card>

      {/* 情节详情面板 */}
      <Card className="w-80">
        <CardHeader>
          <CardTitle>
            {selectedPlotNode ? selectedPlotNode.title : '选择情节'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {selectedPlotNode ? (
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium mb-1">章节</h4>
                <p className="text-sm text-muted-foreground">第{selectedPlotNode.chapter}章</p>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-1">情节概述</h4>
                <p className="text-sm text-muted-foreground">{selectedPlotNode.summary}</p>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-1">涉及人物</h4>
                <div className="flex flex-wrap gap-1">
                  {(selectedPlotNode.characters || []).map((char, i) => (
                    <Badge key={i} variant="outline">{char}</Badge>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-1">主要情绪</h4>
                <Badge>{selectedPlotNode.emotion}</Badge>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-1">重要程度</h4>
                <div className="flex gap-1">
                  {[...Array(10)].map((_, i) => (
                    <div
                      key={i}
                      className={`w-2 h-4 rounded ${
                        i < (selectedPlotNode.importance || 5) ? 'bg-primary' : 'bg-muted'
                      }`}
                    />
                  ))}
                </div>
              </div>

              <div className="flex gap-2 pt-4">
                <Button variant="outline" size="sm">
                  <Edit2 className="h-4 w-4" />
                  编辑
                </Button>
                <Button variant="destructive" size="sm" onClick={() => handleDelete(selectedPlotNode.id)}>
                  <Trash2 className="h-4 w-4" />
                  删除
                </Button>
              </div>
            </div>
          ) : (
            <div className="text-center text-muted-foreground py-8">
              点击图谱中的情节节点查看详情
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
