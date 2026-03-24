'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { Graph } from '@antv/g6';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useCharacterStore } from '@/stores';
import { Character, CharacterRelation } from '@/types';
import { RefreshCw, Edit2, Trash2, Loader2 } from 'lucide-react';

interface CharacterGraphProps {
  onAnalyze?: () => void;
  isAnalyzing?: boolean;
}

// 安全地检查和操作 graph
function isGraphReady(graph: Graph | null): graph is Graph {
  return graph !== null && !graph.destroyed;
}

export function CharacterGraph({ onAnalyze, isAnalyzing }: CharacterGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);
  const { characters, relations, selectedCharacter, setSelectedCharacter, updateCharacter, deleteCharacter } = useCharacterStore();
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingCharacter, setEditingCharacter] = useState<Character | null>(null);
  const [graphReady, setGraphReady] = useState(false);

  // 用于在点击事件中获取最新的 characters
  const charactersRef = useRef(characters);
  useEffect(() => {
    charactersRef.current = characters;
  }, [characters]);

  // 初始化图谱
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 如果已存在 graph 实例，先销毁
    if (graphRef.current && !graphRef.current.destroyed) {
      graphRef.current.destroy();
      graphRef.current = null;
    }

    const graph = new Graph({
      container: container,
      width: container.clientWidth,
      height: container.clientHeight || 500,
      autoFit: 'view',
      padding: 20,
      behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
      node: {
        style: {
          size: (d: Record<string, unknown>) => {
            // 根据关系数量调整节点大小
            const data = d.data as Character;
            const relCount = relations.filter(r => r.sourceId === data?.id || r.targetId === data?.id).length;
            return Math.max(50, 50 + relCount * 5);
          },
          fill: '#5B8FF9',
          stroke: '#1890ff',
          lineWidth: 2,
          radius: 8,
          labelText: (d: Record<string, unknown>) => (d.data as { name?: string })?.name || '',
          labelFill: '#fff',
          labelFontSize: 12,
          labelPlacement: 'center',
        },
        state: {
          selected: {
            lineWidth: 4,
            stroke: '#faad14',
          },
        },
      },
      edge: {
        style: {
          stroke: '#A0AEC0',
          lineWidth: 2,
          endArrow: true,
          labelText: (d: Record<string, unknown>) => (d.data as { relationType?: string })?.relationType || '',
          labelFill: '#666',
          labelFontSize: 10,
        },
      },
      layout: {
        type: 'force',
        preventOverlap: true,
        nodeStrength: -500,
        edgeStrength: 0.2,
        linkDistance: 150,
        nodeSpacing: 100,
      },
    });

    graphRef.current = graph;

    // 节点点击事件 - 使用 ref 获取最新的 characters
    graph.on('node:click', (event: unknown) => {
      const evt = event as { target: { id: string } };
      const nodeId = evt.target.id;
      const character = charactersRef.current.find(c => c.id === nodeId);
      if (character) {
        setSelectedCharacter(character);
      }
    });

    // 标记 graph 已就绪
    setGraphReady(true);

    return () => {
      if (graphRef.current && !graphRef.current.destroyed) {
        graphRef.current.destroy();
      }
      graphRef.current = null;
      setGraphReady(false);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 辅助函数：通过名称或ID找到人物ID
  const findCharacterId = (ref: string): string | null => {
    const char = characters.find(c =>
      c.id === ref ||
      c.name === ref ||
      c.name?.includes(ref.replace('ID', '').replace('人物', '')) ||
      ref.includes(c.name || '')
    );
    return char?.id || null;
  };

  // 更新图谱数据
  useEffect(() => {
    if (!graphReady || !isGraphReady(graphRef.current)) return;

    const graph = graphRef.current;

    const nodes = characters.map(char => ({
      id: char.id,
      data: char,
    }));

    // 处理关系数据，通过名称匹配ID
    const validEdges: Array<{
      id: string;
      source: string;
      target: string;
      data: CharacterRelation;
    }> = [];

    relations.forEach(rel => {
      let sourceId = rel.sourceId;
      let targetId = rel.targetId;

      // 如果 sourceId/targetId 不是有效的人物ID，尝试通过名称匹配
      if (!characters.find(c => c.id === sourceId)) {
        const matched = findCharacterId(sourceId);
        if (matched) sourceId = matched;
      }
      if (!characters.find(c => c.id === targetId)) {
        const matched = findCharacterId(targetId);
        if (matched) targetId = matched;
      }

      // 只有当 sourceId 和 targetId 都是有效的人物ID 时才添加边
      if (sourceId && targetId &&
          characters.find(c => c.id === sourceId) &&
          characters.find(c => c.id === targetId) &&
          sourceId !== targetId) {
        validEdges.push({
          id: rel.id,
          source: sourceId,
          target: targetId,
          data: rel,
        });
      }
    });

    try {
      graph.setData({
        nodes,
        edges: validEdges,
      });
      graph.render();
    } catch (error) {
      // 忽略已销毁实例的错误
      if (!graph.destroyed) {
        console.warn('Graph render error:', error);
      }
    }
  }, [graphReady, characters, relations]);

  // 打开编辑对话框
  const handleEdit = useCallback((character: Character) => {
    setEditingCharacter({ ...character });
    setEditDialogOpen(true);
  }, []);

  // 保存编辑
  const handleSaveEdit = useCallback(() => {
    if (editingCharacter) {
      updateCharacter(editingCharacter.id, editingCharacter);
      setEditDialogOpen(false);
      setEditingCharacter(null);
    }
  }, [editingCharacter, updateCharacter]);

  // 删除人物
  const handleDelete = useCallback((id: string) => {
    if (confirm('确定要删除这个人物吗？')) {
      deleteCharacter(id);
    }
  }, [deleteCharacter]);

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
          <div ref={containerRef} className="w-full h-[500px]" />
        </CardContent>
      </Card>

      {/* 人物详情面板 */}
      <Card className="w-80">
        <CardHeader>
          <CardTitle>
            {selectedCharacter ? selectedCharacter.name : '选择人物'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {selectedCharacter ? (
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium mb-1">基本信息</h4>
                <div className="space-y-1">
                  {Object.entries(selectedCharacter.basicInfo || selectedCharacter.basic_info || {}).map(([key, value]) => (
                    <div key={key} className="flex justify-between text-sm">
                      <span className="text-muted-foreground">{key}</span>
                      <span>{String(value)}</span>
                    </div>
                  ))}
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
                <p className="text-sm text-muted-foreground">{selectedCharacter.storySummary || (selectedCharacter as Character & { story_summary?: string }).story_summary || '暂无'}</p>
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
            <div className="text-center text-muted-foreground py-8">
              点击图谱中的人物节点查看详情
            </div>
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
                <Button onClick={handleSaveEdit}>
                  保存
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
