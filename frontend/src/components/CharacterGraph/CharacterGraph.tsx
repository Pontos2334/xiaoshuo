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
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useCharacterStore } from '@/stores';
import { Character, CharacterRelation } from '@/types';
import { RefreshCw, Edit2, Trash2, Loader2, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import { CharacterNode } from './CharacterNode';

interface CharacterGraphProps {
  onAnalyze?: () => void;
  isAnalyzing?: boolean;
}

const nodeTypes = {
  characterNode: CharacterNode,
};

// Dagre 布局配置
const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const nodeWidth = 150;
const nodeHeight = 80;

function getLayoutedElements(nodes: Node[], edges: Edge[], direction = 'TB') {
  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({ rankdir: direction, nodesep: 100, ranksep: 150 });

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

export function CharacterGraph({ onAnalyze, isAnalyzing }: CharacterGraphProps) {
  const {
    characters,
    relations,
    selectedCharacter,
    setSelectedCharacter,
    updateCharacter,
    deleteCharacter,
  } = useCharacterStore();

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingCharacter, setEditingCharacter] = useState<Character | null>(null);
  const charactersRef = useRef(characters);

  useEffect(() => {
    charactersRef.current = characters;
  }, [characters]);

  // 转换为 React Flow 格式并应用布局
  const { initialNodes, initialEdges } = useMemo(() => {
    const nodes: Node[] = characters.map((char) => ({
      id: char.id,
      type: 'characterNode',
      position: { x: 0, y: 0 }, // 将由 dagre 计算
      data: char,
    }));

    // 过滤有效的边
    const validEdges: Edge[] = relations
      .filter((rel) => {
        const sourceId = rel.sourceId || rel.source_id;
        const targetId = rel.targetId || rel.target_id;
        return (
          sourceId &&
          targetId &&
          characters.find((c) => c.id === sourceId) &&
          characters.find((c) => c.id === targetId) &&
          sourceId !== targetId
        );
      })
      .map((rel) => ({
        id: rel.id,
        source: rel.sourceId || rel.source_id || '',
        target: rel.targetId || rel.target_id || '',
        label: rel.relationType || rel.relation_type || '关联',
        style: { stroke: '#6366f1', strokeWidth: 2 },
        labelStyle: { fill: '#6366f1', fontWeight: 500, fontSize: 11 },
        labelBgStyle: { fill: '#fff', fillOpacity: 0.9 },
        labelBgPadding: [4, 2] as [number, number],
        markerEnd: { type: MarkerType.ArrowClosed, color: '#6366f1' },
      }));

    // 应用 dagre 布局
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      nodes,
      validEdges,
      'LR' // 从左到右布局
    );

    return { initialNodes: layoutedNodes, initialEdges: layoutedEdges };
  }, [characters, relations]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // 当数据变化时更新节点和边
  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const character = charactersRef.current.find((c) => c.id === node.id);
      if (character) {
        setSelectedCharacter(character);
      }
    },
    [setSelectedCharacter]
  );

  const handleEdit = useCallback((character: Character) => {
    setEditingCharacter({ ...character });
    setEditDialogOpen(true);
  }, []);

  const handleSaveEdit = useCallback(() => {
    if (editingCharacter) {
      updateCharacter(editingCharacter.id, editingCharacter);
      setEditDialogOpen(false);
      setEditingCharacter(null);
    }
  }, [editingCharacter, updateCharacter]);

  const handleDelete = useCallback(
    (id: string) => {
      if (confirm('确定要删除这个人物吗？')) {
        deleteCharacter(id);
      }
    },
    [deleteCharacter]
  );

  return (
    <div className="h-full flex gap-4">
      {/* 图谱区域 */}
      <Card className="flex-1">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>人物关系图</CardTitle>
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
                  const data = node.data as Character;
                  const colors: Record<string, string> = {
                    '正义': '#93c5fd',
                    '邪恶': '#fca5a5',
                    '中立': '#d1d5db',
                  };
                  return colors[data?.basicInfo?.身份] || '#c7d2fe';
                }}
              />
              <Background gap={16} size={1} />
            </ReactFlow>
          </div>
        </CardContent>
      </Card>

      {/* 人物详情面板 */}
      <Card className="w-80">
        <CardHeader>
          <CardTitle>{selectedCharacter ? selectedCharacter.name : '选择人物'}</CardTitle>
        </CardHeader>
        <CardContent>
          {selectedCharacter ? (
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium mb-1">基本信息</h4>
                <div className="space-y-1">
                  {Object.entries(selectedCharacter.basicInfo || selectedCharacter.basic_info || {}).map(
                    ([key, value]) => (
                      <div key={key} className="flex justify-between text-sm">
                        <span className="text-muted-foreground">{key}</span>
                        <span>{String(value)}</span>
                      </div>
                    )
                  )}
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-1">性格特点</h4>
                <div className="flex flex-wrap gap-1">
                  {(selectedCharacter.personality || []).map((p, i) => (
                    <Badge key={i} variant="secondary">
                      {p}
                    </Badge>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-1">能力</h4>
                <div className="flex flex-wrap gap-1">
                  {(selectedCharacter.abilities || []).map((a, i) => (
                    <Badge key={i} variant="outline">
                      {a}
                    </Badge>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-1">故事简介</h4>
                <p className="text-sm text-muted-foreground">
                  {selectedCharacter.storySummary ||
                    (selectedCharacter as Character & { story_summary?: string }).story_summary ||
                    '暂无'}
                </p>
              </div>

              <div className="flex gap-2 pt-4">
                <Button variant="outline" size="sm" onClick={() => handleEdit(selectedCharacter)}>
                  <Edit2 className="h-4 w-4" />
                  编辑
                </Button>
                <Button variant="destructive" size="sm" onClick={() => handleDelete(selectedCharacter.id)}>
                  <Trash2 className="h-4 w-4" />
                  删除
                </Button>
              </div>
            </div>
          ) : (
            <div className="text-center text-muted-foreground py-8">点击图谱中的人物节点查看详情</div>
          )}
        </CardContent>
      </Card>

      {/* 编辑对话框 */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>编辑人物信息</DialogTitle>
          </DialogHeader>
          {editingCharacter && (
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium">姓名</label>
                <Input
                  value={editingCharacter.name}
                  onChange={(e) => setEditingCharacter({ ...editingCharacter, name: e.target.value })}
                />
              </div>
              <div>
                <label className="text-sm font-medium">故事简介</label>
                <Textarea
                  value={editingCharacter.storySummary || ''}
                  onChange={(e) => setEditingCharacter({ ...editingCharacter, storySummary: e.target.value })}
                  rows={4}
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
                  取消
                </Button>
                <Button onClick={handleSaveEdit}>保存</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
