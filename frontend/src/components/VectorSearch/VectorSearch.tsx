'use client';

import { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Search, Loader2, User, BookOpen, FileText } from 'lucide-react';
import { API_URL } from '@/lib/constants';
import { toast } from 'sonner';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface VectorSearchProps {
  novelId: string;
}

interface SemanticResult {
  id: string;
  content: string;
  metadata: {
    type: string;
    source: string;
    title: string;
  };
  score: number;
}

interface CharacterResult {
  id: string;
  name: string;
  similarity: number;
  [key: string]: unknown;
}

interface PlotResult {
  id: string;
  title: string;
  similarity: number;
  [key: string]: unknown;
}

type SearchTab = 'all' | 'semantic' | 'characters' | 'plots';

interface UnifiedResult {
  id: string;
  type: '人物' | '情节' | '文本';
  title: string;
  content: string;
  score: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getScoreBadgeColor(score: number): string {
  if (score > 0.8) return 'bg-green-100 text-green-800 border-green-300 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800';
  if (score > 0.5) return 'bg-yellow-100 text-yellow-800 border-yellow-300 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-800';
  return 'bg-red-100 text-red-800 border-red-300 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800';
}

function getTypeBadgeColor(type: string): string {
  switch (type) {
    case '人物':
      return 'bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800';
    case '情节':
      return 'bg-purple-100 text-purple-800 border-purple-300 dark:bg-purple-900/30 dark:text-purple-400 dark:border-purple-800';
    case '文本':
      return 'bg-gray-100 text-gray-800 border-gray-300 dark:bg-gray-900/30 dark:text-gray-400 dark:border-gray-800';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-300 dark:bg-gray-900/30 dark:text-gray-400 dark:border-gray-800';
  }
}

function getTypeIcon(type: string) {
  switch (type) {
    case '人物': return User;
    case '情节': return BookOpen;
    case '文本': return FileText;
    default: return FileText;
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function VectorSearch({ novelId }: VectorSearchProps) {
  const [query, setQuery] = useState('');
  const [activeTab, setActiveTab] = useState<SearchTab>('all');
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<UnifiedResult[]>([]);

  // ------- API calls -------

  const fetchSemantic = useCallback(async (searchQuery: string, limit: number): Promise<UnifiedResult[]> => {
    const res = await fetch(`${API_URL}/search/semantic`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: searchQuery, novel_id: novelId, limit }),
    });
    if (!res.ok) throw new Error(`语义搜索失败: ${res.status}`);
    const json = await res.json();
    if (!json.success) throw new Error('语义搜索返回失败');
    return (json.data as SemanticResult[]).map((item) => ({
      id: item.id,
      type: (item.metadata?.type === 'character' ? '人物' : item.metadata?.type === 'plot' ? '情节' : '文本') as UnifiedResult['type'],
      title: item.metadata?.title || '未命名',
      content: item.content,
      score: item.score,
    }));
  }, [novelId]);

