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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useCharacterStore } from '@/stores';
import { API_URL } from '@/lib/constants';
import { Character, CharacterRelation } from '@/types';
import { RefreshCw, Edit2, Trash2, Loader2, Plus, X, ChevronDown, Users } from 'lucide-react';
import { toast } from 'sonner';
import { CharacterNode } from './CharacterNode';
import { getLayoutedElements } from '@/lib/layoutUtils';
import { AnalyzeMode } from '@/types';

interface CharacterGraphProps {
  onAnalyze?: (mode?: AnalyzeMode) => void;
  isAnalyzing?: boolean;
  analyzeMode?: AnalyzeMode;
  setAnalyzeMode?: (mode: AnalyzeMode) => void;
}

const nodeTypes = {
  characterNode: CharacterNode,
};

export function CharacterGraph({ onAnalyze, isAnalyzing, analyzeMode = 'incremental', setAnalyzeMode }: CharacterGraphProps) {
  const {
    characters,
    relations,
    selectedCharacter,
    setSelectedCharacter,
    updateCharacter,
    deleteCharacter,
    updateRelation,
    deleteRelation,
  } = useCharacterStore();

  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingCharacter, setEditingCharacter] = useState<Character | null>(null);
  const [newBasicInfoKey, setNewBasicInfoKey] = useState('');
  const [newBasicInfoValue, setNewBasicInfoValue] = useState('');
  const [newPersonality, setNewPersonality] = useState('');
  const [newAbility, setNewAbility] = useState('');
  const charactersRef = useRef(characters);
  const relationsRef = useRef(relations);

  // 选中的关系
  const [selectedRelation, setSelectedRelation] = useState<CharacterRelation | null>(null);
  const [editRelationDialogOpen, setEditRelationDialogOpen] = useState(false);
  const [editingRelation, setEditingRelation] = useState<CharacterRelation | null>(null);

  useEffect(() => {
    charactersRef.current = characters;
  }, [characters]);

  useEffect(() => {
    relationsRef.current = relations;
  }, [relations]);

  // 转换为 React Flow 格式并应用布局
  const { initialNodes, initialEdges } = useMemo(() => {
    const nodes: Node[] = characters.map((char) => ({
      id: char.id,
      type: 'characterNode',
      position: { x: 0, y: 0 },
      data: char,
    }));

    const validEdges: Edge[] = relations
      .filter((rel) => {
        return (
          rel.sourceId &&
          rel.targetId &&
          characters.find((c) => c.id === rel.sourceId) &&
          characters.find((c) => c.id === rel.targetId) &&
          rel.sourceId !== rel.targetId
        );
      })
      .map((rel) => ({
        id: rel.id,
        source: rel.sourceId,
        target: rel.targetId,
        label: rel.relationType || '关联',
        style: {
          stroke: selectedRelation?.id === rel.id ? '#f59e0b' : '#6366f1',
          strokeWidth: selectedRelation?.id === rel.id ? 3 : 2,
          cursor: 'pointer',
        },
        labelStyle: { fill: selectedRelation?.id === rel.id ? '#f59e0b' : '#6366f1', fontWeight: 500, fontSize: 11 },
        labelBgStyle: { fill: '#fff', fillOpacity: 0.9 },
        labelBgPadding: [4, 2] as [number, number],
        markerEnd: { type: MarkerType.ArrowClosed, color: selectedRelation?.id === rel.id ? '#f59e0b' : '#6366f1' },
        data: rel, // 存储完整的关系数据
      }));

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      nodes,
      validEdges,
      { direction: 'LR' }
    );

    return { initialNodes: layoutedNodes, initialEdges: layoutedEdges };
  }, [characters, relations]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const character = charactersRef.current.find((c) => c.id === node.id);
      if (character) {
        setSelectedCharacter(character);
        setSelectedRelation(null); // 清除选中的关系
      }
    },
    [setSelectedCharacter]
  );

  const onEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: Edge) => {
      const relation = relationsRef.current.find((r) => r.id === edge.id);
      if (relation) {
        setSelectedRelation(relation);
        setSelectedCharacter(null); // 清除选中的人物
      }
    },
    [setSelectedCharacter]
  );

  const handleEdit = useCallback((character: Character) => {
    setEditingCharacter({ ...character });
    setEditDialogOpen(true);
  }, []);

  const handleSaveEdit = useCallback(async () => {
    if (!editingCharacter) return;
    updateCharacter(editingCharacter.id, editingCharacter);
    setEditDialogOpen(false);
    setEditingCharacter(null);
    try {
      await fetch(`${API_URL}/characters/${editingCharacter.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editingCharacter),
      });
    } catch (error) {
      console.error('保存人物失败:', error);
      toast.error('保存到后端失败');
    }
  }, [editingCharacter, updateCharacter]);

  const handleDelete = useCallback(
    async (id: string) => {
      if (!confirm('确定要删除这个人物吗？')) return;
      deleteCharacter(id);
      setSelectedCharacter(null);
      try {
        await fetch(`${API_URL}/characters/${id}`, { method: 'DELETE' });
      } catch (error) {
        console.error('删除人物失败:', error);
        toast.error('从后端删除失败');
      }
    },
    [deleteCharacter, setSelectedCharacter]
  );

  // 编辑基本信息
  const handleBasicInfoChange = useCallback((key: string, value: string) => {
    if (!editingCharacter) return;
    setEditingCharacter({
      ...editingCharacter,
      basicInfo: { ...editingCharacter.basicInfo, [key]: value }
    });
  }, [editingCharacter]);

  const handleAddBasicInfo = useCallback(() => {
    if (!editingCharacter || !newBasicInfoKey.trim()) return;
    setEditingCharacter({
      ...editingCharacter,
      basicInfo: { ...editingCharacter.basicInfo, [newBasicInfoKey.trim()]: newBasicInfoValue.trim() }
    });
    setNewBasicInfoKey('');
    setNewBasicInfoValue('');
  }, [editingCharacter, newBasicInfoKey, newBasicInfoValue]);

  const handleRemoveBasicInfo = useCallback((key: string) => {
    if (!editingCharacter) return;
    const newBasicInfo = { ...editingCharacter.basicInfo };
    delete newBasicInfo[key];
    setEditingCharacter({ ...editingCharacter, basicInfo: newBasicInfo });
  }, [editingCharacter]);

  // 编辑性格
  const handleAddPersonality = useCallback(() => {
    if (!editingCharacter || !newPersonality.trim()) return;
    setEditingCharacter({
      ...editingCharacter,
      personality: [...editingCharacter.personality, newPersonality.trim()]
    });
    setNewPersonality('');
  }, [editingCharacter, newPersonality]);

  const handleRemovePersonality = useCallback((index: number) => {
    if (!editingCharacter) return;
    setEditingCharacter({
      ...editingCharacter,
      personality: editingCharacter.personality.filter((_, i) => i !== index)
    });
  }, [editingCharacter]);

  // 编辑能力
  const handleAddAbility = useCallback(() => {
    if (!editingCharacter || !newAbility.trim()) return;
    setEditingCharacter({
      ...editingCharacter,
      abilities: [...editingCharacter.abilities, newAbility.trim()]
    });
    setNewAbility('');
  }, [editingCharacter, newAbility]);

  const handleRemoveAbility = useCallback((index: number) => {
    if (!editingCharacter) return;
    setEditingCharacter({
      ...editingCharacter,
      abilities: editingCharacter.abilities.filter((_, i) => i !== index)
    });
  }, [editingCharacter]);

  // 关系编辑处理
  const handleEditRelation = useCallback((relation: CharacterRelation) => {
    setEditingRelation({ ...relation });
    setEditRelationDialogOpen(true);
  }, []);

  const handleSaveEditRelation = useCallback(async () => {
    if (!editingRelation) return;
    updateRelation(editingRelation.id, editingRelation);
    setEditRelationDialogOpen(false);
    const saved = editingRelation;
    setEditingRelation(null);
    setSelectedRelation(saved);
    try {
      await fetch(`${API_URL}/characters/relations/${saved.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(saved),
      });
    } catch (error) {
      console.error('保存关系失败:', error);
      toast.error('保存关系到后端失败');
    }
  }, [editingRelation, updateRelation]);

  const handleDeleteRelation = useCallback(
    async (id: string) => {
      if (!confirm('确定要删除这个关系吗？')) return;
      deleteRelation(id);
      setSelectedRelation(null);
      try {
        await fetch(`${API_URL}/characters/relations/${id}`, { method: 'DELETE' });
      } catch (error) {
        console.error('删除关系失败:', error);
        toast.error('从后端删除关系失败');
      }
    },
    [deleteRelation]
  );

  // 获取关系两端的人物名称
  const getRelationCharacterNames = useCallback((relation: CharacterRelation) => {
    const source = characters.find((c) => c.id === relation.sourceId);
    const target = characters.find((c) => c.id === relation.targetId);
    return {
      sourceName: source?.name || '未知',
      targetName: target?.name || '未知',
    };
  }, [characters]);

  return (
    <div className="h-full flex gap-4">
      {/* 图谱区域 */}
      <Card className="flex-1">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>人物关系图</CardTitle>
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
              onEdgeClick={onEdgeClick}
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

      {/* 详情面板 */}
      <Card className="w-80">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {selectedCharacter ? (
              <>
                <span>{selectedCharacter.name}</span>
                <Badge variant="secondary">人物</Badge>
              </>
            ) : selectedRelation ? (
              <>
                <Users className="h-4 w-4" />
                <span>关系详情</span>
                <Badge variant="secondary">关系</Badge>
              </>
            ) : (
              '选择人物或关系'
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {selectedCharacter ? (
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium mb-1">基本信息</h4>
                <div className="space-y-1">
                  {Object.entries(selectedCharacter.basicInfo || {}).map(
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
                    <Badge key={i} variant="secondary">{p}</Badge>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-1">能力</h4>
                <div className="flex flex-wrap gap-1">
                  {(selectedCharacter.abilities || []).map((a, i) => (
                    <Badge key={i} variant="outline">{a}</Badge>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-1">故事简介</h4>
                <p className="text-sm text-muted-foreground">
                  {selectedCharacter.storySummary || '暂无'}
                </p>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-1">首次登场</h4>
                <p className="text-sm text-muted-foreground">
                  {selectedCharacter.firstAppear || '暂无'}
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
          ) : selectedRelation ? (
            <div className="space-y-4">
              {(() => {
                const { sourceName, targetName } = getRelationCharacterNames(selectedRelation);
                return (
                  <>
                    <div>
                      <h4 className="text-sm font-medium mb-1">关系人物</h4>
                      <div className="flex items-center gap-2 text-sm">
                        <Badge variant="default">{sourceName}</Badge>
                        <span className="text-muted-foreground">→</span>
                        <Badge variant="default">{targetName}</Badge>
                      </div>
                    </div>

                    <div>
                      <h4 className="text-sm font-medium mb-1">关系类型</h4>
                      <Badge variant="secondary" className="text-base">
                        {selectedRelation.relationType || '关联'}
                      </Badge>
                    </div>

                    <div>
                      <h4 className="text-sm font-medium mb-1">关系描述</h4>
                      <p className="text-sm text-muted-foreground">
                        {selectedRelation.description || '暂无描述'}
                      </p>
                    </div>

                    <div>
                      <h4 className="text-sm font-medium mb-1">关系强度</h4>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary transition-all"
                            style={{ width: `${(selectedRelation.strength || 5) * 10}%` }}
                          />
                        </div>
                        <span className="text-sm text-muted-foreground">
                          {selectedRelation.strength || 5}/10
                        </span>
                      </div>
                    </div>

                    <div className="flex gap-2 pt-4">
                      <Button variant="outline" size="sm" onClick={() => handleEditRelation(selectedRelation)}>
                        <Edit2 className="h-4 w-4" />
                        编辑
                      </Button>
                      <Button variant="destructive" size="sm" onClick={() => handleDeleteRelation(selectedRelation.id)}>
                        <Trash2 className="h-4 w-4" />
                        删除
                      </Button>
                    </div>
                  </>
                );
              })()}
            </div>
          ) : (
            <div className="text-center text-muted-foreground py-8">
              <p>点击图谱中的人物节点或关系连线查看详情</p>
              <p className="text-xs mt-2">💡 提示：点击连线可以查看关系详情</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 编辑对话框 */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-lg max-h-[80vh]">
          <DialogHeader>
            <DialogTitle>编辑人物信息</DialogTitle>
          </DialogHeader>
          {editingCharacter && (
            <ScrollArea className="max-h-[60vh] pr-4">
              <div className="space-y-4">
                {/* 姓名 */}
                <div>
                  <label className="text-sm font-medium">姓名</label>
                  <Input
                    value={editingCharacter.name}
                    onChange={(e) => setEditingCharacter({ ...editingCharacter, name: e.target.value })}
                  />
                </div>

                {/* 别名 */}
                <div>
                  <label className="text-sm font-medium">别名</label>
                  <Input
                    value={editingCharacter.aliases?.join(', ') || ''}
                    onChange={(e) => setEditingCharacter({
                      ...editingCharacter,
                      aliases: e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                    })}
                    placeholder="用逗号分隔多个别名"
                  />
                </div>

                {/* 基本信息 */}
                <div>
                  <label className="text-sm font-medium mb-2 block">基本信息</label>
                  <div className="space-y-2">
                    {Object.entries(editingCharacter.basicInfo || {}).map(([key, value]) => (
                      <div key={key} className="flex items-center gap-2">
                        <Input
                          value={key}
                          disabled
                          className="w-24 bg-muted"
                        />
                        <Input
                          value={String(value)}
                          onChange={(e) => handleBasicInfoChange(key, e.target.value)}
                          className="flex-1"
                        />
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0"
                          onClick={() => handleRemoveBasicInfo(key)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                    <div className="flex items-center gap-2">
                      <Input
                        value={newBasicInfoKey}
                        onChange={(e) => setNewBasicInfoKey(e.target.value)}
                        placeholder="属性名"
                        className="w-24"
                      />
                      <Input
                        value={newBasicInfoValue}
                        onChange={(e) => setNewBasicInfoValue(e.target.value)}
                        placeholder="属性值"
                        className="flex-1"
                      />
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8 w-8 p-0"
                        onClick={handleAddBasicInfo}
                        disabled={!newBasicInfoKey.trim()}
                      >
                        <Plus className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>

                {/* 性格特点 */}
                <div>
                  <label className="text-sm font-medium mb-2 block">性格特点</label>
                  <div className="flex flex-wrap gap-1 mb-2">
                    {editingCharacter.personality?.map((p, i) => (
                      <Badge key={i} variant="secondary" className="flex items-center gap-1">
                        {p}
                        <X
                          className="h-3 w-3 cursor-pointer"
                          onClick={() => handleRemovePersonality(i)}
                        />
                      </Badge>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Input
                      value={newPersonality}
                      onChange={(e) => setNewPersonality(e.target.value)}
                      placeholder="添加性格特点"
                      onKeyDown={(e) => e.key === 'Enter' && handleAddPersonality()}
                    />
                    <Button variant="outline" size="sm" onClick={handleAddPersonality} disabled={!newPersonality.trim()}>
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                {/* 能力 */}
                <div>
                  <label className="text-sm font-medium mb-2 block">能力</label>
                  <div className="flex flex-wrap gap-1 mb-2">
                    {editingCharacter.abilities?.map((a, i) => (
                      <Badge key={i} variant="outline" className="flex items-center gap-1">
                        {a}
                        <X
                          className="h-3 w-3 cursor-pointer"
                          onClick={() => handleRemoveAbility(i)}
                        />
                      </Badge>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Input
                      value={newAbility}
                      onChange={(e) => setNewAbility(e.target.value)}
                      placeholder="添加能力"
                      onKeyDown={(e) => e.key === 'Enter' && handleAddAbility()}
                    />
                    <Button variant="outline" size="sm" onClick={handleAddAbility} disabled={!newAbility.trim()}>
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                {/* 故事简介 */}
                <div>
                  <label className="text-sm font-medium">故事简介</label>
                  <Textarea
                    value={editingCharacter.storySummary || ''}
                    onChange={(e) => setEditingCharacter({ ...editingCharacter, storySummary: e.target.value })}
                    rows={3}
                  />
                </div>

                {/* 首次登场 */}
                <div>
                  <label className="text-sm font-medium">首次登场</label>
                  <Input
                    value={editingCharacter.firstAppear || ''}
                    onChange={(e) => setEditingCharacter({ ...editingCharacter, firstAppear: e.target.value })}
                    placeholder="例如：第1章"
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

      {/* 关系编辑对话框 */}
      <Dialog open={editRelationDialogOpen} onOpenChange={setEditRelationDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>编辑关系</DialogTitle>
          </DialogHeader>
          {editingRelation && (
            <div className="space-y-4">
              {/* 关系双方 */}
              <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                <Badge variant="default">{getRelationCharacterNames(editingRelation).sourceName}</Badge>
                <span className="text-muted-foreground">→</span>
                <Badge variant="default">{getRelationCharacterNames(editingRelation).targetName}</Badge>
              </div>

              {/* 关系类型 */}
              <div>
                <label className="text-sm font-medium">关系类型</label>
                <Input
                  value={editingRelation.relationType || ''}
                  onChange={(e) => setEditingRelation({ ...editingRelation, relationType: e.target.value })}
                  placeholder="例如：师徒、朋友、敌人"
                />
              </div>

              {/* 关系描述 */}
              <div>
                <label className="text-sm font-medium">关系描述</label>
                <Textarea
                  value={editingRelation.description || ''}
                  onChange={(e) => setEditingRelation({ ...editingRelation, description: e.target.value })}
                  rows={3}
                  placeholder="描述两人之间的关系..."
                />
              </div>

              {/* 关系强度 */}
              <div>
                <label className="text-sm font-medium mb-2 block">
                  关系强度: {editingRelation.strength || 5}/10
                </label>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={editingRelation.strength || 5}
                  onChange={(e) => setEditingRelation({ ...editingRelation, strength: parseInt(e.target.value) })}
                  className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-xs text-muted-foreground mt-1">
                  <span>弱</span>
                  <span>强</span>
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditRelationDialogOpen(false)}>取消</Button>
            <Button onClick={handleSaveEditRelation}>保存</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
