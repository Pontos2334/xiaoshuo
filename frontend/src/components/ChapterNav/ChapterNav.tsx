'use client';

import { useState, useEffect } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { useNovelStore, useChapterStore } from '@/stores';
import { API_URL } from '@/lib/constants';
import type { Chapter } from '@/types';
import {
  BookOpen,
  CheckCircle2,
  Edit3,
  FileText,
  Loader2,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { toast } from 'sonner';

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  draft: { label: '草稿', color: 'text-yellow-500' },
  completed: { label: '完成', color: 'text-green-500' },
  revised: { label: '修订', color: 'text-blue-500' },
};

export function ChapterNav() {
  const { currentNovel } = useNovelStore();
  const { chapters, setChapters, selectedChapterId, setSelectedChapterId } = useChapterStore();
  const [isLoading, setIsLoading] = useState(false);
  const [expandedChapter, setExpandedChapter] = useState<string | null>(null);
  const [chapterContent, setChapterContent] = useState<Record<string, string>>({});

  // 加载章节列表
  useEffect(() => {
    if (!currentNovel) {
      setChapters([]);
      return;
    }
    const loadChapters = async () => {
      setIsLoading(true);
      try {
        const res = await fetch(`${API_URL}/chapters?novel_id=${currentNovel.id}`);
        if (res.ok) {
          const data = await res.json();
          setChapters(data);
        }
      } catch (e) {
        console.error('加载章节失败:', e);
      } finally {
        setIsLoading(false);
      }
    };
    loadChapters();
  }, [currentNovel, setChapters]);

  // 点击章节加载内容
  const handleChapterClick = async (chapter: Chapter) => {
    setSelectedChapterId(chapter.id);

    if (expandedChapter === chapter.id) {
      setExpandedChapter(null);
      return;
    }
    setExpandedChapter(chapter.id);

    // 加载章节内容
    if (!chapterContent[chapter.id]) {
      try {
        const res = await fetch(`${API_URL}/chapters/${chapter.id}`);
        if (res.ok) {
          const data = await res.json();
          setChapterContent((prev) => ({
            ...prev,
            [chapter.id]: data.content || '',
          }));
        }
      } catch (e) {
        console.error('加载章节内容失败:', e);
      }
    }
  };

  // 更新章节状态
  const handleStatusChange = async (chapter: Chapter, newStatus: string) => {
    try {
      const res = await fetch(`${API_URL}/chapters/${chapter.id}/status?status=${newStatus}`, {
        method: 'PUT',
      });
      if (res.ok) {
        const updated = await res.json();
        setChapters(
          chapters.map((c) => (c.id === chapter.id ? { ...c, status: updated.status } : c))
        );
        toast.success('状态已更新');
      }
    } catch (e) {
      toast.error('更新状态失败');
    }
  };

  // AI 摘要
  const handleGenerateSummary = async (chapter: Chapter) => {
    try {
      toast.info('正在生成摘要...');
      const res = await fetch(`${API_URL}/chapters/${chapter.id}/summary`, { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setChapters(
          chapters.map((c) =>
            c.id === chapter.id ? { ...c, summary: data.data?.summary } : c
          )
        );
        toast.success('摘要已生成');
      } else {
        toast.error(data.error || '生成失败');
      }
    } catch (e) {
      toast.error('生成摘要失败');
    }
  };

  if (!currentNovel) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        请先选择一部小说
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-4">
        <Loader2 className="h-4 w-4 animate-spin mr-2" />
        <span className="text-sm text-muted-foreground">加载中...</span>
      </div>
    );
  }

  if (chapters.length === 0) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        暂无章节数据
      </div>
    );
  }

  const totalWords = chapters.reduce((sum, c) => sum + (c.wordCount || 0), 0);

  return (
    <ScrollArea className="h-full">
      <div className="p-3">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold flex items-center gap-1.5">
            <BookOpen className="h-4 w-4" />
            章节 ({chapters.length})
          </h3>
          <span className="text-xs text-muted-foreground">
            共 {totalWords.toLocaleString()} 字
          </span>
        </div>

        <div className="space-y-1">
          {chapters.map((chapter) => {
            const statusInfo = STATUS_LABELS[chapter.status] || STATUS_LABELS.draft;
            const isSelected = selectedChapterId === chapter.id;
            const isExpanded = expandedChapter === chapter.id;

            return (
              <div key={chapter.id}>
                <div
                  className={`p-2 rounded-md cursor-pointer text-sm transition-colors ${
                    isSelected
                      ? 'bg-primary/10 border border-primary/20'
                      : 'hover:bg-muted'
                  }`}
                  onClick={() => handleChapterClick(chapter)}
                >
                  <div className="flex items-center gap-1.5">
                    {isExpanded ? (
                      <ChevronDown className="h-3 w-3 shrink-0 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="h-3 w-3 shrink-0 text-muted-foreground" />
                    )}
                    <span className="truncate flex-1 font-medium">
                      {chapter.title || `第${chapter.chapterNumber}章`}
                    </span>
                    <span className={`text-xs ${statusInfo.color}`}>
                      {statusInfo.label}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 ml-5 mt-0.5">
                    <span className="text-xs text-muted-foreground">
                      {(chapter.wordCount || 0).toLocaleString()} 字
                    </span>
                    {chapter.summary && (
                      <FileText className="h-3 w-3 text-muted-foreground" />
                    )}
                  </div>
                </div>

                {/* 展开的详情 */}
                {isExpanded && (
                  <div className="ml-4 mt-1 mb-2 p-2 rounded bg-muted/50 text-xs space-y-2">
                    {/* 章节内容预览 */}
                    {chapterContent[chapter.id] && (
                      <div className="text-muted-foreground line-clamp-4 whitespace-pre-wrap">
                        {chapterContent[chapter.id].slice(0, 200)}
                        {chapterContent[chapter.id].length > 200 ? '...' : ''}
                      </div>
                    )}

                    {/* 摘要 */}
                    {chapter.summary && (
                      <div className="border-t pt-1">
                        <span className="font-medium">摘要：</span>
                        <span className="text-muted-foreground">{chapter.summary}</span>
                      </div>
                    )}

                    {/* 操作按钮 */}
                    <div className="flex items-center gap-1 pt-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 text-xs"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleGenerateSummary(chapter);
                        }}
                      >
                        <Edit3 className="h-3 w-3 mr-1" />
                        AI摘要
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 text-xs"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleStatusChange(
                            chapter,
                            chapter.status === 'completed' ? 'revised' : 'completed'
                          );
                        }}
                      >
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                        {chapter.status === 'completed' ? '标记修订' : '标记完成'}
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </ScrollArea>
  );
}
