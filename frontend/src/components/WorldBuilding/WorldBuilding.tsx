'use client';

import { useState, useEffect } from 'react';
import { useNovelStore, useWorldBuildingStore } from '@/stores';
import { API_URL } from '@/lib/constants';
import type { WorldEntity, EntityRelation, ConsistencyIssue } from '@/types';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Globe,
  MapPin,
  Sword,
  Users,
  Calendar,
  BookOpen,
  Type,
  Plus,
  Trash2,
  Edit3,
  Search,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Info,
  RefreshCw,
  Zap,
} from 'lucide-react';
import { toast } from 'sonner';

const ENTITY_TYPES = [
  { value: 'location', label: '地点', icon: MapPin, color: 'text-green-500' },
  { value: 'item', label: '物品', icon: Sword, color: 'text-orange-500' },
  { value: 'organization', label: '组织', icon: Users, color: 'text-purple-500' },
  { value: 'event', label: '事件', icon: Calendar, color: 'text-red-500' },
  { value: 'concept', label: '概念', icon: BookOpen, color: 'text-blue-500' },
  { value: 'terminology', label: '术语', icon: Type, color: 'text-teal-500' },
] as const;

const SEVERITY_STYLES: Record<string, { icon: typeof AlertTriangle; color: string }> = {
  error: { icon: AlertTriangle, color: 'text-red-500 bg-red-50 dark:bg-red-950/20' },
  warning: { icon: AlertTriangle, color: 'text-yellow-500 bg-yellow-50 dark:bg-yellow-950/20' },
  info: { icon: Info, color: 'text-blue-500 bg-blue-50 dark:bg-blue-950/20' },
};

