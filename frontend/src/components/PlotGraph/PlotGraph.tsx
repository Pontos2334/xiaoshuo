'use client';

import { useCallback, useMemo, useState, useRef } from 'react';
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
} from '@xyflow/react';
import { ZoomIn, ZoomOut, Maximize2, Lock, Unlock, RefreshCw, Loader2, Edit2, Trash2 } from 'lucide-react';
import '@xyflow/react/dist/style.css';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { usePlotStore } from '@/stores';
import { PlotNode as PlotNodeType, PlotConnection } from '@/types';

interface PlotGraphProps {
  onAnalyze?: () => void;
  isAnalyzing?: boolean;
}

// 情节节点组件
function PlotNodeComponent({ data }: { data: PlotNodeType }) {
  const emotionColors: Record<string, string> = {
    '紧张': 'bg-red-100 border-red-300',
    '温馨': 'bg-pink-100 border-pink-300',
    '悲伤': 'bg-blue-100 border-blue-300',
    '欢乐': 'bg-yellow-100 border-yellow-300',
    '愤怒': 'bg-orange-100 border-orange-300',
    '平静': 'bg-green-100 border-green-300',
  };

  return (
    <div className={`px-4 py-2 rounded-md border-2 min-w-[150px] ${emotionColors[data.emotion] || 'bg-gray-100 border-gray-300'}`}>
      <div className="font-semibold text-sm">{data.title}</div>
      <div className="text-xs text-muted-foreground">第{data.chapter}章</div>
      <div className="flex gap-1 mt-1">
        <Badge variant="outline" className="text-xs">{data.emotion}</Badge>
      </div>
    </div>
  );
}

const nodeTypes = {
  plotNode: PlotNodeComponent,
};

// 自定义中文控制面板
function CustomControls() {
  const { zoomIn, zoomOut, fitView, zoomTo } = useReactFlow();
  const [isLocked, setIsLocked] = useState(false);

  return (
    <Panel position="bottom-left" className="flex gap-1 bg-white rounded-md shadow-md p-1">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => zoomIn()}
        title="放大"
        className="h-8 w-8 p-0"
      >
        <ZoomIn className="h-4 w-4" />
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => zoomOut()}
        title="缩小"
        className="h-8 w-8 p-0"
      >
        <ZoomOut className="h-4 w-4" />
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => fitView()}
        title="适应视图"
        className="h-8 w-8 p-0"
      >
        <Maximize2 className="h-4 w-4" />
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => {
          setIsLocked(!isLocked);
          zoomTo(1);
        }}
        title={isLocked ? '解锁' : '锁定'}
        className="h-8 w-8 p-0"
      >
        {isLocked ? <Unlock className="h-4 w-4" /> : <Lock className="h-4 w-4" />}
      </Button>
    </Panel>
  );
}

// 辅助函数：从章节字符串中提取数字用于排序
function extractChapterNumber(chapter: string): number {
  if (!chapter) return 999;
  const match = chapter.match(/\d+/);
  return match ? parseInt(match[0], 10) : 999;
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

  // 模糊匹配（处理 "情节1ID"、"命运的开端ID" 等情况）
  for (const node of nodes) {
    if (node.title && (node.title.includes(ref) || ref.includes(node.title))) {
      return node.id;
    }
    // 处理 "情节1" 这种格式
    const plotNumMatch = ref.match(/情节(\d+)/);
    if (plotNumMatch) {
      const num = parseInt(plotNumMatch[1]);
      const sortedNodes = [...nodes].sort((a, b) =>
        extractChapterNumber(a.chapter) - extractChapterNumber(b.chapter)
      );
      if (sortedNodes[num - 1] && num <= sortedNodes.length) {
        return sortedNodes[num - 1].id;
      }
    }
  }

  return null;
}

