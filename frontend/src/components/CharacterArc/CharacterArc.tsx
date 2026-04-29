'use client';

import { useState, useEffect, useCallback } from 'react';
import { useNovelStore, useCharacterStore, useCharacterArcStore } from '@/stores';
import { API_URL } from '@/lib/constants';
import type { CharacterArcPoint, ArcInconsistency } from '@/types';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Brain,
  TrendingUp,
  Loader2,
  AlertTriangle,
  Info,
  Sparkles,
  ChevronRight,
  Heart,
  Zap,
  XCircle,
} from 'lucide-react';
import { toast } from 'sonner';

// ---------------------------------------------------------------------------
// Growth curve SVG sub-component
// ---------------------------------------------------------------------------

interface GrowthDataPoint {
  chapter: number;
  level: number;
}

const GrowthChart = ({
  data,
  onPointClick,
  highlightedChapter,
}: {
  data: GrowthDataPoint[];
  onPointClick?: (chapter: number) => void;
  highlightedChapter?: number | null;
}) => {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-[240px] text-muted-foreground text-sm">
        暂无成长数据
      </div>
    );
  }

  const sorted = [...data].sort((a, b) => a.chapter - b.chapter);

  const padding = { left: 30, right: 20, top: 20, bottom: 30 };
  const chartWidth = Math.max(sorted.length * 40, 200);
  const chartHeight = 200;
  const plotW = chartWidth - padding.left - padding.right;
  const plotH = chartHeight - padding.top - padding.bottom;

  const minLevel = 1;
  const maxLevel = 10;

  const scaleX = (i: number) => padding.left + (i / Math.max(sorted.length - 1, 1)) * plotW;
  const scaleY = (level: number) =>
    padding.top + plotH - ((level - minLevel) / (maxLevel - minLevel)) * plotH;

  const points = sorted.map((d, i) => ({ ...d, x: scaleX(i), y: scaleY(d.level) }));
  const polylineStr = points.map((p) => `${p.x},${p.y}`).join(' ');

  // Build gradient polygon (close the shape at the bottom)
  const areaStr =
    points.length > 0
      ? `M ${points[0].x},${padding.top + plotH} ` +
        points.map((p) => `L ${p.x},${p.y}`).join(' ') +
        ` L ${points[points.length - 1].x},${padding.top + plotH} Z`
      : '';

  // Y-axis ticks
  const yTicks = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

  return (
    <ScrollArea className="w-full">
      <svg
        viewBox={`0 0 ${chartWidth} ${chartHeight}`}
        className="w-full"
        style={{ minWidth: chartWidth }}
      >
        <defs>
          <linearGradient id="arcGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.25" />
            <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {/* Grid lines */}
        {yTicks.map((tick) => (
          <line
            key={tick}
            x1={padding.left}
            y1={scaleY(tick)}
            x2={chartWidth - padding.right}
            y2={scaleY(tick)}
            stroke="hsl(var(--border))"
            strokeWidth="0.5"
            strokeDasharray="4 2"
          />
        ))}

        {/* Gradient fill */}
        {areaStr && <path d={areaStr} fill="url(#arcGrad)" />}

        {/* Polyline */}
        <polyline
          points={polylineStr}
          fill="none"
          stroke="hsl(var(--primary))"
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {/* Data point circles */}
        {points.map((p) => {
          const isHighlighted = highlightedChapter === p.chapter;
          return (
            <g
              key={p.chapter}
              onClick={() => onPointClick?.(p.chapter)}
              style={{ cursor: onPointClick ? 'pointer' : 'default' }}
            >
              {isHighlighted && (
                <circle cx={p.x} cy={p.y} r={10} fill="hsl(var(--primary))" opacity={0.15} />
              )}
              <circle
                cx={p.x}
                cy={p.y}
                r={isHighlighted ? 5 : 3.5}
                fill={isHighlighted ? 'hsl(var(--primary))' : 'hsl(var(--card))'}
                stroke="hsl(var(--primary))"
                strokeWidth={isHighlighted ? 2.5 : 2}
              />
            </g>
          );
        })}

        {/* X-axis labels (chapter numbers) */}
        {points.map((p) => (
          <text
            key={`x-${p.chapter}`}
            x={p.x}
            y={chartHeight - 6}
            textAnchor="middle"
            fontSize="10"
            fill="hsl(var(--muted-foreground))"
          >
            {p.chapter}
          </text>
        ))}

        {/* Y-axis labels */}
        {yTicks
          .filter((t) => t % 2 === 1 || t === maxLevel)
          .map((tick) => (
            <text
              key={`y-${tick}`}
              x={padding.left - 6}
              y={scaleY(tick) + 3.5}
              textAnchor="end"
              fontSize="10"
              fill="hsl(var(--muted-foreground))"
            >
              {tick}
            </text>
          ))}

        {/* Axis titles */}
        <text
          x={padding.left + plotW / 2}
          y={chartHeight - 0}
          textAnchor="middle"
          fontSize="10"
          fill="hsl(var(--muted-foreground))"
        >
          章节
        </text>
        <text
          x={8}
          y={padding.top + plotH / 2}
          textAnchor="middle"
          fontSize="10"
          fill="hsl(var(--muted-foreground))"
          transform={`rotate(-90, 8, ${padding.top + plotH / 2})`}
        >
          能力等级
        </text>
      </svg>
    </ScrollArea>
  );
};