export function WorldBuilding() {
  const { currentNovel } = useNovelStore();
  const {
    entities,
    entityRelations,
    selectedEntityId,
    setEntities,
    setEntityRelations,
    setSelectedEntityId,
    addEntity,
    updateEntity,
    deleteEntity,
  } = useWorldBuildingStore();

  const [isLoading, setIsLoading] = useState(false);
  const [activeType, setActiveType] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingEntity, setEditingEntity] = useState<Partial<WorldEntity> | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [consistencyIssues, setConsistencyIssues] = useState<ConsistencyIssue[]>([]);
  const [isChecking, setIsChecking] = useState(false);
  const [showConsistency, setShowConsistency] = useState(false);
  const [isDeepChecking, setIsDeepChecking] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState<Record<number, boolean>>({});

  // 加载实体
  useEffect(() => {
    if (!currentNovel) return;
    const loadEntities = async () => {
      setIsLoading(true);
      try {
        const res = await fetch(`${API_URL}/worldbuilding/entities?novel_id=${currentNovel.id}`);
        if (res.ok) {
          const data = await res.json();
          setEntities(data);
        }
      } catch (e) {
        console.error('加载世界观实体失败:', e);
      } finally {
        setIsLoading(false);
      }
    };
    loadEntities();
  }, [currentNovel, setEntities]);

  // 加载关系
  useEffect(() => {
    if (!currentNovel) return;
    const loadRelations = async () => {
      try {
        const res = await fetch(`${API_URL}/worldbuilding/relations?novel_id=${currentNovel.id}`);
        if (res.ok) {
          const data = await res.json();
          setEntityRelations(data);
        }
      } catch (e) {
        console.error('加载实体关系失败:', e);
      }
    };
    loadRelations();
  }, [currentNovel, setEntityRelations]);

  // 过滤实体
  const filteredEntities = entities.filter((e) => {
    if (activeType !== 'all' && e.entityType !== activeType) return false;
    if (searchQuery && !e.name.includes(searchQuery) && !(e.description || '').includes(searchQuery))
      return false;
    return true;
  });

  // 按类型分组统计
  const typeCounts = entities.reduce(
    (acc, e) => {
      acc[e.entityType] = (acc[e.entityType] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  // 创建/编辑实体
  const handleSaveEntity = async () => {
    if (!editingEntity || !currentNovel) return;
    if (!editingEntity.name || !editingEntity.entityType) {
      toast.error('请填写名称和类型');
      return;
    }

    try {
      if (editingEntity.id) {
        // 更新
        const res = await fetch(`${API_URL}/worldbuilding/entities/${editingEntity.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: editingEntity.name,
            entityType: editingEntity.entityType,
            description: editingEntity.description,
            attributes: editingEntity.attributes,
            rules: editingEntity.rules,
          }),
        });
        if (res.ok) {
          const updated = await res.json();
          updateEntity(editingEntity.id, updated);
          toast.success('更新成功');
        }
      } else {
        // 创建
        const res = await fetch(`${API_URL}/worldbuilding/entities`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            novelId: currentNovel.id,
            name: editingEntity.name,
            entityType: editingEntity.entityType,
            description: editingEntity.description,
            attributes: editingEntity.attributes,
            rules: editingEntity.rules,
            source: 'manual',
          }),
        });
        if (res.ok) {
          const created = await res.json();
          addEntity(created);
          toast.success('创建成功');
        }
      }
      setEditDialogOpen(false);
      setEditingEntity(null);
    } catch (e) {
      toast.error('保存失败');
    }
  };

  // 删除实体
  const handleDeleteEntity = async (id: string) => {
    if (!confirm('确定要删除该实体吗？')) return;
    try {
      const res = await fetch(`${API_URL}/worldbuilding/entities/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        deleteEntity(id);
        if (selectedEntityId === id) setSelectedEntityId(null);
        toast.success('已删除');
      }
    } catch (e) {
      toast.error('删除失败');
    }
  };

  // AI 提取实体
  const handleExtract = async (type?: string) => {
    if (!currentNovel) return;
    setIsExtracting(true);
    try {
      const url = type
        ? `${API_URL}/worldbuilding/entities/extract?novel_id=${currentNovel.id}&entity_type=${type}`
        : `${API_URL}/worldbuilding/entities/extract?novel_id=${currentNovel.id}`;
      const res = await fetch(url, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        // 重新加载
        const loadRes = await fetch(
          `${API_URL}/worldbuilding/entities?novel_id=${currentNovel.id}`
        );
        if (loadRes.ok) {
          setEntities(await loadRes.json());
        }
        toast.success(`提取了 ${data.data?.count || 0} 个实体`);
      } else {
        toast.error(data.error || '提取失败');
      }
    } catch (e) {
      toast.error('AI提取失败');
    } finally {
      setIsExtracting(false);
    }
  };

  // AI 提取术语表
  const handleAutoTerminology = async () => {
    if (!currentNovel) return;
    setIsExtracting(true);
    try {
      const res = await fetch(`${API_URL}/worldbuilding/terminology/auto?novel_id=${currentNovel.id}`, {
        method: 'POST',
      });
      const data = await res.json();
      if (data.success) {
        const loadRes = await fetch(
          `${API_URL}/worldbuilding/entities?novel_id=${currentNovel.id}`
        );
        if (loadRes.ok) {
          setEntities(await loadRes.json());
        }
        toast.success(`提取了 ${data.data?.count || 0} 个术语`);
      } else {
        toast.error(data.error || '提取失败');
      }
    } catch (e) {
      toast.error('提取术语失败');
    } finally {
      setIsExtracting(false);
    }
  };

  // 一致性检查
  const handleConsistencyCheck = async () => {
    if (!currentNovel) return;
    setIsChecking(true);
    setShowConsistency(true);
    setConsistencyIssues([]);
    try {
      const res = await fetch(
        `${API_URL}/worldbuilding/consistency/check?novel_id=${currentNovel.id}`,
        { method: 'POST' }
      );
      const data = await res.json();
      setConsistencyIssues(data.issues || []);
      toast.success(`检查完成，发现 ${data.totalIssues || 0} 个问题`);
    } catch (e) {
      toast.error('一致性检查失败');
    } finally {
      setIsChecking(false);
    }
  };

  // 深度检查
  const handleDeepCheck = async () => {
    if (!currentNovel) return;
    setIsDeepChecking(true);
    setShowConsistency(true);
    setConsistencyIssues([]);
    try {
      const res = await fetch(
        `${API_URL}/worldbuilding/consistency/deep-check?novel_id=${currentNovel.id}`,
        { method: 'POST' }
      );
      const data = await res.json();
      setConsistencyIssues(data.issues || []);
      toast.success(`深度检查完成，发现 ${data.totalIssues || 0} 个问题`);
    } catch (e) {
      toast.error('深度一致性检查失败');
    } finally {
      setIsDeepChecking(false);
    }
  };

  // 选中实体详情
  const selectedEntity = entities.find((e) => e.id === selectedEntityId);

  if (!currentNovel) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        请先选择一部小说
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* 左侧：实体列表 */}
      <div className="w-80 border-r flex flex-col">
        {/* 搜索和操作栏 */}
        <div className="p-3 border-b space-y-2">
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索实体..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 h-9"
              />
            </div>
            <Button
              variant="outline"
              size="icon"
              className="h-9 w-9"
              onClick={() => {
                setEditingEntity({ entityType: 'location', name: '', description: '' });
                setEditDialogOpen(true);
              }}
              title="新建实体"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>

          {/* 类型过滤 */}
          <div className="flex flex-wrap gap-1">
            <Button
              variant={activeType === 'all' ? 'default' : 'outline'}
              size="sm"
              className="h-7 text-xs"
              onClick={() => setActiveType('all')}
            >
              全部 ({entities.length})
            </Button>
            {ENTITY_TYPES.map((t) => (
              <Button
                key={t.value}
                variant={activeType === t.value ? 'default' : 'outline'}
                size="sm"
                className="h-7 text-xs"
                onClick={() => setActiveType(t.value)}
              >
                <t.icon className="h-3 w-3 mr-1" />
                {t.label} ({typeCounts[t.value] || 0})
              </Button>
            ))}
          </div>

          {/* AI 操作 */}
          <div className="flex gap-1">
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs flex-1"
              onClick={() => handleExtract()}
              disabled={isExtracting}
            >
              {isExtracting ? (
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
              ) : (
                <Zap className="h-3 w-3 mr-1" />
              )}
              AI提取
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs flex-1"
              onClick={handleAutoTerminology}
              disabled={isExtracting}
            >
              术语表
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs flex-1"
              onClick={handleConsistencyCheck}
              disabled={isChecking || isDeepChecking}
            >
              {isChecking ? (
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
              ) : (
                <CheckCircle2 className="h-3 w-3 mr-1" />
              )}
              检查
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs flex-1"
              onClick={handleDeepCheck}
              disabled={isChecking || isDeepChecking}
            >
              {isDeepChecking ? (
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
              ) : (
                <Search className="h-3 w-3 mr-1" />
              )}
              深度检查
            </Button>
          </div>
        </div>

        {/* 实体列表 */}
        <ScrollArea className="flex-1">
          <div className="p-2 space-y-1">
            {filteredEntities.map((entity) => {
              const typeInfo = ENTITY_TYPES.find((t) => t.value === entity.entityType);
              const isSelected = selectedEntityId === entity.id;

              return (
                <div
                  key={entity.id}
                  className={`p-2 rounded-md cursor-pointer text-sm transition-colors group ${
                    isSelected ? 'bg-primary/10 border border-primary/20' : 'hover:bg-muted'
                  }`}
                  onClick={() => setSelectedEntityId(isSelected ? null : entity.id)}
                >
                  <div className="flex items-center gap-2">
                    {typeInfo && (
                      <typeInfo.icon className={`h-4 w-4 shrink-0 ${typeInfo.color}`} />
                    )}
                    <span className="font-medium truncate flex-1">{entity.name}</span>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingEntity({ ...entity });
                          setEditDialogOpen(true);
                        }}
                      >
                        <Edit3 className="h-3 w-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteEntity(entity.id);
                        }}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                  {entity.description && (
                    <div className="text-xs text-muted-foreground mt-0.5 ml-6 line-clamp-2">
                      {entity.description}
                    </div>
                  )}
                </div>
              );
            })}
            {filteredEntities.length === 0 && (
              <div className="text-sm text-muted-foreground text-center py-8">
                {entities.length === 0
                  ? '暂无世界观数据，点击AI提取或手动创建'
                  : '没有匹配的实体'}
              </div>
            )}
          </div>
        </ScrollArea>
      </div>

      {/* 右侧：详情/一致性检查 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {showConsistency ? (
          // 一致性检查结果
          <div className="flex-1 overflow-auto p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5" />
                一致性检查结果
              </h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowConsistency(false)}
              >
                关闭
              </Button>
            </div>

            {isChecking || isDeepChecking ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin mr-2" />
                <span>正在{isDeepChecking ? '深度' : ''}检查一致性...</span>
              </div>
            ) : consistencyIssues.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <CheckCircle2 className="h-12 w-12 mx-auto mb-2 text-green-500" />
                <p>未发现一致性问题</p>
              </div>
            ) : (
              <div className="space-y-3">
                {consistencyIssues.map((issue, idx) => {
                  const style = SEVERITY_STYLES[issue.severity] || SEVERITY_STYLES.info;
                  const IconComp = style.icon;

                  // Expanded type icon & label mapping
                  const TYPE_ICON_MAP: Record<string, { icon: typeof Users; label: string }> = {
                    character: { icon: Users, label: '人物' },
                    timeline: { icon: Calendar, label: '时间线' },
                    rule: { icon: BookOpen, label: '规则' },
                    relation: { icon: Users, label: '关系' },
                    power_system: { icon: Zap, label: '战力' },
                    geography: { icon: MapPin, label: '地理' },
                    naming: { icon: Type, label: '称呼' },
                  };
                  const typeInfo = TYPE_ICON_MAP[issue.type] ?? { icon: Info, label: issue.type };
                  const TypeIcon = typeInfo.icon;

                  const showSuggestion = showSuggestions[idx];

                  return (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg border ${style.color}`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <IconComp className="h-4 w-4" />
                        <span className="font-medium text-sm">{issue.description}</span>
                        <span className="text-xs px-1.5 py-0.5 rounded bg-background/50 flex items-center gap-1">
                          <TypeIcon className="h-3 w-3" />
                          {typeInfo.label}
                        </span>
                      </div>
                      {issue.detail && (
                        <p className="text-xs mt-1 text-muted-foreground">{issue.detail}</p>
                      )}
                      <div className="flex items-center gap-4 mt-2 text-xs">
                        {issue.chapterA && (
                          <span>章节A: {issue.chapterA}</span>
                        )}
                        {issue.chapterB && (
                          <span>章节B: {issue.chapterB}</span>
                        )}
                      </div>
                      {issue.suggestion && (
                        <div className="mt-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 text-xs px-2"
                            onClick={() =>
                              setShowSuggestions((prev) => ({
                                ...prev,
                                [idx]: !prev[idx],
                              }))
                            }
                          >
                            {showSuggestion ? '收起建议' : '修复建议'}
                          </Button>
                          {showSuggestion && (
                            <div className="mt-1 p-2 rounded bg-background/30 text-xs">
                              <span className="font-medium">建议：</span>
                              {issue.suggestion}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ) : selectedEntity ? (
          // 实体详情
          <ScrollArea className="flex-1">
            <div className="p-4 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {(() => {
                    const typeInfo = ENTITY_TYPES.find(
                      (t) => t.value === selectedEntity.entityType
                    );
                    return typeInfo ? (
                      <typeInfo.icon className={`h-5 w-5 ${typeInfo.color}`} />
                    ) : null;
                  })()}
                  <h3 className="text-lg font-semibold">{selectedEntity.name}</h3>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-muted">
                    {ENTITY_TYPES.find((t) => t.value === selectedEntity.entityType)?.label ||
                      selectedEntity.entityType}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-muted">
                    {selectedEntity.source === 'ai' ? 'AI提取' : '手动创建'}
                  </span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setEditingEntity({ ...selectedEntity });
                    setEditDialogOpen(true);
                  }}
                >
                  <Edit3 className="h-4 w-4 mr-1" />
                  编辑
                </Button>
              </div>

              {selectedEntity.description && (
                <div>
                  <h4 className="text-sm font-medium mb-1">描述</h4>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                    {selectedEntity.description}
                  </p>
                </div>
              )}

              {selectedEntity.rules && (
                <div>
                  <h4 className="text-sm font-medium mb-1">规则/约束</h4>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                    {selectedEntity.rules}
                  </p>
                </div>
              )}

              {selectedEntity.attributes &&
                Object.keys(selectedEntity.attributes).length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium mb-1">属性</h4>
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(selectedEntity.attributes).map(([key, value]) => (
                        <div key={key} className="p-2 rounded bg-muted text-sm">
                          <span className="font-medium">{key}：</span>
                          <span className="text-muted-foreground">{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              {/* 关联关系 */}
              {entityRelations.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-1">关联关系</h4>
                  <div className="space-y-1">
                    {entityRelations
                      .filter(
                        (r) =>
                          r.sourceId === selectedEntity.id ||
                          r.targetId === selectedEntity.id
                      )
                      .map((rel) => {
                        const isSource = rel.sourceId === selectedEntity.id;
                        const otherName = isSource ? rel.targetName : rel.sourceName;
                        return (
                          <div key={rel.id} className="p-2 rounded bg-muted text-sm">
                            <span className="font-medium">{otherName}</span>
                            <span className="text-muted-foreground">
                              {' '}
                              — {rel.relationType}
                              {rel.description ? `: ${rel.description}` : ''}
                            </span>
                          </div>
                        );
                      })}
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>
        ) : (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            <div className="text-center">
              <Globe className="h-12 w-12 mx-auto mb-2 opacity-30" />
              <p>从左侧选择实体查看详情</p>
              <p className="text-sm mt-1">或点击「AI提取」自动从小说中提取世界观元素</p>
            </div>
          </div>
        )}
      </div>

      {/* 编辑对话框 */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingEntity?.id ? '编辑实体' : '新建实体'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">名称</label>
              <Input
                value={editingEntity?.name || ''}
                onChange={(e) =>
                  setEditingEntity((prev) => prev ? { ...prev, name: e.target.value } : prev)
                }
                placeholder="实体名称"
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">类型</label>
              <div className="flex flex-wrap gap-2 mt-1">
                {ENTITY_TYPES.map((t) => (
                  <Button
                    key={t.value}
                    variant={editingEntity?.entityType === t.value ? 'default' : 'outline'}
                    size="sm"
                    onClick={() =>
                      setEditingEntity((prev) => prev ? { ...prev, entityType: t.value } : prev)
                    }
                  >
                    <t.icon className="h-3 w-3 mr-1" />
                    {t.label}
                  </Button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-sm font-medium">描述</label>
              <Textarea
                value={editingEntity?.description || ''}
                onChange={(e) =>
                  setEditingEntity((prev) => prev ? { ...prev, description: e.target.value } : prev)
                }
                placeholder="详细描述..."
                rows={4}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">规则/约束（可选）</label>
              <Textarea
                value={editingEntity?.rules || ''}
                onChange={(e) =>
                  setEditingEntity((prev) => prev ? { ...prev, rules: e.target.value } : prev)
                }
                placeholder="如：魔法消耗精神力..."
                rows={2}
                className="mt-1"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSaveEntity}>保存</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
