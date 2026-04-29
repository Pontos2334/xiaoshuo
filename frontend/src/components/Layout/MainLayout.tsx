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
  Globe,
  BookOpen,
  BookMarked,
  TrendingUp,
  Activity,
  ListTree,
  FileUp,
} from 'lucide-react';

const LAST_PATH_KEY = 'novel-assistant-last-path';

interface MainLayoutProps {
  children: ReactNode;
}

// 扩展 Window 类型
declare global {
  interface Window {
    showDirectoryPicker?: (options?: { id?: string; startIn?: 'desktop' | 'documents' | 'downloads' | 'music' | 'pictures' | 'videos' }) => Promise<FileSystemDirectoryHandle>;
    showOpenFilePicker?: (options?: {
      multiple?: boolean;
      id?: string;
      startIn?: 'desktop' | 'documents' | 'downloads' | 'music' | 'pictures' | 'videos';
      types?: { description?: string; accept: Record<string, string[]> }[];
    }) => Promise<FileSystemFileHandle[]>;
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
  const { activeTab, setActiveTab, sidebarOpen, setSidebarOpen, setQuickSearchOpen } = useUIStore();
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
      const dirHandle = await window.showDirectoryPicker({ id: 'novel-import', startIn: 'documents' }) as ExtendedFileSystemDirectoryHandle;
      const folderName = dirHandle.name;

      const files: { name: string; content: string; size: number }[] = [];

      for await (const entry of dirHandle.values()) {
        if (entry.kind === 'file') {
          const fileHandle = entry as ExtendedFileSystemFileHandle;
          const file = await fileHandle.getFile();
          const lowerName = file.name.toLowerCase();
          if (lowerName.endsWith('.txt') || lowerName.endsWith('.md')) {
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

  // 选择单个/多个小说文件
  const handleSelectFiles = async () => {
    if (!window.showOpenFilePicker) {
      toast.warning('当前浏览器不支持文件选择器，请使用文件夹导入或手动输入路径');
      return;
    }

    try {
      setIsLoading(true);
      const handles = await window.showOpenFilePicker({
        id: 'novel-import-file',
        startIn: 'documents',
        multiple: true,
        types: [
          {
            description: '小说文件',
            accept: { 'text/plain': ['.txt', '.md'] },
          },
        ],
      });

      const uploadFiles: { name: string; content: string; size: number }[] = [];
      for (const handle of handles) {
        const file = await handle.getFile();
        const lowerName = file.name.toLowerCase();
        if (lowerName.endsWith('.txt') || lowerName.endsWith('.md')) {
          const content = await file.text();
          uploadFiles.push({ name: file.name, content, size: file.size });
        }
      }

      if (uploadFiles.length === 0) {
        toast.warning('未选择到 TXT/MD 小说文件');
        setIsLoading(false);
        return;
      }

      const folderName = uploadFiles.length === 1 ? uploadFiles[0].name.replace(/\.(txt|md)$/i, '') : `批量导入_${Date.now()}`;
      const response = await fetch(`${API_URL}/files/upload-folder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folderName, files: uploadFiles }),
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
        toast.success(`已添加 ${newNovels.length} 部小说`);
      } else {
        toast.error(data.error || '导入文件失败');
      }
    } catch (error) {
      if ((error as Error).name === 'AbortError') return;
      console.error('选择文件失败:', error);
      toast.error('选择文件失败，请重试');
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
    { value: 'worldbuilding', label: '世界观', icon: <Globe className="h-4 w-4" /> },
    { value: 'foreshadow', label: '伏笔追踪', icon: <BookMarked className="h-4 w-4" /> },
    { value: 'arcs', label: '角色弧线', icon: <TrendingUp className="h-4 w-4" /> },
    { value: 'tension', label: '节奏张力', icon: <Activity className="h-4 w-4" /> },
    { value: 'outline', label: '大纲管理', icon: <ListTree className="h-4 w-4" /> },
  ];

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="h-14 flex items-center justify-between px-4 shrink-0 bg-white header-gradient-border">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(!sidebarOpen)} className="text-muted-foreground hover:text-foreground">
            {sidebarOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary/8 flex items-center justify-center">
              <BookOpen className="h-4 w-4 text-primary" />
            </div>
            <h1 className="text-lg font-semibold tracking-tight">小说创作助手</h1>
          </div>
          {currentNovel && (
            <>
              <Separator orientation="vertical" className="h-5 mx-1" />
              <span className="text-sm text-muted-foreground font-medium">{currentNovel.name}</span>
            </>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => setQuickSearchOpen(true)} title="角色速查 (Ctrl+K)" className="text-muted-foreground hover:text-foreground">
            <Search className="h-4 w-4 mr-1" />
            <span className="text-xs hidden sm:inline">速查</span>
          </Button>
          <Button variant="outline" size="sm" onClick={handleSelectFiles} disabled={isLoading} className="shadow-sm hover:shadow transition-shadow">
            <FileUp className="h-4 w-4 mr-2" />
            选择文件
          </Button>
          <Button variant="outline" size="sm" onClick={handleOpenFolder} disabled={isLoading} className="shadow-sm hover:shadow transition-shadow">
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
          className={`border-r transition-all duration-300 bg-white ${
            sidebarOpen ? 'w-64' : 'w-0'
          } overflow-hidden`}
        >
          <ScrollArea className="h-full">
            <div className="p-4">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">小说列表</h2>
              <div className="space-y-2">
                {novels.length > 0 ? (
                  novels.map((novel) => (
                    <div
                      key={novel.id}
                      className={`group relative p-3 rounded-lg cursor-pointer text-sm transition-all duration-200 ${
                        currentNovel?.id === novel.id
                          ? 'bg-primary/[0.05] border border-primary/15'
                          : 'border border-transparent hover:bg-muted/40'
                      }`}
                      onClick={() => setCurrentNovel(novel)}
                    >
                      {currentNovel?.id === novel.id && (
                        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-primary" />
                      )}
                      <div className="flex items-center justify-between">
                        <div className="font-medium truncate flex-1 pl-1">{novel.name}</div>
                        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 text-muted-foreground hover:text-foreground"
                            onClick={(e) => handleExportNovel(novel, e)}
                            title="导出"
                          >
                            <Download className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 text-muted-foreground hover:text-destructive"
                            onClick={(e) => handleDeleteNovel(novel, e)}
                            title="删除"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                      <div className={`text-xs mt-0.5 pl-1 ${currentNovel?.id === novel.id ? 'text-primary/50' : 'text-muted-foreground/70'}`}>
                        {((novel as Record<string, unknown>).chapter_count ?? novel.chapterCount ?? 0) as number} 章 · {((novel as Record<string, unknown>).word_count ?? novel.wordCount ?? 0) as number} 字
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="p-4 rounded-lg border border-dashed text-center space-y-1">
                    <p className="text-xs text-muted-foreground">暂无小说</p>
                    <p className="text-[11px] text-muted-foreground/60">打开文件夹添加</p>
                  </div>
                )}
              </div>
            </div>
          </ScrollArea>
        </aside>

        {/* Content Area */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as TabId)} className="flex-1 flex flex-col overflow-hidden">
            <div className="border-b px-4 py-2 shrink-0 bg-muted/15">
              <TabsList className="bg-transparent h-auto p-0 gap-0.5 inline-flex flex-wrap">
                {tabs.map((tab) => (
                  <TabsTrigger
                    key={tab.value}
                    value={tab.value}
                    className="gap-1.5 text-xs px-3 py-1.5 rounded-md transition-all duration-200 data-[state=active]:bg-white data-[state=active]:shadow-sm data-[state=active]:text-primary"
                  >
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