// ---------------------------------------------------------------------------
// Severity styles for inconsistency alerts
// ---------------------------------------------------------------------------

const SEVERITY_STYLES: Record<
  string,
  { icon: typeof AlertTriangle; color: string; bg: string }
> = {
  error: {
    icon: XCircle,
    color: 'text-red-500',
    bg: 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800',
  },
  warning: {
    icon: AlertTriangle,
    color: 'text-yellow-500',
    bg: 'bg-yellow-50 dark:bg-yellow-950/20 border-yellow-200 dark:border-yellow-800',
  },
  info: {
    icon: Info,
    color: 'text-blue-500',
    bg: 'bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800',
  },
};

// ---------------------------------------------------------------------------
// Emotional state color helper
// ---------------------------------------------------------------------------

const EMOTIONAL_COLORS: Record<string, string> = {
  积极: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  消极: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  中性: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
};

function getEmotionalColor(state: string): string {
  if (state.includes('积极') || state.includes('正面') || state.includes('乐观'))
    return EMOTIONAL_COLORS['积极'];
  if (state.includes('消极') || state.includes('负面') || state.includes('悲观'))
    return EMOTIONAL_COLORS['消极'];
  return EMOTIONAL_COLORS['中性'];
}

// ---------------------------------------------------------------------------
// Main CharacterArc component
// ---------------------------------------------------------------------------