  const fetchCharacters = useCallback(async (searchQuery: string, limit: number): Promise<UnifiedResult[]> => {
    const res = await fetch(`${API_URL}/search/characters`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: searchQuery, novel_id: novelId, limit }),
    });
    if (!res.ok) throw new Error(`人物搜索失败: ${res.status}`);
    const json = await res.json();
    if (!json.success) throw new Error('人物搜索返回失败');
    return (json.data as CharacterResult[]).map((item) => ({
      id: item.id,
      type: '人物' as const,
      title: item.name || '未命名',
      content: item.name || '',
      score: item.similarity,
    }));
  }, [novelId]);

  const fetchPlots = useCallback(async (searchQuery: string, limit: number): Promise<UnifiedResult[]> => {
    const res = await fetch(`${API_URL}/search/plots`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: searchQuery, novel_id: novelId, limit }),
    });
    if (!res.ok) throw new Error(`情节搜索失败: ${res.status}`);
    const json = await res.json();
    if (!json.success) throw new Error('情节搜索返回失败');
    return (json.data as PlotResult[]).map((item) => ({
      id: item.id,
      type: '情节' as const,
      title: item.title || '未命名',
      content: item.title || '',
      score: item.similarity,
    }));
  }, [novelId]);

  // ------- Search handler -------

  const handleSearch = useCallback(async () => {
    const trimmed = query.trim();
    if (!trimmed) {
      toast.error('请输入搜索关键词');
      return;
    }

    setIsLoading(true);
    setResults([]);

    try {
      let combined: UnifiedResult[] = [];
      const limit = 10;

      if (activeTab === 'all' || activeTab === 'semantic') {
        try {
          const semanticResults = await fetchSemantic(trimmed, limit);
          combined = combined.concat(semanticResults);
        } catch {
          // If semantic search fails on "all" tab, continue trying others
        }
      }

      if (activeTab === 'all' || activeTab === 'characters') {
        try {
          const characterResults = await fetchCharacters(trimmed, limit);
          combined = combined.concat(characterResults);
        } catch {
          // continue
        }
      }

      if (activeTab === 'all' || activeTab === 'plots') {
        try {
          const plotResults = await fetchPlots(trimmed, limit);
          combined = combined.concat(plotResults);
        } catch {
          // continue
        }
      }

      // Sort by score descending
      combined.sort((a, b) => b.score - a.score);
      setResults(combined);

      if (combined.length === 0) {
        toast.info('未找到相关内容');
      } else {
        toast.success(`找到 ${combined.length} 条结果`);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : '搜索时发生错误';
      toast.error(message);
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }, [query, activeTab, fetchSemantic, fetchCharacters, fetchPlots]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && !isLoading) {
        handleSearch();
      }
    },
    [handleSearch, isLoading],
  );

  // ------- Render -------

  return (
    <div className="h-full">
      <Card className="h-full flex flex-col">
        {/* Header */}
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            向量搜索
          </CardTitle>
        </CardHeader>

        <CardContent className="flex-1 flex flex-col gap-3 overflow-hidden">
          {/* Search input */}
          <div className="flex items-center gap-2 shrink-0">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入搜索关键词..."
              className="flex-1 h-9 text-sm"
              disabled={isLoading}
            />
            <Button
              onClick={handleSearch}
              disabled={isLoading || !query.trim()}
              size="sm"
              className="shrink-0"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
            </Button>
          </div>

          {/* Type filter tabs */}
          <Tabs
            value={activeTab}
            onValueChange={(val) => setActiveTab(val as SearchTab)}
            className="shrink-0"
          >
            <TabsList>
              <TabsTrigger value="all">全部</TabsTrigger>
              <TabsTrigger value="semantic">语义</TabsTrigger>
              <TabsTrigger value="characters">人物</TabsTrigger>
              <TabsTrigger value="plots">情节</TabsTrigger>
            </TabsList>

            {/* Shared content area across all tabs */}
            <TabsContent value={activeTab} className="flex-1 overflow-hidden mt-3">
              {/* Loading state */}
              {isLoading ? (
                <div className="flex items-center justify-center h-full">
                  <div className="flex flex-col items-center gap-2 text-muted-foreground">
                    <Loader2 className="h-8 w-8 animate-spin" />
                    <span className="text-sm">搜索中...</span>
                  </div>
                </div>
              ) : results.length > 0 ? (
                /* Results list */
                <ScrollArea className="h-full">
                  <div className="space-y-2 pr-2">
                    {results.map((result) => {
                      const TypeIcon = getTypeIcon(result.type);
                      return (
                        <Card key={result.id} className="overflow-hidden">
                          <CardHeader className="py-2 px-3 flex-row items-center justify-between space-y-0">
                            <CardTitle className="text-sm font-medium truncate flex-1 mr-2">
                              {result.title}
                            </CardTitle>
                            <div className="flex items-center gap-1.5 shrink-0">
                              <Badge
                                variant="outline"
                                className={`text-[10px] ${getTypeBadgeColor(result.type)}`}
                              >
                                {result.type}
                              </Badge>
                              <Badge
                                variant="outline"
                                className={`text-[10px] ${getScoreBadgeColor(result.score)}`}
                              >
                                {(result.score * 100).toFixed(1)}%
                              </Badge>
                            </div>
                          </CardHeader>
                          <CardContent className="py-2 px-3">
                            <div className="flex items-start gap-2">
                              <TypeIcon className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
                              <p className="text-xs text-muted-foreground leading-relaxed">
                                {result.content.length > 200
                                  ? result.content.slice(0, 200) + '...'
                                  : result.content}
                              </p>
                            </div>
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>
                </ScrollArea>
              ) : (
                /* Empty state */
                <div className="flex items-center justify-center h-full">
                  <div className="flex flex-col items-center gap-2 text-muted-foreground">
                    <Search className="h-8 w-8 opacity-30" />
                    <span className="text-sm">输入搜索关键词查找语义相似的内容</span>
                  </div>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
