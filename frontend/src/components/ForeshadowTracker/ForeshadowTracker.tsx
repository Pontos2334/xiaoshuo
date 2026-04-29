'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Loader2,
  BookMarked,
  AlertTriangle,
  Sparkles,
  Plus,
  Trash2,
  Edit3,
  Search,
} from 'lucide-react';
import { toast } from 'sonner';
import { useNovelStore, useForeshadowStore, useCharacterStore } from '@/stores';
import { API_URL } from '@/lib/constants';
import type { Foreshadow } from '@/types';

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

type ForeshadowStatus = Foreshadow['status'];

const STATUS_CONFIG: Record<
  ForeshadowStatus,
  { label: string; color: string; bg: string; hex: string }
> = {
  planted: { label: '已埋笔', color: 'text-amber-700', bg: 'bg-amber-100', hex: '#f59e0b' },
  partially_revealed: {
    label: '部分揭示',
    color: 'text-blue-700',
    bg: 'bg-blue-100',
    hex: '#3b82f6',
  },
  resolved: { label: '已回收', color: 'text-green-700', bg: 'bg-green-100', hex: '#22c55e' },
  abandoned: { label: '已放弃', color: 'text-gray-600', bg: 'bg-gray-100', hex: '#9ca3af' },
};

const STATUS_OPTIONS: ForeshadowStatus[] = [
  'planted',
  'partially_revealed',
  'resolved',
  'abandoned',
];

/* ------------------------------------------------------------------ */
/*  Timeline helpers                                                   */
/* ------------------------------------------------------------------ */

interface TimelineBar {
  foreshadow: Foreshadow;
  row: number;
  x: number;
  width: number;
}

function computeTimelineBars(
  foreshadows: Foreshadow[],
  svgWidth: number,
  barHeight: number
): { bars: TimelineBar[]; rows: number; minCh: number; maxCh: number } {
  if (foreshadows.length === 0) return { bars: [], rows: 0, minCh: 0, maxCh: 0 };

  const minCh = Math.min(...foreshadows.map((f) => f.plantChapter));
  const maxCh = Math.max(
    ...foreshadows.map((f) => f.resolveChapter ?? f.plantChapter)
  );
  const span = Math.max(maxCh - minCh, 1);
  const padding = 40;
  const usable = svgWidth - padding * 2;

  // Greedy row assignment to avoid horizontal overlap
  const rowEnds: number[] = [];
  const sorted = [...foreshadows].sort((a, b) => a.plantChapter - b.plantChapter);

  const bars: TimelineBar[] = sorted.map((f) => {
    const start = f.plantChapter;
    const end = f.resolveChapter ?? maxCh;
    const x = padding + ((start - minCh) / span) * usable;
    const width = Math.max(((end - start) / span) * usable, 20);

    let row = rowEnds.findIndex((re) => re < start);
    if (row === -1) {
      row = rowEnds.length;
      rowEnds.push(end);
    } else {
      rowEnds[row] = end;
    }

    return { foreshadow: f, row, x, width };
  });

  return { bars, rows: rowEnds.length, minCh, maxCh };
}

/* ------------------------------------------------------------------ */
/*  Alert type                                                         */
/* ------------------------------------------------------------------ */

