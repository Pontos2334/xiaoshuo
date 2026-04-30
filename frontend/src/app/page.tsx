'use client';

import { useState, useEffect, useCallback, useRef, lazy, Suspense } from 'react';
import { XCircle } from 'lucide-react';
import { toast } from 'sonner';
import { MainLayout } from '@/components/Layout/MainLayout';
import { CharacterGraph } from '@/components/CharacterGraph/CharacterGraph';
import { PlotGraph } from '@/components/PlotGraph/PlotGraph';
import { InspirationPanel } from '@/components/InspirationPanel/InspirationPanel';
import LoadingFallback from '@/components/LoadingFallback';

const VectorSearch = lazy(() => import('@/components/VectorSearch/VectorSearch').then(m => ({ default: m.VectorSearch })));
const KnowledgeGraph = lazy(() => import('@/components/KnowledgeGraph/KnowledgeGraph').then(m => ({ default: m.KnowledgeGraph })));
const CharacterChat = lazy(() => import('@/components/CharacterChat/CharacterChat').then(m => ({ default: m.CharacterChat })));
const AIAssistant = lazy(() => import('@/components/AIAssistant/AIAssistant').then(m => ({ default: m.AIAssistant })));
const WorldBuildingComp = lazy(() => import('@/components/WorldBuilding/WorldBuilding').then(m => ({ default: m.WorldBuilding })));
const ForeshadowTrackerComp = lazy(() => import('@/components/ForeshadowTracker/ForeshadowTracker').then(m => ({ default: m.ForeshadowTracker })));
const CharacterArcComp = lazy(() => import('@/components/CharacterArc/CharacterArc').then(m => ({ default: m.CharacterArc })));
const TensionCurveComp = lazy(() => import('@/components/TensionCurve/TensionCurve').then(m => ({ default: m.TensionCurve })));
const OutlineWorkflowComp = lazy(() => import('@/components/OutlineWorkflow/OutlineWorkflow').then(m => ({ default: m.OutlineWorkflow })));
const CharacterQuickSearchComp = lazy(() => import('@/components/CharacterQuickSearch/CharacterQuickSearch').then(m => ({ default: m.CharacterQuickSearch })));

import { useUIStore, useCharacterStore, usePlotStore, useInspirationStore, useNovelStore } from '@/stores';
import { API_URL } from '@/lib/constants';
import { fetchWithTimeout } from '@/lib/api';
import { AnalyzeMode } from '@/types';

