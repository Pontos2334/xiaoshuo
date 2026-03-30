'use client';

import { useCallback, useMemo, useRef, useEffect, useState } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Controls,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { usePlotStore } from '@/stores';
import { PlotNode as PlotNodeType, PlotConnection } from '@/types';
import { RefreshCw, Edit2, Trash2, Loader2, Plus, X, ChevronDown } from 'lucide-react';
import { API_URL } from '@/lib/constants';
import { toast } from 'sonner';
import { PlotNodeComponent } from './PlotNode';
import { getLayoutedElements, extractChapterNumber } from '@/lib/layoutUtils';
import { AnalyzeMode } from '@/types';

interface PlotGraphProps {
  onAnalyze?: (mode?: AnalyzeMode) => void;
  isAnalyzing?: boolean;
  analyzeMode?: AnalyzeMode;
  setAnalyzeMode?: (mode: AnalyzeMode) => void;
}

const nodeTypes = {
  plotNode: PlotNodeComponent,
};

// 辅助函数：通过标题或ID找到真正的情节ID
function findPlotId(ref: string, nodes: PlotNodeType[]): string | null {
  if (!ref || !nodes.length) return null;
  const directMatch = nodes.find(n => n.id === ref);
  if (directMatch) return directMatch.id;
  const titleMatch = nodes.find(n => n.title === ref);
  if (titleMatch) return titleMatch.id;
  for (const node of nodes) {
    if (node.title && (node.title.includes(ref) || ref.includes(node.title))) {
      return node.id;
    }
  }
  return null;
}

