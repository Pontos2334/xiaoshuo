'use client';

import { ReactNode, useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { useUIStore, useNovelStore } from '@/stores';
import { Novel } from '@/types';
import {
  Users,
  GitBranch,
  Lightbulb,
  FolderOpen,
  Menu,
  X,
  Loader2,
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002/api';
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

  // 加载上次保存的路径
  useEffect(() => {
    const savedPath = localStorage.getItem(LAST_PATH_KEY);
    if (savedPath) {
      setFolderPath(savedPath);
    }
  }, []);

  // 使用系统文件选择器
  const handleSelectFolder = async () => {
    if (!window.showDirectoryPicker) {
      // 不支持 File System Access API，打开手动输入对话框
      setFolderDialogOpen(true);
      return;
    }

    try {
      setIsLoading(true);
      const dirHandle = await window.showDirectoryPicker() as ExtendedFileSystemDirectoryHandle;
      const folderName = dirHandle.name;

      // 读取文件夹中的所有文件
      const files: { name: string; content: string; size: number }[] = [];

      for await (const entry of dirHandle.values()) {
        if (entry.kind === 'file') {
          const fileHandle = entry as ExtendedFileSystemFileHandle;
          const file = await fileHandle.getFile();
          // 只处理 txt 和 md 文件
          if (file.name.endsWith('.txt') || file.name.endsWith('.md')) {
            const content = await file.text();
            files.push({
              name: file.name,
              content,
              size: file.size,
            });
          }
        }
      }

      if (files.length === 0) {
        alert('该文件夹中没有找到小说文件（TXT/MD）');
        setIsLoading(false);
        return;
      }

      // 发送文件内容到后端处理
      const response = await fetch(`${API_URL}/files/upload-folder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          folderName,
          files,
        }),
      });

      const data = await response.json();

      if (data.success && data.data) {
        setNovels(data.data);
        if (data.data.length > 0) {
          setCurrentNovel(data.data[0]);
        }
        // 保存文件夹名称
        localStorage.setItem(LAST_PATH_KEY, folderName);
      } else {
        alert(data.error || '处理文件夹失败');
      }
    } catch (error) {
      // 用户取消选择
      if ((error as Error).name === 'AbortError') {
        return;
      }
      console.error('选择文件夹失败:', error);
      alert('选择文件夹失败，请重试');
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
        alert(data.error || '扫描文件夹失败');
      }
    } catch (error) {
      console.error('扫描文件夹失败:', error);
      alert('扫描文件夹失败，请确保后端服务正在运行');
    } finally {
      setIsLoading(false);
    }
  };

  const handleScanFolder = () => scanFolder(folderPath);

  const handleOpenFolder = () => {
    handleSelectFolder();
  };

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="h-14 border-b flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
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
                      className={`p-2 rounded-md cursor-pointer text-sm transition-colors ${
                        currentNovel?.id === novel.id
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted hover:bg-muted/80'
                      }`}
                      onClick={() => setCurrentNovel(novel)}
                    >
                      <div className="font-medium">{novel.name}</div>
                      <div className={`text-xs ${currentNovel?.id === novel.id ? 'text-primary-foreground/70' : 'text-muted-foreground'}`}>
                        {(novel.chapter_count ?? novel.chapterCount ?? 0)} 章 · {((novel.word_count ?? novel.wordCount ?? 0) as number).toLocaleString()} 字
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
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)} className="flex-1 flex flex-col">
            <div className="border-b px-4">
              <TabsList>
                <TabsTrigger value="characters" className="gap-2">
                  <Users className="h-4 w-4" />
                  人物关系图
                </TabsTrigger>
                <TabsTrigger value="plots" className="gap-2">
                  <GitBranch className="h-4 w-4" />
                  情节关联图
                </TabsTrigger>
                <TabsTrigger value="inspiration" className="gap-2">
                  <Lightbulb className="h-4 w-4" />
                  灵感提示
                </TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="characters" className="flex-1 m-0 overflow-hidden">
              <ScrollArea className="h-full">
                <div className="p-4">
                  {children}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="plots" className="flex-1 m-0 overflow-hidden">
              <ScrollArea className="h-full">
                <div className="p-4">
                  {children}
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="inspiration" className="flex-1 m-0 overflow-hidden">
              <ScrollArea className="h-full">
                <div className="p-4">
                  {children}
                </div>
              </ScrollArea>
            </TabsContent>
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
