'use client';

import { useCallback, useMemo, useState } from 'react';
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
import { PlotNode as PlotNodeType } from '@/types';

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

export function PlotGraph({ onAnalyze, isAnalyzing }: PlotGraphProps) {
  const { plotNodes, plotConnections, selectedPlotNode, setSelectedPlotNode, updatePlotNode, deletePlotNode } = usePlotStore();

  // 转换为React Flow格式
  const initialNodes: Node[] = useMemo(() => {
    return plotNodes.map((node) => ({
      id: node.id,
      type: 'plotNode',
      position: { x: Math.random() * 800, y: Math.random() * 500 },
      data: node,
    }));
  }, [plotNodes]);

  const initialEdges: Edge[] = useMemo(() => {
    const connectionStyles: Record<string, { stroke: string; label: string }> = {
      'cause': { stroke: '#ef4444', label: '因果' },
      'parallel': { stroke: '#22c55e', label: '并行' },
      'foreshadow': { stroke: '#f59e0b', label: '伏笔' },
      'flashback': { stroke: '#8b5cf6', label: '闪回' },
      'next': { stroke: '#3b82f6', label: '后续' },
    };

    return plotConnections.map((conn) => {
      const style = connectionStyles[conn.connectionType] || { stroke: '#94a3b8', label: '关联' };
      return {
        id: conn.id,
        source: conn.sourceId,
        target: conn.targetId,
        label: style.label,
        style: { stroke: style.stroke, strokeWidth: 2 },
        labelStyle: { fill: style.stroke, fontWeight: 500 },
        markerEnd: { type: MarkerType.ArrowClosed, color: style.stroke },
      };
    });
  }, [plotConnections]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    const plotNode = plotNodes.find((p) => p.id === node.id);
    if (plotNode) {
      setSelectedPlotNode(plotNode);
    }
  }, [plotNodes, setSelectedPlotNode]);

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
