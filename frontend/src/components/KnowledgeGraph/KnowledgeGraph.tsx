'use client';

import { useCallback, useMemo, useState, useEffect, memo } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  MiniMap,
  Controls,
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Network, Loader2, RefreshCw } from 'lucide-react';
import { API_URL } from '@/lib/constants';
import { toast } from 'sonner';
import { getLayoutedElements } from '@/lib/layoutUtils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface KnowledgeGraphProps {
  novelId: string;
  novelName: string;
}

interface GraphEntity {
  name: string;
  entity_type: string;
  description: string;
  attributes: Record<string, unknown>;
}

interface GraphRelation {
  source: string;
  target: string;
  relation_type: string;
  description: string;
  strength: number;
}

interface GraphSummary {
  entity_count: number;
  relation_count: number;
  entity_types: Record<string, number>;
  sample_entities: GraphEntity[];
  sample_relations: GraphRelation[];
}

interface EntityNodeData {
  name: string;
  entity_type: string;
  description: string;
  attributes: Record<string, unknown>;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Entity type colour mapping (circle border & label colours)
// ---------------------------------------------------------------------------

const ENTITY_COLORS: Record<string, string> = {
  PERSON: '#93c5fd',
  LOCATION: '#86efac',
  ITEM: '#fdba74',
  ORGANIZATION: '#c4b5fd',
};

const ENTITY_LABEL_COLORS: Record<string, string> = {
  PERSON: '#1d4ed8',
  LOCATION: '#16a34a',
  ITEM: '#ea580c',
  ORGANIZATION: '#7c3aed',
};

const ENTITY_TYPE_LABELS: Record<string, string> = {
  PERSON: '人物',
  LOCATION: '地点',
  ITEM: '物品',
  ORGANIZATION: '组织',
};

const DEFAULT_ENTITY_COLOR = '#d1d5db';
const DEFAULT_LABEL_COLOR = '#6b7280';

// ---------------------------------------------------------------------------
// Custom node component (circular node with entity name & type)
// ---------------------------------------------------------------------------

interface EntityNodeProps {
  data: EntityNodeData;
}

function EntityNode({ data }: EntityNodeProps) {
  const borderColor = ENTITY_COLORS[data.entity_type] || DEFAULT_ENTITY_COLOR;

  return (
    <div
      style={{
        width: 80,
        height: 80,
        borderRadius: '50%',
        border: `3px solid ${borderColor}`,
        background: '#ffffff',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
      }}
    >
      <Handle id="target-left" type="target" position={Position.Left} style={{ background: 'transparent', border: 'none' }} />
      <Handle id="target-top" type="target" position={Position.Top} style={{ background: 'transparent', border: 'none' }} />
      <span
        style={{
          fontSize: 12,
          fontWeight: 600,
          maxWidth: 64,
          textAlign: 'center',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          lineHeight: 1.2,
        }}
      >
        {data.name}
      </span>
      <span
        style={{
          fontSize: 9,
          color: ENTITY_LABEL_COLORS[data.entity_type] || DEFAULT_LABEL_COLOR,
          marginTop: 2,
        }}
      >
        {ENTITY_TYPE_LABELS[data.entity_type] || data.entity_type}
      </span>
      <Handle id="source-right" type="source" position={Position.Right} style={{ background: 'transparent', border: 'none' }} />
      <Handle id="source-bottom" type="source" position={Position.Bottom} style={{ background: 'transparent', border: 'none' }} />
    </div>
  );
}

const EntityNodeComponent = memo(EntityNode);

const nodeTypes = {
  entityNode: EntityNodeComponent,
};

// ---------------------------------------------------------------------------
// KnowledgeGraph main component
// ---------------------------------------------------------------------------

export function KnowledgeGraph({ novelId, novelName }: KnowledgeGraphProps) {
  const [entities, setEntities] = useState<GraphEntity[]>([]);
  const [relations, setRelations] = useState<GraphRelation[]>([]);
  const [summary, setSummary] = useState<GraphSummary | null>(null);
  const [selectedEntity, setSelectedEntity] = useState<GraphEntity | null>(null);
  const [isBuilding, setIsBuilding] = useState(false);
  const [isLoadingSummary, setIsLoadingSummary] = useState(false);

  // ---- fetch summary on mount / novelId change ----
  useEffect(() => {
    if (!novelId) return;
    fetchSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [novelId]);

  // ---- build React Flow nodes & edges from graph data ----
  const { initialNodes, initialEdges } = useMemo(() => {
    if (entities.length === 0) return { initialNodes: [], initialEdges: [] };

    const nameToId = new Map<string, string>();
    entities.forEach((entity, index) => {
      nameToId.set(entity.name, `entity-${index}`);
    });

    const nodes: Node[] = entities.map((entity, index) => ({
      id: `entity-${index}`,
      type: 'entityNode',
      position: { x: 0, y: 0 },
      data: {
        name: entity.name,
        entity_type: entity.entity_type,
        description: entity.description,
        attributes: entity.attributes,
      },
    }));

    const validEdges: Edge[] = [];
    const usedRelationTypes = new Map<string, string>();
    const relationColorPalette = [
      '#6366f1', '#8b5cf6', '#a855f7', '#d946ef', '#ec4899',
      '#f43f5e', '#ef4444', '#f97316', '#eab308', '#22c55e',
      '#14b8a6', '#06b6d4', '#3b82f6',
    ];
    let colorIdx = 0;

    relations.forEach((rel, idx) => {
      const sourceId = nameToId.get(rel.source);
      const targetId = nameToId.get(rel.target);
      if (!sourceId || !targetId || sourceId === targetId) return;

      if (!usedRelationTypes.has(rel.relation_type)) {
        usedRelationTypes.set(rel.relation_type, relationColorPalette[colorIdx % relationColorPalette.length]);
        colorIdx++;
      }
      const color = usedRelationTypes.get(rel.relation_type)!;

      validEdges.push({
        id: `rel-${idx}`,
        source: sourceId,
        target: targetId,
        label: rel.relation_type || '关联',
        style: { stroke: color, strokeWidth: 1.5 + (rel.strength || 5) * 0.15 },
        labelStyle: { fill: color, fontWeight: 500, fontSize: 10 },
        labelBgStyle: { fill: '#fff', fillOpacity: 0.85 },
        labelBgPadding: [3, 2] as [number, number],
        markerEnd: { type: MarkerType.ArrowClosed, color, width: 12, height: 12 },
      });
    });

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      nodes,
      validEdges,
      { direction: 'LR', nodeWidth: 100, nodeHeight: 100, nodesep: 80, ranksep: 200 },
    );

    return { initialNodes: layoutedNodes, initialEdges: layoutedEdges };
  }, [entities, relations]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  // ---- node click handler ----
  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      const data = node.data as EntityNodeData;
      const entity = entities.find((e) => e.name === data.name);
      if (entity) {
        setSelectedEntity(entity);
      }
    },
    [entities],
  );