export function PlotGraph({ onAnalyze, isAnalyzing, analyzeMode = 'incremental', setAnalyzeMode }: PlotGraphProps) {
  const { plotNodes, plotConnections, selectedPlotNode, setSelectedPlotNode, updatePlotNode, deletePlotNode } = usePlotStore();
  const plotNodesRef = useRef(plotNodes);

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingPlot, setEditingPlot] = useState<PlotNodeType | null>(null);
  const [newCharacter, setNewCharacter] = useState('');

  useEffect(() => {
    plotNodesRef.current = plotNodes;
  }, [plotNodes]);

  // 转换为 React Flow 格式并应用布局
  const { initialNodes, initialEdges } = useMemo(() => {
    if (plotNodes.length === 0) {
      return { initialNodes: [], initialEdges: [] };
    }

    const sortedNodes = [...plotNodes].sort((a, b) =>
      extractChapterNumber(a.chapter) - extractChapterNumber(b.chapter)
    );

    const nodes: Node[] = sortedNodes.map((node) => ({
      id: node.id,
      type: 'plotNode',
      position: { x: 0, y: 0 },
      data: node,
    }));

    const connectionStyles: Record<string, { stroke: string; label: string }> = {
      'cause': { stroke: '#ef4444', label: '因果' },
      'parallel': { stroke: '#22c55e', label: '并行' },
      'foreshadow': { stroke: '#f59e0b', label: '伏笔' },
      'flashback': { stroke: '#8b5cf6', label: '闪回' },
      'next': { stroke: '#3b82f6', label: '后续' },
    };

    const validEdges: Edge[] = [];

    plotConnections.forEach((conn) => {
      let sourceId = conn.sourceId;
      let targetId = conn.targetId;

      if (sourceId && !plotNodes.find(n => n.id === sourceId)) {
        const found = findPlotId(sourceId, plotNodes);
        if (found) sourceId = found;
      }
      if (targetId && !plotNodes.find(n => n.id === targetId)) {
        const found = findPlotId(targetId, plotNodes);
        if (found) targetId = found;
      }

      if (sourceId && targetId &&
          plotNodes.find(n => n.id === sourceId) &&
          plotNodes.find(n => n.id === targetId) &&
          sourceId !== targetId) {
        const style = connectionStyles[conn.connectionType] || { stroke: '#94a3b8', label: '关联' };

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

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      nodes,
      validEdges,
      { direction: 'LR', nodeWidth: 180, nodeHeight: 100, nodesep: 120, ranksep: 180 }
    );

    return { initialNodes: layoutedNodes, initialEdges: layoutedEdges };
  }, [plotNodes, plotConnections]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

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

  const handleEdit = useCallback((plot: PlotNodeType) => {
    setEditingPlot({ ...plot });
    setEditDialogOpen(true);
  }, []);

  const handleSaveEdit = useCallback(async () => {
    if (!editingPlot) return;
    updatePlotNode(editingPlot.id, editingPlot);
    setEditDialogOpen(false);
    setEditingPlot(null);
    try {
      await fetch(`${API_URL}/plots/${editingPlot.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editingPlot),
      });
    } catch (error) {
      console.error('保存情节失败:', error);
      toast.error('保存到后端失败');
    }
  }, [editingPlot, updatePlotNode]);

  const handleDelete = useCallback(
    async (id: string) => {
      if (!confirm('确定要删除这个情节节点吗？')) return;
      deletePlotNode(id);
      setSelectedPlotNode(null);
      try {
        await fetch(`${API_URL}/plots/${id}`, { method: 'DELETE' });
      } catch (error) {
        console.error('删除情节失败:', error);
        toast.error('从后端删除失败');
      }
    },
    [deletePlotNode, setSelectedPlotNode]
  );

  // 添加涉及人物
  const handleAddCharacter = useCallback(() => {
    if (!editingPlot || !newCharacter.trim()) return;
    setEditingPlot({
      ...editingPlot,
      characters: [...(editingPlot.characters || []), newCharacter.trim()]
    });
    setNewCharacter('');
  }, [editingPlot, newCharacter]);

  // 移除涉及人物
  const handleRemoveCharacter = useCallback((index: number) => {
    if (!editingPlot) return;
    setEditingPlot({
      ...editingPlot,
      characters: editingPlot.characters.filter((_, i) => i !== index)
    });
  }, [editingPlot]);

  // 情绪选项
  const emotionOptions = ['紧张', '温馨', '悲伤', '欢乐', '愤怒', '平静', '悬疑', '惊讶'];

  return (
    <div className="h-full flex gap-4">
      {/* 情节图谱区域 */}
      <Card className="flex-1">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>情节关联图</CardTitle>
          <div className="flex gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" disabled={isAnalyzing}>
                  {isAnalyzing ? (
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4 mr-1" />
                  )}
                  {isAnalyzing ? '分析中...' : 'AI分析'}
                  <ChevronDown className="h-4 w-4 ml-1" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  onClick={() => {
                    setAnalyzeMode?.('incremental');
                    onAnalyze?.('incremental');
                  }}
                  className="flex items-center gap-2"
                >
                  <span className={analyzeMode === 'incremental' ? 'font-bold' : ''}>增量分析</span>
                  <span className="text-xs text-muted-foreground ml-auto">推荐</span>
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => {
                    setAnalyzeMode?.('full');
                    onAnalyze?.('full');
                  }}
                  className="flex items-center gap-2"
                >
                  <span className={analyzeMode === 'full' ? 'font-bold' : ''}>全量分析</span>
                  <span className="text-xs text-muted-foreground ml-auto">重新分析全部</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
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
                    '悬疑': '#e9d5ff',
                    '惊讶': '#fde68a',
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
          <CardTitle>{selectedPlotNode ? selectedPlotNode.title : '选择情节'}</CardTitle>
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
                <Button variant="outline" size="sm" onClick={() => handleEdit(selectedPlotNode)}>
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

      {/* 编辑对话框 */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-lg max-h-[80vh]">
          <DialogHeader>
            <DialogTitle>编辑情节信息</DialogTitle>
          </DialogHeader>
          {editingPlot && (
            <ScrollArea className="max-h-[60vh] pr-4">
              <div className="space-y-4">
                {/* 标题 */}
                <div>
                  <label className="text-sm font-medium">标题</label>
                  <Input
                    value={editingPlot.title}
                    onChange={(e) => setEditingPlot({ ...editingPlot, title: e.target.value })}
                    placeholder="情节标题"
                  />
                </div>

                {/* 章节 */}
                <div>
                  <label className="text-sm font-medium">章节</label>
                  <Input
                    value={editingPlot.chapter}
                    onChange={(e) => setEditingPlot({ ...editingPlot, chapter: e.target.value })}
                    placeholder="例如：1, 2-1, 外传"
                  />
                </div>

                {/* 情节概述 */}
                <div>
                  <label className="text-sm font-medium">情节概述</label>
                  <Textarea
                    value={editingPlot.summary || ''}
                    onChange={(e) => setEditingPlot({ ...editingPlot, summary: e.target.value })}
                    rows={4}
                    placeholder="描述这个情节的主要内容..."
                  />
                </div>

                {/* 涉及人物 */}
                <div>
                  <label className="text-sm font-medium mb-2 block">涉及人物</label>
                  <div className="flex flex-wrap gap-1 mb-2">
                    {editingPlot.characters?.map((char, i) => (
                      <Badge key={i} variant="outline" className="flex items-center gap-1">
                        {char}
                        <X
                          className="h-3 w-3 cursor-pointer"
                          onClick={() => handleRemoveCharacter(i)}
                        />
                      </Badge>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Input
                      value={newCharacter}
                      onChange={(e) => setNewCharacter(e.target.value)}
                      placeholder="添加人物"
                      onKeyDown={(e) => e.key === 'Enter' && handleAddCharacter()}
                    />
                    <Button variant="outline" size="sm" onClick={handleAddCharacter} disabled={!newCharacter.trim()}>
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                {/* 主要情绪 */}
                <div>
                  <label className="text-sm font-medium mb-2 block">主要情绪</label>
                  <div className="flex flex-wrap gap-1">
                    {emotionOptions.map((emotion) => (
                      <Badge
                        key={emotion}
                        variant={editingPlot.emotion === emotion ? 'default' : 'outline'}
                        className="cursor-pointer"
                        onClick={() => setEditingPlot({ ...editingPlot, emotion })}
                      >
                        {emotion}
                      </Badge>
                    ))}
                  </div>
                </div>

                {/* 重要程度 */}
                <div>
                  <label className="text-sm font-medium mb-2 block">重要程度: {editingPlot.importance}/10</label>
                  <Input
                    type="range"
                    min={1}
                    max={10}
                    value={editingPlot.importance || 5}
                    onChange={(e) => setEditingPlot({ ...editingPlot, importance: parseInt(e.target.value) })}
                  />
                  <div className="flex gap-1 mt-2">
                    {[...Array(10)].map((_, i) => (
                      <div
                        key={i}
                        className={`flex-1 h-2 rounded ${
                          i < (editingPlot.importance || 5) ? 'bg-primary' : 'bg-muted'
                        }`}
                      />
                    ))}
                  </div>
                </div>

                {/* 内容引用 */}
                <div>
                  <label className="text-sm font-medium">内容引用</label>
                  <Input
                    value={editingPlot.contentRef || ''}
                    onChange={(e) => setEditingPlot({ ...editingPlot, contentRef: e.target.value })}
                    placeholder="原文位置或引用"
                  />
                </div>
              </div>
            </ScrollArea>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>取消</Button>
            <Button onClick={handleSaveEdit}>保存</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