export function CharacterArc() {
  const { currentNovel } = useNovelStore();
  const { characters } = useCharacterStore();
  const { arcPoints, setArcPoints } = useCharacterArcStore();

  const [selectedCharacterId, setSelectedCharacterId] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [growthData, setGrowthData] = useState<GrowthDataPoint[]>([]);
  const [inconsistencies, setInconsistencies] = useState<ArcInconsistency[]>([]);
  const [isChecking, setIsChecking] = useState(false);
  const [highlightedChapter, setHighlightedChapter] = useState<number | null>(null);

  // -----------------------------------------------------------------------
  // Load arc points
  // -----------------------------------------------------------------------
  const loadArcPoints = useCallback(
    async (characterId: string) => {
      if (!currentNovel || !characterId) return;
      setIsLoading(true);
      try {
        const res = await fetch(
          `${API_URL}/arcs/?novel_id=${currentNovel.id}&character_id=${characterId}`
        );
        if (res.ok) {
          const data: CharacterArcPoint[] = await res.json();
          setArcPoints(data);
        }
      } catch (e) {
        console.error('加载弧线数据失败:', e);
      } finally {
        setIsLoading(false);
      }
    },
    [currentNovel, setArcPoints]
  );

  // -----------------------------------------------------------------------
  // Load growth curve
  // -----------------------------------------------------------------------
  const loadGrowthCurve = useCallback(async (characterId: string) => {
    if (!characterId) return;
    try {
      const res = await fetch(`${API_URL}/arcs/growth-curve?character_id=${characterId}`);
      if (res.ok) {
        const data = await res.json();
        // Expect {chapter: level} pairs
        const points: GrowthDataPoint[] = Object.entries(data).map(([ch, lv]) => ({
          chapter: Number(ch),
          level: Number(lv),
        }));
        setGrowthData(points);
      }
    } catch (e) {
      console.error('加载成长曲线失败:', e);
    }
  }, []);

  // -----------------------------------------------------------------------
  // React to character selection
  // -----------------------------------------------------------------------
  useEffect(() => {
    if (selectedCharacterId) {
      loadArcPoints(selectedCharacterId);
      loadGrowthCurve(selectedCharacterId);
      setInconsistencies([]);
      setHighlightedChapter(null);
    } else {
      setArcPoints([]);
      setGrowthData([]);
      setInconsistencies([]);
    }
  }, [selectedCharacterId, loadArcPoints, loadGrowthCurve, setArcPoints]);

  // -----------------------------------------------------------------------
  // AI extract
  // -----------------------------------------------------------------------
  const handleExtract = async () => {
    if (!currentNovel || !selectedCharacterId) {
      toast.error('请先选择人物');
      return;
    }
    setIsExtracting(true);
    try {
      const res = await fetch(
        `${API_URL}/arcs/extract?novel_id=${currentNovel.id}&character_id=${selectedCharacterId}`,
        { method: 'POST' }
      );
      const data = await res.json();
      if (data.success !== false) {
        await loadArcPoints(selectedCharacterId);
        await loadGrowthCurve(selectedCharacterId);
        toast.success('弧线分析完成');
      } else {
        toast.error(data.error || 'AI分析失败');
      }
    } catch (e) {
      toast.error('AI分析请求失败');
    } finally {
      setIsExtracting(false);
    }
  };

  // -----------------------------------------------------------------------
  // Detect inconsistencies
  // -----------------------------------------------------------------------
  const handleCheckInconsistencies = async () => {
    if (!currentNovel || !selectedCharacterId) {
      toast.error('请先选择人物');
      return;
    }
    setIsChecking(true);
    setInconsistencies([]);
    try {
      const res = await fetch(
        `${API_URL}/arcs/inconsistencies?novel_id=${currentNovel.id}&character_id=${selectedCharacterId}`,
        { method: 'POST' }
      );
      const data = await res.json();
      setInconsistencies(data.inconsistencies || data || []);
      toast.success(`检测完成，发现 ${(data.inconsistencies || data || []).length} 个不一致`);
    } catch (e) {
      toast.error('不一致检测失败');
    } finally {
      setIsChecking(false);
    }
  };

  // -----------------------------------------------------------------------
  // Derived state
  // -----------------------------------------------------------------------
  const sortedArcPoints = [...arcPoints].sort((a, b) => a.chapterNumber - b.chapterNumber);

  // Scroll highlighted card into view
  useEffect(() => {
    if (highlightedChapter != null) {
      const el = document.getElementById(`arc-card-ch-${highlightedChapter}`);
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [highlightedChapter]);

  // -----------------------------------------------------------------------
  // Guard: no novel selected
  // -----------------------------------------------------------------------
  if (!currentNovel) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        请先选择一部小说
      </div>
    );
  }

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  return (
    <div className="flex h-full flex-col">
      {/* ---- Top Bar ---- */}
      <div className="flex items-center gap-3 border-b px-4 py-3">
        <Select value={selectedCharacterId} onValueChange={setSelectedCharacterId}>
          <SelectTrigger className="w-52 h-9">
            <SelectValue placeholder="选择人物" />
          </SelectTrigger>
          <SelectContent>
            {characters.map((c) => (
              <SelectItem key={c.id} value={c.id}>
                {c.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Button
          size="sm"
          className="h-9"
          onClick={handleExtract}
          disabled={!selectedCharacterId || isExtracting}
        >
          {isExtracting ? (
            <Loader2 className="h-4 w-4 mr-1 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4 mr-1" />
          )}
          AI 分析
        </Button>
      </div>

      {/* ---- Two-panel body ---- */}
      <div className="flex flex-1 overflow-hidden">
        {/* ---- Left Panel: Timeline ---- */}
        <div className="w-96 border-r flex flex-col">
          <ScrollArea className="flex-1">
            <div className="p-3 space-y-2">
              {isLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-5 w-5 animate-spin mr-2" />
                  <span className="text-sm text-muted-foreground">加载中...</span>
                </div>
              ) : sortedArcPoints.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                  <TrendingUp className="h-10 w-10 mb-2 opacity-30" />
                  <p className="text-sm">
                    {selectedCharacterId ? '暂无弧线数据，点击「AI 分析」' : '请先选择人物'}
                  </p>
                </div>
              ) : (
                sortedArcPoints.map((point) => {
                  const isHighlighted = highlightedChapter === point.chapterNumber;
                  return (
                    <Card
                      key={point.id}
                      id={`arc-card-ch-${point.chapterNumber}`}
                      className={`transition-all ${
                        isHighlighted
                          ? 'ring-2 ring-primary shadow-md'
                          : 'hover:shadow-sm'
                      }`}
                    >
                      <CardContent className="p-3 space-y-2">
                        {/* Chapter badge */}
                        <div className="flex items-center gap-2">
                          <Badge
                            variant="secondary"
                            className="bg-primary/10 text-primary font-medium"
                          >
                            第 {point.chapterNumber} 章
                          </Badge>
                          {point.source === 'ai' && (
                            <Badge variant="outline" className="text-xs">
                              AI
                            </Badge>
                          )}
                        </div>

                        {/* Psychological state */}
                        {point.psychologicalState && (
                          <div className="flex items-start gap-1.5 text-sm">
                            <Brain className="h-4 w-4 mt-0.5 shrink-0 text-muted-foreground" />
                            <span className="text-muted-foreground">
                              {point.psychologicalState}
                            </span>
                          </div>
                        )}

                        {/* Emotional state */}
                        {point.emotionalState && (
                          <div>
                            <Badge
                              variant="secondary"
                              className={`text-xs ${getEmotionalColor(point.emotionalState)}`}
                            >
                              <Heart className="h-3 w-3 mr-1" />
                              {point.emotionalState}
                            </Badge>
                          </div>
                        )}

                        {/* Ability description */}
                        {point.abilityDescription && (
                          <div className="flex items-start gap-1.5 text-sm">
                            <Zap className="h-4 w-4 mt-0.5 shrink-0 text-muted-foreground" />
                            <span className="text-muted-foreground">
                              {point.abilityDescription}
                            </span>
                          </div>
                        )}

                        {/* Key events */}
                        {point.keyEvents.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {point.keyEvents.map((evt, idx) => (
                              <Badge
                                key={idx}
                                variant="outline"
                                className="text-xs font-normal"
                              >
                                {evt}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  );
                })
              )}
            </div>
          </ScrollArea>
        </div>

        {/* ---- Right Panel: Chart + Inconsistencies ---- */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Growth curve chart */}
          <div className="border-b p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold flex items-center gap-1.5">
                <TrendingUp className="h-4 w-4" />
                成长曲线
              </h3>
              {selectedCharacterId && (
                <span className="text-xs text-muted-foreground">
                  {growthData.length} 个数据点
                </span>
              )}
            </div>
            {selectedCharacterId ? (
              <GrowthChart
                data={growthData}
                highlightedChapter={highlightedChapter}
                onPointClick={(chapter) =>
                  setHighlightedChapter((prev) => (prev === chapter ? null : chapter))
                }
              />
            ) : (
              <div className="flex items-center justify-center h-[200px] text-muted-foreground text-sm">
                选择人物后查看成长曲线
              </div>
            )}
          </div>

          {/* Inconsistency section */}
          <div className="flex-1 overflow-auto p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold flex items-center gap-1.5">
                <AlertTriangle className="h-4 w-4" />
                不一致检测
              </h3>
              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs"
                onClick={handleCheckInconsistencies}
                disabled={!selectedCharacterId || isChecking}
              >
                {isChecking ? (
                  <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                ) : (
                  <AlertTriangle className="h-3 w-3 mr-1" />
                )}
                检测不一致
              </Button>
            </div>

            {isChecking ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-5 w-5 animate-spin mr-2" />
                <span className="text-sm text-muted-foreground">正在检测...</span>
              </div>
            ) : inconsistencies.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground text-sm">
                {selectedCharacterId ? (
                  <>
                    <Info className="h-8 w-8 mx-auto mb-2 opacity-30" />
                    <p>点击「检测不一致」分析角色弧线中的矛盾</p>
                  </>
                ) : (
                  '选择人物后进行检测'
                )}
              </div>
            ) : (
              <div className="space-y-2">
                {inconsistencies.map((issue, idx) => {
                  const style = SEVERITY_STYLES[issue.severity] || SEVERITY_STYLES.info;
                  const IconComp = style.icon;
                  return (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg border ${style.bg}`}
                    >
                      <div className="flex items-center gap-2">
                        <IconComp className={`h-4 w-4 shrink-0 ${style.color}`} />
                        <span className="text-sm font-medium">
                          第{issue.fromChapter}章
                          <ChevronRight className="h-3 w-3 inline mx-0.5" />
                          第{issue.toChapter}章
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1 ml-6">
                        {issue.description}
                      </p>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
