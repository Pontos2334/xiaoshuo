'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { toast } from 'sonner';
import { MainLayout } from '@/components/Layout/MainLayout';
import { CharacterGraph } from '@/components/CharacterGraph/CharacterGraph';
import { PlotGraph } from '@/components/PlotGraph/PlotGraph';
import { InspirationPanel } from '@/components/InspirationPanel/InspirationPanel';
import { useUIStore, useCharacterStore, usePlotStore, useInspirationStore, useNovelStore } from '@/stores';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002/api';

export type AnalyzeMode = 'full' | 'incremental';

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
  }, [currentNovel?.id, setCharacters, setRelations, setPlotNodes, setPlotConnections, clearInspirations, addInspiration]);

  // AI分析人物
  const handleAnalyzeCharacters = async (mode?: AnalyzeMode) => {
    const actualMode = mode || analyzeMode;
    if (!currentNovel) {
      toast.error('请先打开文件夹选择小说');
      return;
    }

    setIsAnalyzing(true);
    setStatusMessage(actualMode === 'incremental' ? '正在增量分析人物...' : '正在全量分析人物...');

    try {
      setStatusMessage('正在读取小说内容...');
      const response = await fetch(`${API_URL}/characters/analyze?novel_id=${currentNovel.id}&mode=${actualMode}`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`服务器错误: ${response.status} - ${errorText}`);
      }

      setStatusMessage('正在解析人物信息...');
      const data = await response.json();

      if (data.success) {
        const characters = data.data?.characters || data.data || [];
        setCharacters(characters);
        const modeText = actualMode === 'incremental' ? '增量' : '全量';
        setStatusMessage(`${modeText}分析完成！发现 ${characters.length} 个人物`);

        // 分析人物关系
        setStatusMessage('正在分析人物关系...');
        const relResponse = await fetch(`${API_URL}/characters/relations/analyze?novel_id=${currentNovel.id}`, {
          method: 'POST',
        });
        const relData = await relResponse.json();
        if (relData.success) {
          setRelations(relData.data || []);
          toast.success(`完成！${characters.length} 个人物，${relData.data?.length || 0} 个关系`);
        }
      } else {
        toast.error(`分析失败: ${data.error || '未知错误'}`);
      }
    } catch (error) {
      console.error('分析人物失败:', error);
      toast.error(`分析失败: ${(error as Error).message}`);
    } finally {
      setIsAnalyzing(false);
      setTimeout(() => setStatusMessage(''), 3000);
    }
  };

  // AI分析情节
  const handleAnalyzePlots = async (mode?: AnalyzeMode) => {
    const actualMode = mode || analyzeMode;
    if (!currentNovel) {
      toast.error('请先打开文件夹选择小说');
      return;
    }

    setIsAnalyzing(true);
    setStatusMessage(actualMode === 'incremental' ? '正在增量分析情节...' : '正在全量分析情节...');

    try {
      setStatusMessage('正在读取小说内容...');
      const response = await fetch(`${API_URL}/plots/analyze?novel_id=${currentNovel.id}&mode=${actualMode}`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`服务器错误: ${response.status} - ${errorText}`);
      }

      setStatusMessage('正在解析情节节点...');
      const data = await response.json();

      if (data.success) {
        const nodes = data.data?.nodes || data.data || [];
        setPlotNodes(nodes);
        const modeText = actualMode === 'incremental' ? '增量' : '全量';
        setStatusMessage(`${modeText}分析完成！发现 ${nodes.length} 个情节节点`);

        // 分析情节连接
        setStatusMessage('正在分析情节关联...');
        const connResponse = await fetch(`${API_URL}/plots/connections/analyze?novel_id=${currentNovel.id}`, {
          method: 'POST',
        });
        const connData = await connResponse.json();
        if (connData.success) {
          setPlotConnections(connData.data || []);
          toast.success(`完成！${nodes.length} 个情节，${connData.data?.length || 0} 个关联`);
        }
      } else {
        toast.error(`分析失败: ${data.error || '未知错误'}`);
      }
    } catch (error) {
      console.error('分析情节失败:', error);
      toast.error(`分析失败: ${(error as Error).message}`);
    } finally {
      setIsAnalyzing(false);
      setTimeout(() => setStatusMessage(''), 3000);
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
        <div className="fixed top-16 left-1/2 -translate-x-1/2 z-50 bg-primary text-primary-foreground px-4 py-2 rounded-md shadow-lg flex items-center gap-2">
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
    </MainLayout>
  );
}