export default function Home() {
  const { activeTab } = useUIStore();
  const { currentNovel } = useNovelStore();
  const { setCharacters, setRelations } = useCharacterStore();
  const { setPlotNodes, setPlotConnections } = usePlotStore();
  const { addInspiration, setInspirations, clearInspirations } = useInspirationStore();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [isLoadingData, setIsLoadingData] = useState(false);
  const [analyzeMode, setAnalyzeMode] = useState<AnalyzeMode>('incremental');
  const [analysisProgress, setAnalysisProgress] = useState({ percent: 0, current: 0, total: 0, message: '' });
  const abortControllerRef = useRef<AbortController | null>(null);
  const [quickSearchOpen, setQuickSearchOpen] = useState(false);

  // Ctrl+K 快捷键监听
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setQuickSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // 当选择小说时，从后端加载已保存的数据 - 使用 AbortController 防止竞态条件
  useEffect(() => {
    // 清空数据的函数
    const clearData = () => {
      setCharacters([]);
      setRelations([]);
      setPlotNodes([]);
      setPlotConnections([]);
    };

    if (!currentNovel?.id) {
      clearData();
      return;
    }

    const abortController = new AbortController();
    const { signal } = abortController;

    const loadSavedData = async () => {
      setIsLoadingData(true);
      try {
        // 并行加载人物和情节数据
        const [charRes, plotRes] = await Promise.all([
          fetch(`${API_URL}/characters?novel_id=${currentNovel.id}`, { signal }),
          fetch(`${API_URL}/plots?novel_id=${currentNovel.id}`, { signal }),
        ]);

        // 检查是否已取消
        if (signal.aborted) return;

        if (charRes.ok) {
          const charData = await charRes.json();
          setCharacters(charData || []);
        }

        if (plotRes.ok) {
          const plotData = await plotRes.json();
          setPlotNodes(plotData || []);
        }

        // 加载关系数据
        const relRes = await fetch(`${API_URL}/characters/relations?novel_id=${currentNovel.id}`, { signal });
        if (signal.aborted) return;
        if (relRes.ok) {
          const relData = await relRes.json();
          setRelations(relData || []);
        }

        // 加载情节连接
        const connRes = await fetch(`${API_URL}/plots/connections?novel_id=${currentNovel.id}`, { signal });
        if (signal.aborted) return;
        if (connRes.ok) {
          const connData = await connRes.json();
          setPlotConnections(connData || []);
        }

        // 加载灵感历史记录
        clearInspirations();
        const inspRes = await fetch(`${API_URL}/inspiration/history?novel_id=${currentNovel.id}&limit=50`, { signal });
        if (signal.aborted) return;
        if (inspRes.ok) {
          const inspData = await inspRes.json();
          if (Array.isArray(inspData)) {
            inspData.forEach((insp: { id: string; type: string; content: string; createdAt?: string }) => {
              addInspiration({
                id: insp.id,
                type: insp.type as 'scene' | 'plot' | 'continue' | 'character' | 'emotion',
                content: insp.content,
                createdAt: insp.createdAt || new Date().toISOString(),
              });
            });
          }
        }
      } catch (error) {
        // 忽略取消错误
        if ((error as Error).name === 'AbortError') return;
        console.error('加载保存的数据失败:', error);
        toast.error('加载数据失败');
      } finally {
        if (!signal.aborted) {
          setIsLoadingData(false);
        }
      }
    };

    loadSavedData();

    // 清理函数：取消未完成的请求
    return () => {
      abortController.abort();
    };
  }, [currentNovel?.id]); // Zustand setters are stable references, no need to list

  // 取消分析
  const cancelAnalysis = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsAnalyzing(false);
    setAnalysisProgress({ percent: 0, current: 0, total: 0, message: '' });
    toast.info('已取消分析');
  };

  // 通用 SSE 流式分析
  const handleSSEAnalysis = async (endpoint: string, type: 'characters' | 'plots') => {
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsAnalyzing(true);
    setAnalysisProgress({ percent: 0, current: 0, total: 0, message: '正在连接...' });

    try {
      const response = await fetch(`${API_URL}/${endpoint}`, {
        method: 'POST',
        signal: controller.signal,
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: response.statusText }));
        throw new Error(errorData.error || `服务器错误: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('无法读取响应');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            if (data.step === 'progress') {
              setAnalysisProgress({
                percent: data.progress_percent || 0,
                current: data.completed_chunks || 0,
                total: data.total_chunks || 0,
                message: `第 ${data.current_chunk_index || 0} 块 / 共 ${data.total_chunks || 0} 块`,
              });
            } else if (data.step === 'complete') {
              const characters = data.data?.characters || data.data || [];
              if (type === 'characters') {
                setCharacters(characters);
                // 人物分析完成后自动分析关系
                if (characters.length > 0 && currentNovel?.id) {
                  setAnalysisProgress({ percent: 100, current: 0, total: 0, message: '正在分析人物关系...' });
                  try {
                    const relRes = await fetch(`${API_URL}/characters/relations/analyze?novel_id=${currentNovel.id}`, {
                      method: 'POST',
                      signal: controller.signal,
                      headers: { 'Content-Type': 'application/json' },
                    });
                    if (relRes.ok) {
                      const relData = await relRes.json();
                      if (relData.success && relData.data) {
                        setRelations(relData.data);
                        toast.success(`完成！${characters.length} 个人物，${relData.data.length} 个关系`);
                      } else {
                        toast.success(`完成！发现 ${characters.length} 个人物`);
                      }
                    } else {
                      toast.success(`完成！发现 ${characters.length} 个人物`);
                    }
                  } catch {
                    toast.success(`完成！发现 ${characters.length} 个人物`);
                  }
                } else {
                  toast.success(`完成！发现 ${characters.length} 个人物`);
                }
                setAnalysisProgress({ percent: 100, current: 0, total: 0, message: '分析完成！' });
              } else if (type === 'plots') {
                setAnalysisProgress({ percent: 100, current: 0, total: 0, message: '分析完成！' });
                const nodes = data.data?.nodes || data.data || [];
                setPlotNodes(nodes);
                toast.success(`完成！提取 ${nodes.length} 个情节节点`);
              }
            } else if (data.step === 'error') {
              throw new Error(data.message || '分析失败');
            }
          }
        }
      }
    } catch (error) {
      if ((error as Error).name === 'AbortError') return;
      console.error('分析失败:', error);
      const errorMsg = (error as Error).message;
      if (errorMsg.includes('Failed to fetch') || errorMsg.includes('NetworkError')) {
        toast.error('网络连接失败，请检查后端服务是否运行');
      } else {
        toast.error(`分析失败: ${errorMsg}`);
      }
    } finally {
      setIsAnalyzing(false);
      abortControllerRef.current = null;
    }
  };

  // AI分析人物
  const handleAnalyzeCharacters = async (mode?: AnalyzeMode) => {
    const actualMode = mode || analyzeMode;
    if (!currentNovel) {
      toast.error('请先打开文件夹选择小说');
      return;
    }
    await handleSSEAnalysis(
      `characters/analyze/stream?novel_id=${currentNovel.id}&mode=${actualMode}`,
      'characters'
    );
  };

  // AI分析情节
  const handleAnalyzePlots = async (mode?: AnalyzeMode) => {
    const actualMode = mode || analyzeMode;
    if (!currentNovel) {
      toast.error('请先打开文件夹选择小说');
      return;
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsAnalyzing(true);
    setAnalysisProgress({ percent: 0, current: 0, total: 0, message: actualMode === 'incremental' ? '正在增量分析情节...' : '正在全量分析情节...' });

    try {
      setAnalysisProgress({ percent: 0, current: 0, total: 0, message: '正在读取小说内容...' });
      const response = await fetchWithTimeout(
        `${API_URL}/plots/analyze?novel_id=${currentNovel.id}&mode=${actualMode}`,
        { method: 'POST', signal: controller.signal },
        180000
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`服务器错误: ${response.status} - ${errorText}`);
      }

      setAnalysisProgress({ percent: 50, current: 0, total: 0, message: '正在解析情节节点...' });
      const data = await response.json();

      if (data.success) {
        const nodes = data.data?.nodes || data.data || [];
        setPlotNodes(nodes);
        const modeText = actualMode === 'incremental' ? '增量' : '全量';
        setAnalysisProgress({ percent: 80, current: 0, total: 0, message: `${modeText}分析完成！发现 ${nodes.length} 个情节节点` });
        const connResponse = await fetchWithTimeout(
          `${API_URL}/plots/connections/analyze?novel_id=${currentNovel.id}`,
          { method: 'POST', signal: controller.signal },
          120000
        );
        const connData = await connResponse.json();
        if (connData.success) {
          setPlotConnections(connData.data || []);
          toast.success(`完成！${nodes.length} 个情节，${connData.data?.length || 0} 个关联`);
        }
      } else {
        toast.error(`分析失败: ${data.error || '未知错误'}`);
      }
    } catch (error) {
      if ((error as Error).name === 'AbortError') return;
      console.error('分析情节失败:', error);
      const errorMsg = (error as Error).message;
      if (errorMsg.includes('Failed to fetch') || errorMsg.includes('NetworkError')) {
        toast.error('网络连接失败，请检查后端服务是否运行');
      } else {
        toast.error(`分析失败: ${errorMsg}`);
      }
    } finally {
      setIsAnalyzing(false);
      abortControllerRef.current = null;
    }
  };

  // 生成灵感
  const handleGenerateInspiration = async (type: string, targetIds?: string[], context?: string) => {
    setIsAnalyzing(true);
    setStatusMessage('正在生成灵感...');
    try {
      const endpoint = `${API_URL}/inspiration/${type}`;
      const body: Record<string, string | string[] | undefined> = {
        type,
      };
      if (currentNovel?.id) body.novel_id = currentNovel.id;
      if (targetIds && targetIds.length > 0) body.target_ids = targetIds;
      if (context) body.context = context;

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      if (data.success && data.data) {
        // 使用后端返回的 ID 和时间戳
        addInspiration({
          id: data.data.id || Date.now().toString(),
          type: data.data.type || type as 'scene' | 'plot' | 'continue' | 'character' | 'emotion',
          targetId: data.data.targetId || targetIds?.join(','),
          content: data.data.content || data.data,
          createdAt: data.data.createdAt || new Date().toISOString(),
        });
        toast.success('灵感生成成功！');
      } else {
        toast.error(`生成失败: ${data.error || '未知错误'}`);
      }
    } catch (error) {
      console.error('生成灵感失败:', error);
      toast.error(`生成失败: ${(error as Error).message}`);
    } finally {
      setIsAnalyzing(false);
      setTimeout(() => setStatusMessage(''), 3000);
    }
  };

  return (
    <MainLayout>
      {/* 全局状态提示 */}
      {(isAnalyzing || statusMessage) && (
        <div className="fixed top-16 left-1/2 -translate-x-1/2 z-50 bg-primary/95 backdrop-blur-sm text-primary-foreground px-5 py-2.5 rounded-full shadow-lg shadow-primary/20 flex items-center gap-2.5 text-sm font-medium">
          {isAnalyzing && (
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          )}
          <span>{statusMessage}</span>
        </div>
      )}

      {activeTab === 'characters' && (
        <CharacterGraph
          onAnalyze={handleAnalyzeCharacters}
          isAnalyzing={isAnalyzing}
          analyzeMode={analyzeMode}
          setAnalyzeMode={setAnalyzeMode}
          progress={analysisProgress}
          onCancel={cancelAnalysis}
        />
      )}
      {activeTab === 'plots' && (
        <PlotGraph
          onAnalyze={handleAnalyzePlots}
          isAnalyzing={isAnalyzing}
          analyzeMode={analyzeMode}
          setAnalyzeMode={setAnalyzeMode}
        />
      )}
      {activeTab === 'inspiration' && (
        <InspirationPanel onGenerateInspiration={handleGenerateInspiration} isAnalyzing={isAnalyzing} />
      )}
      {activeTab === 'search' && currentNovel && (
        <Suspense fallback={<LoadingFallback />}>
          <VectorSearch novelId={currentNovel.id} />
        </Suspense>
      )}
      {activeTab === 'knowledge' && currentNovel && (
        <Suspense fallback={<LoadingFallback />}>
          <KnowledgeGraph novelId={currentNovel.id} novelName={currentNovel.name} />
        </Suspense>
      )}
      {activeTab === 'chat' && currentNovel && (
        <Suspense fallback={<LoadingFallback />}>
          <CharacterChat novelId={currentNovel.id} novelName={currentNovel.name} />
        </Suspense>
      )}
      {activeTab === 'assistant' && currentNovel && (
        <Suspense fallback={<LoadingFallback />}>
          <AIAssistant novelId={currentNovel.id} novelName={currentNovel.name} />
        </Suspense>
      )}
      {activeTab === 'worldbuilding' && (
        <Suspense fallback={<LoadingFallback />}>
          <WorldBuildingComp />
        </Suspense>
      )}
      {activeTab === 'foreshadow' && (
        <Suspense fallback={<LoadingFallback />}>
          <ForeshadowTrackerComp />
        </Suspense>
      )}
      {activeTab === 'arcs' && (
        <Suspense fallback={<LoadingFallback />}>
          <CharacterArcComp />
        </Suspense>
      )}
      {activeTab === 'tension' && (
        <Suspense fallback={<LoadingFallback />}>
          <TensionCurveComp />
        </Suspense>
      )}
      {activeTab === 'outline' && (
        <Suspense fallback={<LoadingFallback />}>
          <OutlineWorkflowComp />
        </Suspense>
      )}
      <CharacterQuickSearchComp open={quickSearchOpen} onOpenChange={setQuickSearchOpen} />
    </MainLayout>
  );
}