export function PlotGraph({ onAnalyze, isAnalyzing }: PlotGraphProps) {
  const { plotNodes, plotConnections, selectedPlotNode, setSelectedPlotNode, updatePlotNode, deletePlotNode } = usePlotStore();
  const plotNodesRef = useRef(plotNodes);

  // 更新 ref
  useEffect(() => {
    plotNodesRef.current = plotNodes;
  }, [plotNodes]);

  // 转换为React Flow格式
  const initialNodes: Node[] = useMemo(() => {
    if (plotNodes.length === 0) return [];

    // 按章节排序
    const sortedNodes = [...plotNodes].sort((a, b) =>
      extractChapterNumber(a.chapter) - extractChapterNumber(b.chapter)
    );

    // 计算布局：按时间线从左到右排列
    const nodeWidth = 180;
    const nodeHeight = 100;
    const horizontalGap = 100;
    const verticalGap = 150;
    const nodesPerRow = 4;

    return sortedNodes.map((node, index) => {
      const row = Math.floor(index / nodesPerRow);
      const col = index % nodesPerRow;
      const x = col * (nodeWidth + horizontalGap) + 50;
      const y = row * (nodeHeight + verticalGap) + 50;

      return {
        id: node.id,
        type: 'plotNode',
        position: { x, y },
        data: node,
      };
    });
  }, [plotNodes]);

  const initialEdges: Edge[] = useMemo(() => {
    if (plotConnections.length === 0 || plotNodes.length === 0) return [];

    const connectionStyles: Record<string, { stroke: string; label: string }> = {
      'cause': { stroke: '#ef4444', label: '因果' },
      'parallel': { stroke: '#22c55e', label: '并行' },
      'foreshadow': { stroke: '#f59e0b', label: '伏笔' },
      'flashback': { stroke: '#8b5cf6', label: '闪回' },
      'next': { stroke: '#3b82f6', label: '后续' },
    };

    const validEdges: Edge[] = [];

    plotConnections.forEach((conn) => {
      let sourceId = conn.sourceId || conn.source_id;
      let targetId = conn.targetId || conn.target_id;

      // 如果不是有效的ID，尝试通过引用查找
      if (!plotNodes.find(n => n.id === sourceId)) {
        const found = findPlotId(sourceId, plotNodes);
        if (found) sourceId = found;
      }
      if (!plotNodes.find(n => n.id === targetId)) {
        const found = findPlotId(targetId, plotNodes);
        if (found) targetId = found;
      }

      // 只有当两个ID都有效时才添加边
      if (sourceId && targetId &&
          plotNodes.find(n => n.id === sourceId) &&
          plotNodes.find(n => n.id === targetId) &&
          sourceId !== targetId) {
        const connType = conn.connectionType || conn.connection_type || 'next';
        const style = connectionStyles[connType] || { stroke: '#94a3b8', label: '关联' };

        validEdges.push({
          id: conn.id,
          source: sourceId,
          target: targetId,
          label: style.label,
          style: { stroke: style.stroke, strokeWidth: 2 },
          labelStyle: { fill: style.stroke, fontWeight: 500 },
          markerEnd: { type: MarkerType.ArrowClosed, color: style.stroke },
        });
      }
    });

    return validEdges;
  }, [plotConnections, plotNodes]);

  // 自动生成主线连接（如果没有连接数据）
  const autoEdges: Edge[] = useMemo(() => {
    if (plotConnections.length > 0 || plotNodes.length < 2) return [];

    // 按章节排序后，自动连接相邻的情节
    const sortedNodes = [...plotNodes].sort((a, b) =>
      extractChapterNumber(a.chapter) - extractChapterNumber(b.chapter)
    );

    const edges: Edge[] = [];
    for (let i = 0; i < sortedNodes.length - 1; i++) {
      edges.push({
        id: `auto-${sortedNodes[i].id}-${sortedNodes[i + 1].id}`,
        source: sortedNodes[i].id,
        target: sortedNodes[i + 1].id,
        label: '后续',
        style: { stroke: '#3b82f6', strokeWidth: 2, strokeDasharray: '5,5' },
        labelStyle: { fill: '#3b82f6', fontWeight: 500 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#3b82f6' },
      });
    }
    return edges;
  }, [plotNodes, plotConnections]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // 合并边：初始边 + 自动生成的边
  useEffect(() => {
    const allEdges = [...initialEdges, ...autoEdges];
    setEdges(allEdges);
  }, [initialEdges, autoEdges, setEdges]);

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    const plotNode = plotNodesRef.current.find((p) => p.id === node.id);
    if (plotNode) {
      setSelectedPlotNode(plotNode);
    }
  }, [setSelectedPlotNode]);

  const handleDelete = (id: string) => {
    if (confirm('确定要删除这个情节节点吗？')) {
      deletePlotNode(id);
    }
  };

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
            >
              <CustomControls />
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
              <Background />
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
                        i < selectedPlotNode.importance ? 'bg-primary' : 'bg-muted'
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