  // ---- API calls ----
  const fetchSummary = useCallback(async () => {
    setIsLoadingSummary(true);
    try {
      const res = await fetch(`${API_URL}/graph/summary/${novelId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.success && data.data) {
        setSummary(data.data as GraphSummary);
      }
    } catch {
      // Summary is optional; silently ignore
    } finally {
      setIsLoadingSummary(false);
    }
  }, [novelId]);

  const handleBuildGraph = useCallback(async () => {
    if (!novelId) {
      toast.error('请先选择一本小说');
      return;
    }

    setIsBuilding(true);
    setSelectedEntity(null);
    toast.loading('正在构建知识图谱，请稍候...', { id: 'build-graph' });

    try {
      const buildRes = await fetch(`${API_URL}/graph/build`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ novel_id: novelId }),
      });

      if (!buildRes.ok) {
        const errData = await buildRes.json().catch(() => null);
        throw new Error(errData?.detail || `HTTP ${buildRes.status}`);
      }

      const buildData = await buildRes.json();

      if (buildData.success) {
        // After building, refresh summary to get the latest entities/relations
        await fetchSummary();

        // Also try to get the full graph data from summary endpoint
        const summaryRes = await fetch(`${API_URL}/graph/summary/${novelId}`);
        if (summaryRes.ok) {
          const summaryData = await summaryRes.json();
          if (summaryData.success && summaryData.data) {
            const d = summaryData.data;
            setEntities(d.sample_entities || []);
            setRelations(d.sample_relations || []);
          }
        }

        toast.success(
          `图谱构建完成：${buildData.data?.entity_count ?? 0} 个实体，${buildData.data?.relation_count ?? 0} 条关系`,
          { id: 'build-graph' },
        );
      } else {
        throw new Error('构建失败');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '未知错误';
      toast.error(`构建图谱失败：${message}`, { id: 'build-graph' });
    } finally {
      setIsBuilding(false);
    }
  }, [novelId, fetchSummary]);

  // ---- Related relations for selected entity ----
  const relatedRelations = useMemo(() => {
    if (!selectedEntity) return [];
    return relations.filter(
      (r) => r.source === selectedEntity.name || r.target === selectedEntity.name,
    );
  }, [selectedEntity, relations]);

  // ---- Helper to get entity colour ----
  const getEntityBadgeClass = (type: string) => {
    const color = ENTITY_COLORS[type] || DEFAULT_ENTITY_COLOR;
    return { bg: color, text: ENTITY_LABEL_COLORS[type] || DEFAULT_LABEL_COLOR };
  };

  // ---- Render ----
  return (
    <div className="h-full flex gap-4">
      {/* Left: Graph Card */}
      <Card className="flex-1">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="flex items-center gap-2">
            <Network className="h-5 w-5" />
            知识图谱 - {novelName}
          </CardTitle>
          <div className="flex items-center gap-3">
            {/* Summary stats in toolbar */}
            {summary && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Badge variant="outline">{summary.entity_count} 个实体</Badge>
                <Badge variant="outline">{summary.relation_count} 条关系</Badge>
              </div>
            )}
            <Button
              variant="default"
              size="sm"
              onClick={handleBuildGraph}
              disabled={isBuilding}
            >
              {isBuilding ? (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-1" />
              )}
              {isBuilding ? '构建中...' : '构建图谱'}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0 relative">
          {entities.length > 0 ? (
            <div className="h-[500px]">
              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={onNodeClick}
                nodeTypes={nodeTypes}
                fitView
                minZoom={0.2}
                maxZoom={2.5}
              >
                <Controls showInteractive={false} />
                <MiniMap
                  pannable
                  zoomable
                  nodeColor={(node) => {
                    const data = node.data as EntityNodeData;
                    return ENTITY_COLORS[data?.entity_type] || DEFAULT_ENTITY_COLOR;
                  }}
                />
                <Background gap={16} size={1} />
              </ReactFlow>
            </div>
          ) : (
            /* Empty state */
            <div className="h-[500px] flex flex-col items-center justify-center text-muted-foreground">
              <Network className="h-16 w-16 mb-4 opacity-20" />
              <p className="text-lg font-medium mb-1">暂无图谱数据</p>
              <p className="text-sm">点击「构建图谱」按钮开始构建知识图谱</p>
            </div>
          )}

          {/* Loading overlay */}
          {isBuilding && (
            <div className="absolute inset-0 bg-white/70 dark:bg-black/50 flex flex-col items-center justify-center z-50 rounded-lg">
              <Loader2 className="h-10 w-10 animate-spin text-primary mb-3" />
              <p className="text-sm text-muted-foreground">正在构建知识图谱...</p>
              <p className="text-xs text-muted-foreground mt-1">这可能需要几分钟</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Right: Detail panel (320px) */}
      <Card className="w-80">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">图谱详情</CardTitle>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[480px]">
            {/* Summary Stats */}
            <div className="space-y-3 mb-6">
              {isLoadingSummary && !summary ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  <span className="text-sm text-muted-foreground">加载中...</span>
                </div>
              ) : summary ? (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-lg border p-3 text-center">
                      <div className="text-2xl font-bold">{summary.entity_count}</div>
                      <div className="text-xs text-muted-foreground">实体数量</div>
                    </div>
                    <div className="rounded-lg border p-3 text-center">
                      <div className="text-2xl font-bold">{summary.relation_count}</div>
                      <div className="text-xs text-muted-foreground">关系数量</div>
                    </div>
                  </div>

                  {/* Entity type breakdown */}
                  {Object.keys(summary.entity_types || {}).length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium mb-2">实体类型分布</h4>
                      <div className="flex flex-wrap gap-1.5">
                        {Object.entries(summary.entity_types).map(([type, count]) => {
                          const colors = getEntityBadgeClass(type);
                          return (
                            <Badge
                              key={type}
                              variant="outline"
                              style={{
                                backgroundColor: colors.bg,
                                color: colors.text,
                                borderColor: 'transparent',
                              }}
                            >
                              {ENTITY_TYPE_LABELS[type] || type}: {count}
                            </Badge>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center text-muted-foreground py-4 text-sm">
                  暂无图谱数据
                </div>
              )}
            </div>

            {/* Selected Entity Details */}
            {selectedEntity ? (
              <div className="border-t pt-4">
                <h3 className="text-sm font-semibold mb-3">实体详情</h3>
                <div className="space-y-3">
                  {/* Name */}
                  <div>
                    <h4 className="text-xs text-muted-foreground">名称</h4>
                    <p className="text-sm font-medium">{selectedEntity.name}</p>
                  </div>

                  {/* Type */}
                  <div>
                    <h4 className="text-xs text-muted-foreground mb-1">类型</h4>
                    <Badge
                      style={{
                        backgroundColor: ENTITY_COLORS[selectedEntity.entity_type] || DEFAULT_ENTITY_COLOR,
                        color: ENTITY_LABEL_COLORS[selectedEntity.entity_type] || DEFAULT_LABEL_COLOR,
                        border: 'none',
                      }}
                    >
                      {ENTITY_TYPE_LABELS[selectedEntity.entity_type] || selectedEntity.entity_type}
                    </Badge>
                  </div>

                  {/* Description */}
                  {selectedEntity.description && (
                    <div>
                      <h4 className="text-xs text-muted-foreground">描述</h4>
                      <p className="text-sm text-muted-foreground">{selectedEntity.description}</p>
                    </div>
                  )}

                  {/* Attributes */}
                  {Object.keys(selectedEntity.attributes || {}).length > 0 && (
                    <div>
                      <h4 className="text-xs text-muted-foreground mb-1">属性</h4>
                      <div className="space-y-1">
                        {Object.entries(selectedEntity.attributes).map(([key, value]) => (
                          <div key={key} className="flex justify-between text-sm">
                            <span className="text-muted-foreground">{key}</span>
                            <span className="text-right max-w-[60%] truncate">{String(value)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Related Relations */}
                  {relatedRelations.length > 0 && (
                    <div>
                      <h4 className="text-xs text-muted-foreground mb-1">
                        相关关系 ({relatedRelations.length})
                      </h4>
                      <div className="space-y-1.5">
                        {relatedRelations.map((rel, idx) => (
                          <div
                            key={idx}
                            className="text-xs bg-muted/50 rounded-md px-2 py-1.5 flex items-center gap-1.5"
                          >
                            <Badge variant="outline" className="text-[10px] h-4 px-1">
                              {rel.source === selectedEntity.name ? rel.target : rel.source}
                            </Badge>
                            <span className="text-muted-foreground">-</span>
                            <Badge variant="secondary" className="text-[10px] h-4 px-1">
                              {rel.relation_type}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              !isBuilding && entities.length > 0 && (
                <div className="border-t pt-4 text-center text-muted-foreground py-6 text-sm">
                  点击图谱中的实体节点查看详情
                </div>
              )
            )}
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}