interface ForeshadowAlert {
  id: string;
  title: string;
  chaptersSincePlant: number;
  suggestion?: string;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function ForeshadowTracker() {
  const { currentNovel } = useNovelStore();
  const { characters } = useCharacterStore();
  const {
    foreshadows,
    selectedForeshadowId,
    setForeshadows,
    setSelectedForeshadowId,
    addForeshadow,
    updateForeshadow,
    deleteForeshadow,
  } = useForeshadowStore();

  /* ---- local state ---- */
  const [isLoading, setIsLoading] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<ForeshadowStatus | 'all'>('all');
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<Partial<Foreshadow> | null>(null);
  const [alerts, setAlerts] = useState<ForeshadowAlert[]>([]);
  const [alertsLoading, setAlertsLoading] = useState(false);
  const [suggestingId, setSuggestingId] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<Record<string, string>>({});

  /* ---- derived ---- */
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = { all: foreshadows.length };
    for (const f of foreshadows) {
      counts[f.status] = (counts[f.status] || 0) + 1;
    }
    return counts;
  }, [foreshadows]);

  const filtered = useMemo(() => {
    return foreshadows.filter((f) => {
      if (statusFilter !== 'all' && f.status !== statusFilter) return false;
      if (searchQuery && !f.title.includes(searchQuery) && !f.description.includes(searchQuery))
        return false;
      return true;
    });
  }, [foreshadows, statusFilter, searchQuery]);

  const selected = useMemo(
    () => foreshadows.find((f) => f.id === selectedForeshadowId) ?? null,
    [foreshadows, selectedForeshadowId]
  );

  /* ---- data loading ---- */
  const loadForeshadows = useCallback(async () => {
    if (!currentNovel) return;
    setIsLoading(true);
    try {
      const res = await fetch(`${API_URL}/foreshadows?novel_id=${currentNovel.id}`);
      if (res.ok) {
        const data = await res.json();
        setForeshadows(Array.isArray(data) ? data : data.data ?? []);
      }
    } catch {
      console.error('加载伏笔列表失败');
      toast.error('加载伏笔列表失败');
    } finally {
      setIsLoading(false);
    }
  }, [currentNovel, setForeshadows]);

  useEffect(() => {
    loadForeshadows();
  }, [loadForeshadows]);

  /* ---- alerts loading ---- */
  const loadAlerts = useCallback(async () => {
    if (!currentNovel) return;
    setAlertsLoading(true);
    try {
      const res = await fetch(
        `${API_URL}/foreshadows/alerts?novel_id=${currentNovel.id}&threshold=50`
      );
      if (res.ok) {
        const data = await res.json();
        setAlerts(Array.isArray(data) ? data : data.alerts ?? []);
      }
    } catch {
      console.error('加载伏笔告警失败');
      toast.error('加载伏笔告警失败');
    } finally {
      setAlertsLoading(false);
    }
  }, [currentNovel]);

  /* ---- CRUD operations ---- */
  const handleSave = async () => {
    if (!editingItem || !currentNovel) return;
    if (!editingItem.title?.trim()) {
      toast.error('请填写标题');
      return;
    }
    try {
      if (editingItem.id) {
        const res = await fetch(`${API_URL}/foreshadows/${editingItem.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(editingItem),
        });
        if (res.ok) {
          const updated = await res.json();
          updateForeshadow(editingItem.id, updated);
          toast.success('更新成功');
        }
      } else {
        const res = await fetch(`${API_URL}/foreshadows`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ...editingItem, novelId: currentNovel.id }),
        });
        if (res.ok) {
          const created = await res.json();
          addForeshadow(created);
          toast.success('创建成功');
        }
      }
      setEditDialogOpen(false);
      setEditingItem(null);
    } catch {
      toast.error('保存失败');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('确定删除该伏笔？')) return;
    try {
      const res = await fetch(`${API_URL}/foreshadows/${id}`, { method: 'DELETE' });
      if (res.ok) {
        deleteForeshadow(id);
        if (selectedForeshadowId === id) setSelectedForeshadowId(null);
        toast.success('已删除');
      }
    } catch {
      toast.error('删除失败');
    }
  };

  const handleExtract = async () => {
    if (!currentNovel) return;
    setIsExtracting(true);
    try {
      const res = await fetch(
        `${API_URL}/foreshadows/extract?novel_id=${currentNovel.id}`,
        { method: 'POST' }
      );
      const data = await res.json();
      if (data.success !== false) {
        await loadForeshadows();
        toast.success(`提取了 ${data.count ?? '若干'} 条伏笔`);
      } else {
        toast.error(data.error || '提取失败');
      }
    } catch {
      toast.error('AI 提取失败');
    } finally {
      setIsExtracting(false);
    }
  };

  const handleSuggest = async (id: string) => {
    setSuggestingId(id);
    try {
      const res = await fetch(`${API_URL}/foreshadows/${id}/suggest-resolution`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        setSuggestions((prev) => ({ ...prev, [id]: data.suggestion ?? data.data ?? '' }));
      }
    } catch {
      toast.error('获取建议失败');
    } finally {
      setSuggestingId(null);
    }
  };

  /* ---- importance dots ---- */
  const renderImportance = (n: number) => (
    <div className="flex gap-0.5">
      {Array.from({ length: 10 }).map((_, i) => (
        <span
          key={i}
          className={`inline-block h-1.5 w-1.5 rounded-full ${
            i < n ? 'bg-amber-500' : 'bg-gray-200'
          }`}
        />
      ))}
    </div>
  );

  /* ---- empty guard ---- */
  if (!currentNovel) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        请先选择一部小说
      </div>
    );
  }

  /* ---- timeline data ---- */
  const timeline = useMemo(
    () => computeTimelineBars(filtered, 700, 28),
    [filtered]
  );

  /* ================================================================ */
  /*  Render                                                           */
  /* ================================================================ */

  return (
    <div className="flex h-full">
      {/* ---------- Left Panel ---------- */}
      <div className="w-80 border-r flex flex-col bg-white">
        {/* Header */}
        <div className="p-3 border-b space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-sm flex items-center gap-1.5">
              <BookMarked className="h-4 w-4" />
              伏笔追踪
            </h2>
            <div className="flex gap-1">
              {STATUS_OPTIONS.map((s) => {
                const cfg = STATUS_CONFIG[s];
                return (
                  <Badge key={s} variant="secondary" className={`text-[10px] px-1.5 py-0 ${cfg.bg} ${cfg.color}`}>
                    {statusCounts[s] || 0}
                  </Badge>
                );
              })}
            </div>
          </div>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="搜索伏笔..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 h-9"
            />
          </div>

          {/* Status filter row */}
          <div className="flex flex-wrap gap-1">
            <Button
              variant={statusFilter === 'all' ? 'default' : 'outline'}
              size="sm"
              className="h-7 text-xs"
              onClick={() => setStatusFilter('all')}
            >
              全部 ({statusCounts.all || 0})
            </Button>
            {STATUS_OPTIONS.map((s) => {
              const cfg = STATUS_CONFIG[s];
              return (
                <Button
                  key={s}
                  variant={statusFilter === s ? 'default' : 'outline'}
                  size="sm"
                  className={`h-7 text-xs ${statusFilter === s ? cfg.bg + ' ' + cfg.color : ''}`}
                  onClick={() => setStatusFilter(s)}
                >
                  {cfg.label} ({statusCounts[s] || 0})
                </Button>
              );
            })}
          </div>

          {/* Action buttons */}
          <div className="flex gap-2">
            <Button size="sm" className="flex-1 h-8" onClick={handleExtract} disabled={isExtracting}>
              {isExtracting ? (
                <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
              ) : (
                <Sparkles className="h-3.5 w-3.5 mr-1" />
              )}
              AI 提取
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="flex-1 h-8"
              onClick={() => {
                setEditingItem({
                  title: '',
                  description: '',
                  status: 'planted',
                  importance: 5,
                  plantChapter: 1,
                  plantDescription: '',
                  resolveChapter: null,
                  resolveDescription: null,
                  relatedCharacters: [],
                  relatedPlots: [],
                  source: 'user',
                });
                setEditDialogOpen(true);
              }}
            >
              <Plus className="h-3.5 w-3.5 mr-1" />
              手动添加
            </Button>
          </div>
        </div>

        {/* List */}
        <ScrollArea className="flex-1">
          <div className="p-2 space-y-1">
            {isLoading && foreshadows.length === 0 ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-5 w-5 animate-spin mr-2" />
                <span className="text-sm text-muted-foreground">加载中...</span>
              </div>
            ) : (
              filtered.map((f) => {
                const cfg = STATUS_CONFIG[f.status];
                const isSelected = selectedForeshadowId === f.id;
                return (
                  <div
                    key={f.id}
                    className={`p-2 rounded-lg cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-primary/10 border border-primary/20'
                        : 'hover:bg-muted/60'
                    }`}
                    onClick={() =>
                      setSelectedForeshadowId(isSelected ? null : f.id)
                    }
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm truncate flex-1">
                        {f.title}
                      </span>
                      <Badge
                        variant="secondary"
                        className={`text-[10px] px-1.5 py-0 shrink-0 ${cfg.bg} ${cfg.color}`}
                      >
                        {cfg.label}
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      第{f.plantChapter}章埋笔
                    </div>
                    {renderImportance(f.importance)}
                  </div>
                );
              })
            )}
            {!isLoading && filtered.length === 0 && (
              <div className="text-sm text-muted-foreground text-center py-8">
                {foreshadows.length === 0
                  ? '暂无伏笔数据，点击 AI 提取或手动添加'
                  : '没有匹配的伏笔'}
              </div>
            )}
          </div>
        </ScrollArea>
      </div>

      {/* ---------- Right Panel ---------- */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <Tabs defaultValue="detail" className="flex-1 flex flex-col">
          <div className="px-4 pt-3 border-b">
            <TabsList>
              <TabsTrigger value="detail">详情</TabsTrigger>
              <TabsTrigger value="timeline">时间线</TabsTrigger>
              <TabsTrigger value="alerts" onClick={loadAlerts}>
                告警
              </TabsTrigger>
            </TabsList>
          </div>

          {/* ---- Detail Tab ---- */}
          <TabsContent value="detail" className="flex-1 overflow-auto m-0">
            {selected ? (
              <div className="p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <h3 className="text-lg font-semibold">{selected.title}</h3>
                    <Badge className={`${STATUS_CONFIG[selected.status].bg} ${STATUS_CONFIG[selected.status].color}`}>
                      {STATUS_CONFIG[selected.status].label}
                    </Badge>
                    <Badge variant="outline">
                      {selected.source === 'ai' ? 'AI' : '手动'}
                    </Badge>
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setEditingItem({ ...selected });
                        setEditDialogOpen(true);
                      }}
                    >
                      <Edit3 className="h-3.5 w-3.5 mr-1" />
                      编辑
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-red-600 hover:text-red-700"
                      onClick={() => handleDelete(selected.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5 mr-1" />
                      删除
                    </Button>
                  </div>
                </div>

                <Card>
                  <CardContent className="pt-4 space-y-3">
                    <div>
                      <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                        描述
                      </span>
                      <p className="text-sm mt-1 whitespace-pre-wrap">
                        {selected.description || '无'}
                      </p>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <span className="text-xs font-medium text-muted-foreground">
                          埋笔章节
                        </span>
                        <p className="text-sm mt-0.5">第 {selected.plantChapter} 章</p>
                      </div>
                      <div>
                        <span className="text-xs font-medium text-muted-foreground">
                          回收章节
                        </span>
                        <p className="text-sm mt-0.5">
                          {selected.resolveChapter != null
                            ? `第 ${selected.resolveChapter} 章`
                            : '未回收'}
                        </p>
                      </div>
                    </div>
                    {selected.plantDescription && (
                      <div>
                        <span className="text-xs font-medium text-muted-foreground">
                          埋笔描述
                        </span>
                        <p className="text-sm mt-0.5 whitespace-pre-wrap">
                          {selected.plantDescription}
                        </p>
                      </div>
                    )}
                    {selected.resolveDescription && (
                      <div>
                        <span className="text-xs font-medium text-muted-foreground">
                          回收描述
                        </span>
                        <p className="text-sm mt-0.5 whitespace-pre-wrap">
                          {selected.resolveDescription}
                        </p>
                      </div>
                    )}
                    <div>
                      <span className="text-xs font-medium text-muted-foreground">
                        重要度
                      </span>
                      <div className="mt-0.5">{renderImportance(selected.importance)}</div>
                    </div>
                    {selected.relatedCharacters.length > 0 && (
                      <div>
                        <span className="text-xs font-medium text-muted-foreground">
                          关联人物
                        </span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {selected.relatedCharacters.map((cid) => {
                            const ch = characters.find((c) => c.id === cid);
                            return (
                              <Badge key={cid} variant="secondary" className="text-xs">
                                {ch?.name ?? cid}
                              </Badge>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                <div className="text-center">
                  <BookMarked className="h-12 w-12 mx-auto mb-2 opacity-30" />
                  <p>选择伏笔查看详情</p>
                </div>
              </div>
            )}
          </TabsContent>

          {/* ---- Timeline Tab ---- */}
          <TabsContent value="timeline" className="flex-1 overflow-auto m-0 p-4">
            {timeline.bars.length === 0 ? (
              <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                暂无伏笔数据可展示时间线
              </div>
            ) : (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">伏笔时间线</CardTitle>
                </CardHeader>
                <CardContent>
                  <svg
                    width="100%"
                    viewBox={`0 0 700 ${timeline.rows * 40 + 30}`}
                    className="select-none"
                  >
                    {/* axis line */}
                    <line
                      x1={40}
                      y1={timeline.rows * 40 + 10}
                      x2={660}
                      y2={timeline.rows * 40 + 10}
                      stroke="#e5e7eb"
                      strokeWidth={1}
                    />
                    {timeline.minCh !== timeline.maxCh && (
                      <>
                        <text x={40} y={timeline.rows * 40 + 24} className="text-[10px]" fill="#9ca3af">
                          第{timeline.minCh}章
                        </text>
                        <text x={640} y={timeline.rows * 40 + 24} className="text-[10px]" fill="#9ca3af" textAnchor="end">
                          第{timeline.maxCh}章
                        </text>
                      </>
                    )}
                    {timeline.bars.map((bar) => {
                      const cfg = STATUS_CONFIG[bar.foreshadow.status];
                      return (
                        <g
                          key={bar.foreshadow.id}
                          className="cursor-pointer"
                          onClick={() => setSelectedForeshadowId(bar.foreshadow.id)}
                        >
                          <rect
                            x={bar.x}
                            y={bar.row * 40}
                            width={bar.width}
                            height={28}
                            rx={4}
                            fill={cfg.hex}
                            opacity={selectedForeshadowId === bar.foreshadow.id ? 1 : 0.7}
                          />
                          <text
                            x={bar.x + 6}
                            y={bar.row * 40 + 18}
                            fill="white"
                            fontSize={11}
                            className="pointer-events-none"
                          >
                            {bar.foreshadow.title.length * 11 > bar.width - 12
                              ? bar.foreshadow.title.slice(0, Math.max(1, Math.floor((bar.width - 12) / 11))) + '...'
                              : bar.foreshadow.title}
                          </text>
                          <title>{bar.foreshadow.title}</title>
                        </g>
                      );
                    })}
                  </svg>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* ---- Alerts Tab ---- */}
          <TabsContent value="alerts" className="flex-1 overflow-auto m-0 p-4">
            {alertsLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-5 w-5 animate-spin mr-2" />
                <span className="text-sm text-muted-foreground">加载告警...</span>
              </div>
            ) : alerts.length === 0 ? (
              <div className="flex items-center justify-center h-full text-muted-foreground">
                <div className="text-center">
                  <AlertTriangle className="h-12 w-12 mx-auto mb-2 opacity-30" />
                  <p>暂无伏笔告警</p>
                  <p className="text-sm mt-1">所有伏笔都在正常范围内</p>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {alerts.map((alert) => (
                  <Card key={alert.id}>
                    <CardContent className="pt-4 space-y-2">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />
                        <span className="font-medium text-sm">{alert.title}</span>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        已埋笔 {alert.chaptersSincePlant} 章，可能被遗忘
                      </p>
                      {suggestions[alert.id] && (
                        <div className="p-2 rounded-md bg-muted text-sm whitespace-pre-wrap">
                          {suggestions[alert.id]}
                        </div>
                      )}
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-7 text-xs"
                        disabled={suggestingId === alert.id}
                        onClick={() => handleSuggest(alert.id)}
                      >
                        {suggestingId === alert.id ? (
                          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                        ) : (
                          <Sparkles className="h-3 w-3 mr-1" />
                        )}
                        获取建议
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>

      {/* ---------- Edit Dialog ---------- */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingItem?.id ? '编辑伏笔' : '新建伏笔'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium">标题</label>
              <Input
                className="mt-1"
                value={editingItem?.title ?? ''}
                onChange={(e) =>
                  setEditingItem((prev) => (prev ? { ...prev, title: e.target.value } : prev))
                }
                placeholder="伏笔标题"
              />
            </div>
            <div>
              <label className="text-sm font-medium">描述</label>
              <textarea
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm min-h-[60px] focus:outline-none focus:ring-2 focus:ring-ring"
                value={editingItem?.description ?? ''}
                onChange={(e) =>
                  setEditingItem((prev) => (prev ? { ...prev, description: e.target.value } : prev))
                }
                placeholder="伏笔描述..."
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium">状态</label>
                <select
                  className="mt-1 w-full h-9 rounded-md border px-2 text-sm"
                  value={editingItem?.status ?? 'planted'}
                  onChange={(e) =>
                    setEditingItem((prev) =>
                      prev ? { ...prev, status: e.target.value as ForeshadowStatus } : prev
                    )
                  }
                >
                  {STATUS_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                      {STATUS_CONFIG[s].label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium">重要度 (1-10)</label>
                <Input
                  type="number"
                  min={1}
                  max={10}
                  className="mt-1"
                  value={editingItem?.importance ?? 5}
                  onChange={(e) =>
                    setEditingItem((prev) =>
                      prev
                        ? { ...prev, importance: Math.min(10, Math.max(1, Number(e.target.value))) }
                        : prev
                    )
                  }
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium">埋笔章节</label>
                <Input
                  type="number"
                  min={1}
                  className="mt-1"
                  value={editingItem?.plantChapter ?? 1}
                  onChange={(e) =>
                    setEditingItem((prev) =>
                      prev ? { ...prev, plantChapter: Number(e.target.value) } : prev
                    )
                  }
                />
              </div>
              <div>
                <label className="text-sm font-medium">回收章节</label>
                <Input
                  type="number"
                  min={1}
                  className="mt-1"
                  value={editingItem?.resolveChapter ?? ''}
                  onChange={(e) =>
                    setEditingItem((prev) =>
                      prev
                        ? { ...prev, resolveChapter: e.target.value ? Number(e.target.value) : null }
                        : prev
                    )
                  }
                  placeholder="未回收"
                />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium">回收描述</label>
              <textarea
                className="mt-1 w-full rounded-md border px-3 py-2 text-sm min-h-[40px] focus:outline-none focus:ring-2 focus:ring-ring"
                value={editingItem?.resolveDescription ?? ''}
                onChange={(e) =>
                  setEditingItem((prev) =>
                    prev ? { ...prev, resolveDescription: e.target.value || null } : prev
                  )
                }
                placeholder="如何回收该伏笔..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave}>保存</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
