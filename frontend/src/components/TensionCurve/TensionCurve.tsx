'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useNovelStore, useTensionStore } from '@/stores';
import { API_URL } from '@/lib/constants';
import type { TensionPoint, PacingIssue } from '@/types';
import { Activity, AlertTriangle, TrendingUp, Zap, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

// --- Constants ---

const CHART_HEIGHT = 300;
const PADDING = { top: 20, right: 30, bottom: 60, left: 50 };
const Y_MIN = 1;
const Y_MAX = 10;
const Y_STEP = 1;

const TENSION_COLORS: Record<string, string> = {
  red: '#ef4444',
  orange: '#f97316',
  yellow: '#eab308',
  green: '#22c55e',
};

function getTensionColor(level: number): string {
  if (level >= 8) return TENSION_COLORS.red;
  if (level >= 6) return TENSION_COLORS.orange;
  if (level >= 4) return TENSION_COLORS.yellow;
  return TENSION_COLORS.green;
}

const EMOTION_TAG_STYLES: Record<string, { color: string; bg: string }> = {
  '紧张': { color: '#dc2626', bg: '#fef2f2' },
  '温馨': { color: '#db2777', bg: '#fdf2f8' },
  '悲伤': { color: '#2563eb', bg: '#eff6ff' },
  '欢乐': { color: '#d97706', bg: '#fffbeb' },
  '愤怒': { color: '#ea580c', bg: '#fff7ed' },
  '平静': { color: '#16a34a', bg: '#f0fdf4' },
  '恐惧': { color: '#7c3aed', bg: '#f5f3ff' },
  '惊讶': { color: '#0891b2', bg: '#ecfeff' },
  '绝望': { color: '#4b5563', bg: '#f9fafb' },
  '希望': { color: '#eab308', bg: '#fefce8' },
};

function getEmotionStyle(tag: string): { color: string; bg: string } {
  return EMOTION_TAG_STYLES[tag] || { color: '#6b7280', bg: '#f3f4f6' };
}

// --- Component ---

export function TensionCurve() {
  const { currentNovel } = useNovelStore();
  const { tensionPoints, setTensionPoints } = useTensionStore();

  const [isLoading, setIsLoading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [selectedChapter, setSelectedChapter] = useState<number | null>(null);
  const [pacingIssues, setPacingIssues] = useState<PacingIssue[]>([]);
  const [isDetectingIssues, setIsDetectingIssues] = useState(false);
  const [cliffhangerSuggestion, setCliffhangerSuggestion] = useState<string | null>(null);
  const [isGeneratingCliffhanger, setIsGeneratingCliffhanger] = useState(false);
  const [showCliffhangerSuggestion, setShowCliffhangerSuggestion] = useState(false);

  // Sorted tension points by chapter
  const sortedPoints = useMemo(
    () => [...tensionPoints].sort((a, b) => a.chapterNumber - b.chapterNumber),
    [tensionPoints]
  );

  const chapterCount = sortedPoints.length;

  // Selected tension point detail
  const selectedPoint = useMemo(
    () => (selectedChapter !== null ? sortedPoints.find((p) => p.chapterNumber === selectedChapter) : null),
    [sortedPoints, selectedChapter]
  );

  // --- Alert badge detection ---

  const alerts = useMemo(() => {
    if (sortedPoints.length === 0) return { lowStreak: false, weakOpening: false, noCliffhanger: false };

    // Low tension streak: 5+ consecutive chapters with tension < 4
    let maxLowStreak = 0;
    let currentStreak = 0;
    for (const p of sortedPoints) {
      if (p.tensionLevel < 4) {
        currentStreak++;
        maxLowStreak = Math.max(maxLowStreak, currentStreak);
      } else {
        currentStreak = 0;
      }
    }
    const lowStreak = maxLowStreak >= 5;

    // Weak opening: golden 3 chapters average tension < 4
    const goldenChapters = sortedPoints.slice(0, 3);
    const weakOpening =
      goldenChapters.length >= 2 &&
      goldenChapters.reduce((sum, p) => sum + p.tensionLevel, 0) / goldenChapters.length < 4;

    // No cliffhanger: chapters with cliffhangerScore < 4 or null
    const chaptersWithoutCliffhanger = sortedPoints.filter(
      (p) => p.cliffhangerScore === null || p.cliffhangerScore < 4
    );
    const noCliffhanger = chaptersWithoutCliffhanger.length >= Math.ceil(sortedPoints.length * 0.6);

    return { lowStreak, weakOpening, noCliffhanger };
  }, [sortedPoints]);

  // --- API calls ---

  const fetchTensionPoints = useCallback(async () => {
    if (!currentNovel) return;
    setIsLoading(true);
    try {
      const res = await fetch(`${API_URL}/tension/?novel_id=${currentNovel.id}`);
      if (res.ok) {
        const data = await res.json();
        setTensionPoints(Array.isArray(data) ? data : data?.data ?? []);
      }
    } catch (e) {
      console.error('加载节奏张力数据失败:', e);
    } finally {
      setIsLoading(false);
    }
  }, [currentNovel, setTensionPoints]);

  const handleAnalyze = useCallback(async () => {
    if (!currentNovel) return;
    setIsAnalyzing(true);
    try {
      const res = await fetch(`${API_URL}/tension/analyze?novel_id=${currentNovel.id}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        const points: TensionPoint[] = Array.isArray(data) ? data : data?.data ?? [];
        setTensionPoints(points);
        toast.success(`AI 分析完成，共 ${points.length} 个章节`);
      } else {
        toast.error('AI 分析失败');
      }
    } catch (e) {
      console.error('AI 分析失败:', e);
      toast.error('AI 分析失败，请检查后端服务');
    } finally {
      setIsAnalyzing(false);
    }
  }, [currentNovel, setTensionPoints]);

  const handleDetectIssues = useCallback(async () => {
    if (!currentNovel) return;
    setIsDetectingIssues(true);
    try {
      const res = await fetch(`${API_URL}/tension/pacing-issues?novel_id=${currentNovel.id}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        const issues: PacingIssue[] = Array.isArray(data) ? data : data?.data ?? [];
        setPacingIssues(issues);
        toast.success(`检测到 ${issues.length} 个节奏问题`);
      } else {
        toast.error('节奏问题检测失败');
      }
    } catch (e) {
      console.error('节奏问题检测失败:', e);
      toast.error('节奏问题检测失败');
    } finally {
      setIsDetectingIssues(false);
    }
  }, [currentNovel]);

  const handleGenerateCliffhanger = useCallback(async () => {
    if (!currentNovel || selectedChapter === null) return;
    setIsGeneratingCliffhanger(true);
    setShowCliffhangerSuggestion(false);
    try {
      const res = await fetch(
        `${API_URL}/tension/${selectedChapter}/cliffhanger?novel_id=${currentNovel.id}`,
        { method: 'POST' }
      );
      if (res.ok) {
        const data = await res.json();
        const suggestion = typeof data === 'string' ? data : data?.suggestion ?? data?.data ?? '暂无建议';
        setCliffhangerSuggestion(suggestion);
        setShowCliffhangerSuggestion(true);
        toast.success('已生成断章建议');
      } else {
        toast.error('生成断章建议失败');
      }
    } catch (e) {
      console.error('生成断章建议失败:', e);
      toast.error('生成断章建议失败');
    } finally {
      setIsGeneratingCliffhanger(false);
    }
  }, [currentNovel, selectedChapter]);

  // --- Load data on novel change ---

  useEffect(() => {
    if (currentNovel) {
      fetchTensionPoints();
      setSelectedChapter(null);
      setPacingIssues([]);
      setCliffhangerSuggestion(null);
    }
  }, [currentNovel, fetchTensionPoints]);

  // --- SVG chart calculations ---

  const chartWidth = useMemo(() => {
    if (chapterCount <= 1) return 600;
    return Math.max(600, chapterCount * 60);
  }, [chapterCount]);

  const plotWidth = chartWidth - PADDING.left - PADDING.right;
  const plotHeight = CHART_HEIGHT - PADDING.top - PADDING.bottom;

  const getX = useCallback(
    (index: number) => {
      if (chapterCount <= 1) return PADDING.left + plotWidth / 2;
      return PADDING.left + (index / (chapterCount - 1)) * plotWidth;
    },
    [chapterCount, plotWidth]
  );

  const getY = useCallback(
    (tensionLevel: number) => {
      const clamped = Math.max(Y_MIN, Math.min(Y_MAX, tensionLevel));
      return PADDING.top + plotHeight - ((clamped - Y_MIN) / (Y_MAX - Y_MIN)) * plotHeight;
    },
    [plotHeight]
  );

  // Polyline points string
  const polylinePoints = useMemo(
    () => sortedPoints.map((p, i) => `${getX(i)},${getY(p.tensionLevel)}`).join(' '),
    [sortedPoints, getX, getY]
  );

  // Area fill polygon (closed under the line)
  const areaPoints = useMemo(() => {
    if (sortedPoints.length === 0) return '';
    const bottomY = PADDING.top + plotHeight;
    const topPoints = sortedPoints.map((p, i) => `${getX(i)},${getY(p.tensionLevel)}`).join(' ');
    const lastX = getX(sortedPoints.length - 1);
    const firstX = getX(0);
    return `${firstX},${bottomY} ${topPoints} ${lastX},${bottomY}`;
  }, [sortedPoints, getX, getY, plotHeight]);

  // Y-axis gridlines
  const yGridLines = useMemo(() => {
    const lines = [];
    for (let v = Y_MIN; v <= Y_MAX; v += Y_STEP) {
      lines.push({ value: v, y: getY(v) });
    }
    return lines;
  }, [getY]);

  // X-axis labels (show every Nth to avoid overlap)
  const xLabelInterval = useMemo(() => {
    if (chapterCount <= 15) return 1;
    if (chapterCount <= 30) return 2;
    if (chapterCount <= 60) return 5;
    return 10;
  }, [chapterCount]);

  // Cliffhanger triangles
  const cliffhangerTriangles = useMemo(
    () =>
      sortedPoints
        .filter((p) => p.cliffhangerScore !== null)
        .map((p, i) => {
          const x = getX(i);
          const baseY = PADDING.top + plotHeight;
          const h = (p.cliffhangerScore as number) * 5;
          const color =
            (p.cliffhangerScore as number) >= 7
              ? '#22c55e'
              : (p.cliffhangerScore as number) >= 4
                ? '#eab308'
                : '#ef4444';
          return { x, baseY, h, color, chapter: p.chapterNumber };
        }),
    [sortedPoints, getX, plotHeight]
  );

  // --- Render ---

  if (!currentNovel) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <div className="text-center space-y-2">
          <Activity className="h-12 w-12 mx-auto opacity-30" />
          <p className="text-sm">请先选择一部小说</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      {/* Top Bar */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Activity className="h-5 w-5" />
            节奏张力
          </h2>
          <Button onClick={handleAnalyze} disabled={isAnalyzing || isLoading} size="sm">
            {isAnalyzing ? (
              <>
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                分析中...
              </>
            ) : (
              <>
                <Zap className="h-4 w-4 mr-1" />
                AI 分析
              </>
            )}
          </Button>
        </div>

        {/* Alert badges */}
        <div className="flex items-center gap-2 flex-wrap">
          {alerts.lowStreak && (
            <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/30 dark:text-amber-400 dark:border-amber-800">
              <AlertTriangle className="h-3 w-3 mr-1" />
              低张力连胜
            </Badge>
          )}
          {alerts.weakOpening && (
            <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200 dark:bg-red-950/30 dark:text-red-400 dark:border-red-800">
              <AlertTriangle className="h-3 w-3 mr-1" />
              开局薄弱
            </Badge>
          )}
          {alerts.noCliffhanger && (
            <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-950/30 dark:text-orange-400 dark:border-orange-800">
              <AlertTriangle className="h-3 w-3 mr-1" />
              缺少悬念
            </Badge>
          )}
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <Card>
          <CardContent className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <span className="ml-3 text-muted-foreground">加载节奏张力数据...</span>
          </CardContent>
        </Card>
      )}

      {/* Empty state */}
      {!isLoading && sortedPoints.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <TrendingUp className="h-12 w-12 mb-3 opacity-30" />
            <p className="text-sm mb-3">暂无节奏张力数据</p>
            <Button onClick={handleAnalyze} disabled={isAnalyzing} size="sm">
              <Zap className="h-4 w-4 mr-1" />
              AI 分析章节张力
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Main Chart */}
      {!isLoading && sortedPoints.length > 0 && (
        <>
          <Card>
            <CardContent className="p-4">
              <ScrollArea className="w-full">
                <svg
                  width={chartWidth}
                  height={CHART_HEIGHT}
                  viewBox={`0 0 ${chartWidth} ${CHART_HEIGHT}`}
                  className="block"
                >
                  <defs>
                    {/* Area fill gradient */}
                    <linearGradient id="tensionAreaGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.15" />
                      <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0.01" />
                    </linearGradient>
                    {/* Line gradient */}
                    <linearGradient id="tensionLineGradient" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="#3b82f6" />
                      <stop offset="50%" stopColor="#f97316" />
                      <stop offset="100%" stopColor="#ef4444" />
                    </linearGradient>
                  </defs>

                  {/* Y-axis gridlines */}
                  {yGridLines.map(({ value, y }) => (
                    <g key={`grid-${value}`}>
                      <line
                        x1={PADDING.left}
                        y1={y}
                        x2={chartWidth - PADDING.right}
                        y2={y}
                        stroke="currentColor"
                        strokeOpacity="0.08"
                        strokeDasharray="4 4"
                      />
                      <text
                        x={PADDING.left - 8}
                        y={y}
                        textAnchor="end"
                        dominantBaseline="middle"
                        className="fill-muted-foreground text-[10px]"
                      >
                        {value}
                      </text>
                    </g>
                  ))}

                  {/* Y-axis label */}
                  <text
                    x={12}
                    y={PADDING.top + plotHeight / 2}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    className="fill-muted-foreground text-[10px]"
                    transform={`rotate(-90, 12, ${PADDING.top + plotHeight / 2})`}
                  >
                    张力等级
                  </text>

                  {/* Area fill */}
                  {areaPoints && (
                    <polygon points={areaPoints} fill="url(#tensionAreaGradient)" />
                  )}

                  {/* Tension line */}
                  {sortedPoints.length > 1 && (
                    <polyline
                      points={polylinePoints}
                      fill="none"
                      stroke="url(#tensionLineGradient)"
                      strokeWidth={2.5}
                      strokeLinejoin="round"
                      strokeLinecap="round"
                    />
                  )}

                  {/* Cliffhanger score triangles */}
                  {cliffhangerTriangles.map(({ x, baseY, h, color, chapter }) => (
                    <polygon
                      key={`cliff-${chapter}`}
                      points={`${x - 4},${baseY} ${x + 4},${baseY} ${x},${baseY - h}`}
                      fill={color}
                      opacity={0.7}
                    />
                  ))}

                  {/* Data point circles */}
                  {sortedPoints.map((point, i) => {
                    const cx = getX(i);
                    const cy = getY(point.tensionLevel);
                    const color = getTensionColor(point.tensionLevel);
                    const isSelected = selectedChapter === point.chapterNumber;

                    return (
                      <g
                        key={point.id}
                        className="cursor-pointer"
                        onClick={() =>
                          setSelectedChapter(
                            selectedChapter === point.chapterNumber ? null : point.chapterNumber
                          )
                        }
                      >
                        {/* Selection ring */}
                        {isSelected && (
                          <circle cx={cx} cy={cy} r={12} fill={color} opacity={0.15} />
                        )}
                        {/* Main circle */}
                        <circle
                          cx={cx}
                          cy={cy}
                          r={isSelected ? 7 : 5}
                          fill={color}
                          stroke="white"
                          strokeWidth={2}
                          className="transition-all duration-150"
                        />
                        {/* Hover target (larger invisible circle for easier clicking) */}
                        <circle cx={cx} cy={cy} r={14} fill="transparent" />
                      </g>
                    );
                  })}

                  {/* X-axis labels */}
                  {sortedPoints.map((point, i) => {
                    if (i % xLabelInterval !== 0 && i !== sortedPoints.length - 1) return null;
                    const cx = getX(i);
                    return (
                      <text
                        key={`xlabel-${point.chapterNumber}`}
                        x={cx}
                        y={CHART_HEIGHT - PADDING.bottom + 18}
                        textAnchor="middle"
                        className="fill-muted-foreground text-[10px]"
                      >
                        第{point.chapterNumber}章
                      </text>
                    );
                  })}

                  {/* Baseline */}
                  <line
                    x1={PADDING.left}
                    y1={PADDING.top + plotHeight}
                    x2={chartWidth - PADDING.right}
                    y2={PADDING.top + plotHeight}
                    stroke="currentColor"
                    strokeOpacity="0.15"
                  />
                </svg>
              </ScrollArea>

              {/* Emotion Tags Bar */}
              <div className="mt-3 border-t pt-3">
                <div className="text-xs text-muted-foreground mb-2">情感标签</div>
                <ScrollArea className="w-full">
                  <div
                    style={{ width: chartWidth - PADDING.left - PADDING.right, marginLeft: PADDING.left }}
                  >
                    <div className="flex">
                      {sortedPoints.map((point) => (
                        <div
                          key={`emotion-${point.id}`}
                          className="flex-shrink-0 flex flex-col items-center gap-0.5"
                          style={{ width: chapterCount <= 1 ? plotWidth : plotWidth / (chapterCount - 1) }}
                        >
                          {point.emotionTags.map((tag) => {
                            const style = getEmotionStyle(tag);
                            return (
                              <span
                                key={tag}
                                className="text-[9px] leading-tight px-1 py-px rounded whitespace-nowrap"
                                style={{ color: style.color, backgroundColor: style.bg }}
                              >
                                {tag}
                              </span>
                            );
                          })}
                        </div>
                      ))}
                    </div>
                  </div>
                </ScrollArea>
              </div>

              {/* Tension legend */}
              <div className="mt-3 flex items-center gap-4 text-[10px] text-muted-foreground">
                <span className="flex items-center gap-1">
                  <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ backgroundColor: TENSION_COLORS.red }} />
                  高 (8-10)
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ backgroundColor: TENSION_COLORS.orange }} />
                  中高 (6-7)
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ backgroundColor: TENSION_COLORS.yellow }} />
                  中 (4-5)
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ backgroundColor: TENSION_COLORS.green }} />
                  低 (1-3)
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Detail Panel */}
          {selectedPoint && (
            <Card>
              <CardHeader className="py-3 px-4 flex-row items-center justify-between space-y-0">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Activity className="h-4 w-4" />
                  第 {selectedPoint.chapterNumber} 章
                  <Badge
                    variant="outline"
                    style={{
                      color: getTensionColor(selectedPoint.tensionLevel),
                      borderColor: getTensionColor(selectedPoint.tensionLevel),
                    }}
                  >
                    张力 {selectedPoint.tensionLevel}/10
                  </Badge>
                </CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0"
                  onClick={() => setSelectedChapter(null)}
                >
                  &times;
                </Button>
              </CardHeader>
              <CardContent className="px-4 pb-4 space-y-3">
                {/* Key events summary */}
                {selectedPoint.keyEventsSummary && (
                  <div>
                    <div className="text-xs font-medium text-muted-foreground mb-1">关键事件</div>
                    <p className="text-sm leading-relaxed">{selectedPoint.keyEventsSummary}</p>
                  </div>
                )}

                {/* Emotion tags */}
                {selectedPoint.emotionTags.length > 0 && (
                  <div>
                    <div className="text-xs font-medium text-muted-foreground mb-1">情感标签</div>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedPoint.emotionTags.map((tag) => {
                        const style = getEmotionStyle(tag);
                        return (
                          <Badge
                            key={tag}
                            variant="outline"
                            className="text-xs"
                            style={{ color: style.color, borderColor: style.bg, backgroundColor: style.bg }}
                          >
                            {tag}
                          </Badge>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Pacing note */}
                {selectedPoint.pacingNote && (
                  <div>
                    <div className="text-xs font-medium text-muted-foreground mb-1">节奏备注</div>
                    <p className="text-sm leading-relaxed text-muted-foreground">{selectedPoint.pacingNote}</p>
                  </div>
                )}

                {/* Reader hook & cliffhanger scores */}
                <div className="grid grid-cols-2 gap-3">
                  {/* Reader hook score */}
                  {selectedPoint.readerHookScore !== null && (
                    <div className="rounded-lg border p-3">
                      <div className="text-xs text-muted-foreground mb-1">读者吸引力</div>
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-bold">{selectedPoint.readerHookScore}</span>
                        <span className="text-xs text-muted-foreground">/10</span>
                      </div>
                      <div className="mt-1.5 h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${selectedPoint.readerHookScore * 10}%`,
                            backgroundColor: getTensionColor(selectedPoint.readerHookScore),
                          }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Cliffhanger score */}
                  {selectedPoint.cliffhangerScore !== null && (
                    <div className="rounded-lg border p-3">
                      <div className="text-xs text-muted-foreground mb-1">悬念分数</div>
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-bold">{selectedPoint.cliffhangerScore}</span>
                        <span className="text-xs text-muted-foreground">/10</span>
                      </div>
                      <div className="mt-1.5 h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${selectedPoint.cliffhangerScore * 10}%`,
                            backgroundColor:
                              selectedPoint.cliffhangerScore >= 7
                                ? '#22c55e'
                                : selectedPoint.cliffhangerScore >= 4
                                  ? '#eab308'
                                  : '#ef4444',
                          }}
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Cliffhanger suggestion button */}
                <div className="space-y-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleGenerateCliffhanger}
                    disabled={isGeneratingCliffhanger}
                    className="w-full"
                  >
                    {isGeneratingCliffhanger ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                        生成中...
                      </>
                    ) : (
                      <>
                        <Zap className="h-4 w-4 mr-1" />
                        建议改进断章
                      </>
                    )}
                  </Button>

                  {/* Cliffhanger suggestion result */}
                  {showCliffhangerSuggestion && cliffhangerSuggestion && (
                    <div className="rounded-lg border bg-muted/30 p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-muted-foreground">AI 断章建议</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-5 w-5 p-0"
                          onClick={() => setShowCliffhangerSuggestion(false)}
                        >
                          &times;
                        </Button>
                      </div>
                      <p className="text-sm leading-relaxed">{cliffhangerSuggestion}</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Pacing Issues */}
      <Card>
        <CardHeader className="py-3 px-4 flex-row items-center justify-between space-y-0">
          <CardTitle className="text-sm flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            节奏问题检测
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDetectIssues}
            disabled={isDetectingIssues || !currentNovel}
          >
            {isDetectingIssues ? (
              <>
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                检测中...
              </>
            ) : (
              <>
                <AlertTriangle className="h-4 w-4 mr-1" />
                检测节奏问题
              </>
            )}
          </Button>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          {pacingIssues.length === 0 ? (
            <div className="text-center text-sm text-muted-foreground py-6">
              {isDetectingIssues ? '正在检测...' : '点击"检测节奏问题"开始分析'}
            </div>
          ) : (
            <ScrollArea className="max-h-72">
              <div className="space-y-3">
                {pacingIssues.map((issue, i) => {
                  const severityColor =
                    issue.issueType.includes('低张力') || issue.issueType.includes('拖沓')
                      ? 'border-l-amber-500'
                      : issue.issueType.includes('薄弱') || issue.issueType.includes('缺失')
                        ? 'border-l-red-500'
                        : 'border-l-orange-500';

                  return (
                    <div
                      key={`issue-${i}`}
                      className={`rounded-lg border border-l-4 p-3 space-y-2 ${severityColor}`}
                    >
                      <div className="flex items-center justify-between">
                        <Badge variant="outline" className="text-xs">
                          {issue.issueType}
                        </Badge>
                        <span className="text-[10px] text-muted-foreground">
                          第 {issue.chapters.join(', ')} 章
                        </span>
                      </div>
                      <p className="text-sm">{issue.description}</p>
                      {issue.suggestion && (
                        <div className="text-xs text-muted-foreground bg-muted/30 rounded p-2">
                          <span className="font-medium">建议：</span>
                          {issue.suggestion}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
