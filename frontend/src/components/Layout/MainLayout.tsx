'use client';

import { ReactNode, useState, useEffect } from 'react';
import { toast } from 'sonner';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { useUIStore, useNovelStore } from '@/stores';
import type { TabId } from '@/stores';
import { Novel } from '@/types';
import { API_URL } from '@/lib/constants';
import {
  Users,
  GitBranch,
  Lightbulb,
  FolderOpen,
  Menu,
  X,
  Loader2,
  Trash2,
  Download,
  Search,
  Network,
  MessageSquare,
  Sparkles,
} from 'lucide-react';

const LAST_PATH_KEY = 'novel-assistant-last-path';

interface MainLayoutProps {
  children: ReactNode;
}

// 扩展 Window 类型
declare global {
  interface Window {
    showDirectoryPicker?: () => Promise<FileSystemDirectoryHandle>;
  }
}

interface ExtendedFileSystemDirectoryHandle extends FileSystemDirectoryHandle {
  values(): AsyncIterable<FileSystemHandle>;
  kind: 'directory';
  name: string;
}

interface ExtendedFileSystemFileHandle extends FileSystemFileHandle {
  getFile(): Promise<File>;
}

export function MainLayout({ children }: MainLayoutProps) {
  const { activeTab, setActiveTab, sidebarOpen, setSidebarOpen } = useUIStore();
  const { novels, currentNovel, setNovels, setCurrentNovel } = useNovelStore();
  const [folderDialogOpen, setFolderDialogOpen] = useState(false);
  const [folderPath, setFolderPath] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // 加载已保存的小说列表
  useEffect(() => {
    const loadSavedNovels = async () => {
      try {
        const response = await fetch(`${API_URL}/files/novels`);
        if (response.ok) {
          const data = await response.json();
          if (data && data.length > 0) {
            setNovels(data);
            const savedPath = localStorage.getItem(LAST_PATH_KEY);
            if (savedPath) {
              const savedNovel = data.find((n: { name: string; path: string }) =>
                n.name === savedPath || n.path.includes(savedPath)
              );
              if (savedNovel) {
                setCurrentNovel(savedNovel);
              } else {
                setCurrentNovel(data[0]);
              }
            } else {
              setCurrentNovel(data[0]);
            }
          }
        }
      } catch (error) {
        console.error('加载已保存的小说失败:', error);
      }
    };
    loadSavedNovels();
  }, [setNovels, setCurrentNovel]);

  // 使用系统文件选择器
  const handleSelectFolder = async () => {
    if (!window.showDirectoryPicker) {
      setFolderDialogOpen(true);
      return;
    }

    try {
      setIsLoading(true);
      const dirHandle = await window.showDirectoryPicker() as ExtendedFileSystemDirectoryHandle;
      const folderName = dirHandle.name;

      const files: { name: string; content: string; size: number }[] = [];

      for await (const entry of dirHandle.values()) {
        if (entry.kind === 'file') {
          const fileHandle = entry as ExtendedFileSystemFileHandle;
          const file = await fileHandle.getFile();
          if (file.name.endsWith('.txt') || file.name.endsWith('.md')) {
            const content = await file.text();
            files.push({ name: file.name, content, size: file.size });
          }
        }
      }

      if (files.length === 0) {
        toast.warning('该文件夹中没有找到小说文件（TXT/MD）');
        setIsLoading(false);
        return;
      }

      const response = await fetch(`${API_URL}/files/upload-folder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folderName, files }),
      });

      const data = await response.json();

      if (data.success && data.data) {
        const newNovels = data.data.filter(
          (newNovel: Novel) => !novels.some((n) => n.id === newNovel.id)
        );
        setNovels([...novels, ...newNovels]);
        if (data.data.length > 0) {
          setCurrentNovel(data.data[0]);
        }
        localStorage.setItem(LAST_PATH_KEY, folderName);
        toast.success(`已添加 ${newNovels.length} 部小说`);
      } else {
        toast.error(data.error || '处理文件夹失败');
      }
    } catch (error) {
      if ((error as Error).name === 'AbortError') return;
      console.error('选择文件夹失败:', error);
      toast.error('选择文件夹失败，请重试');
    } finally {
      setIsLoading(false);
    }
  };

  // 手动输入路径扫描
  const scanFolder = async (path: string) => {
    if (!path.trim()) return;

    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/files/scan?path=${encodeURIComponent(path)}`);
      const data = await response.json();

      if (data.success && data.data) {
        setNovels(data.data);
        if (data.data.length > 0) {
          setCurrentNovel(data.data[0]);
        }
        setFolderDialogOpen(false);
        localStorage.setItem(LAST_PATH_KEY, path);
      } else {
        toast.error(data.error || '扫描文件夹失败');
      }
    } catch (error) {
      console.error('扫描文件夹失败:', error);
      toast.error('扫描文件夹失败，请确保后端服务正在运行');
    } finally {
      setIsLoading(false);
    }
  };

  const handleScanFolder = () => scanFolder(folderPath);
  const handleOpenFolder = () => handleSelectFolder();

  // 删除小说
  const handleDeleteNovel = async (novel: Novel, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`确定要删除《${novel.name}》吗？\n\n这将同时删除该小说的所有人物、情节和灵感数据。`)) return;

    try {
      const response = await fetch(`${API_URL}/files/novels/${novel.id}`, { method: 'DELETE' });
      const data = await response.json();

      if (data.success) {
        const updatedNovels = novels.filter((n) => n.id !== novel.id);
        setNovels(updatedNovels);
        if (currentNovel?.id === novel.id) {
          setCurrentNovel(updatedNovels.length > 0 ? updatedNovels[0] : null);
        }
        toast.success(data.data?.message || '删除成功');
      } else {
        toast.error(data.error || '删除失败');
      }
    } catch (error) {
      console.error('删除小说失败:', error);
      toast.error('删除失败，请重试');
    }
  };

  // 导出小说
  const handleExportNovel = async (novel: Novel, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const response = await fetch(`${API_URL}/files/novels/${novel.id}/export`);
      if (!response.ok) {
        const data = await response.json();
        toast.error(data.detail || '导出失败');
        return;
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${novel.name}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success('导出成功');
    } catch (error) {
      console.error('导出小说失败:', error);
      toast.error('导出失败，请重试');
    }
  };

  const tabs: { value: TabId; label: string; icon: ReactNode }[] = [
    { value: 'characters', label: '人物关系图', icon: <Users className="h-4 w-4" /> },
    { value: 'plots', label: '情节关联图', icon: <GitBranch className="h-4 w-4" /> },
    { value: 'inspiration', label: '灵感提示', icon: <Lightbulb className="h-4 w-4" /> },
    { value: 'search', label: '语义搜索', icon: <Search className="h-4 w-4" /> },
    { value: 'knowledge', label: '知识图谱', icon: <Network className="h-4 w-4" /> },
    { value: 'chat', label: '人物对话', icon: <MessageSquare className="h-4 w-4" /> },
    { value: 'assistant', label: '智能助手', icon: <Sparkles className="h-4 w-4" /> },
  ];

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="h-14 border-b flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(!sidebarOpen)}>
            {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
          <h1 className="text-xl font-bold">小说创作助手</h1>
          {currentNovel && (
            <>
              <Separator orientation="vertical" className="h-6" />
              <span className="text-muted-foreground">{currentNovel.name}</span>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleOpenFolder} disabled={isLoading}>
            {isLoading ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <FolderOpen className="h-4 w-4 mr-2" />
            )}
            打开文件夹
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <aside
          className={`border-r transition-all duration-300 ${
            sidebarOpen ? 'w-64' : 'w-0'
          } overflow-hidden`}
        >
          <ScrollArea className="h-full">
            <div className="p-4">
              <h2 className="font-semibold mb-4">小说列表</h2>
              <div className="space-y-2">
                {novels.length > 0 ? (
                  novels.map((novel) => (
                    <div
                      key={novel.id}
                      className={`p-2 rounded-md cursor-pointer text-sm transition-colors group ${
                        currentNovel?.id === novel.id
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted hover:bg-muted/80'
                      }`}
                      onClick={() => setCurrentNovel(novel)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="font-medium truncate flex-1">{novel.name}</div>
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Button
                            variant="ghost"
                            size="icon"
                            className={`h-6 w-6 ${
                              currentNovel?.id === novel.id
                                ? 'text-primary-foreground hover:bg-primary-foreground/20'
                                : 'text-muted-foreground hover:bg-muted-foreground/20'
                            }`}
                            onClick={(e) => handleExportNovel(novel, e)}
                            title="导出"
                          >
                            <Download className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className={`h-6 w-6 ${
                              currentNovel?.id === novel.id
                                ? 'text-primary-foreground hover:bg-primary-foreground/20'
                                : 'text-muted-foreground hover:bg-muted-foreground/20 hover:text-destructive'
                            }`}
                            onClick={(e) => handleDeleteNovel(novel, e)}
                            title="删除"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                      <div className={`text-xs ${currentNovel?.id === novel.id ? 'text-primary-foreground/70' : 'text-muted-foreground'}`}>
                        {((novel as Record<string, unknown>).chapter_count ?? novel.chapterCount ?? 0) as number} 章 · {((novel as Record<string, unknown>).word_count ?? novel.wordCount ?? 0) as number} 字
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-2 rounded-md bg-muted text-sm text-muted-foreground">
                    暂无小说，请打开文件夹
                  </div>
                )}
              </div>
            </div>
          </ScrollArea>
        </aside>

        {/* Content Area */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as TabId)} className="flex-1 flex flex-col overflow-hidden">
            <div className="border-b px-4 shrink-0">
              <TabsList className="flex-wrap h-auto gap-1">
                {tabs.map((tab) => (
                  <TabsTrigger key={tab.value} value={tab.value} className="gap-1.5 text-xs">
                    {tab.icon}
                    {tab.label}
                  </TabsTrigger>
                ))}
              </TabsList>
            </div>

            {/* Fix: only render children in the active tab, not all tabs */}
            {tabs.map((tab) => (
              <TabsContent key={tab.value} value={tab.value} className="flex-1 m-0 overflow-hidden">
                {activeTab === tab.value && children}
              </TabsContent>
            ))}
          </Tabs>
        </main>
      </div>

      {/* 手动输入路径对话框 */}
      <Dialog open={folderDialogOpen} onOpenChange={setFolderDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>打开文件夹</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">文件夹路径</label>
              <Input
                value={folderPath}
                onChange={(e) => setFolderPath(e.target.value)}
                placeholder="例如: C:\novels 或 /home/user/novels"
                className="mt-2"
              />
              <p className="text-xs text-muted-foreground mt-1">
                输入包含小说文件（TXT/MD）的文件夹路径
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setFolderDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleScanFolder} disabled={isLoading || !folderPath.trim()}>
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  扫描中...
                </>
              ) : (
                '扫描'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
