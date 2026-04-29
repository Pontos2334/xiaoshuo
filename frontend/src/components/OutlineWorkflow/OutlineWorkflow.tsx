'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Loader2,
  ListTree,
  Plus,
  ChevronRight,
  ChevronDown,
  Sparkles,
  Trash2,
  Edit3,
} from 'lucide-react';
import { toast } from 'sonner';
import { useNovelStore, useOutlineStore } from '@/stores';
import { API_URL } from '@/lib/constants';
import type { OutlineNode } from '@/types';

// ---------------------------------------------------------------------------
// Level & Status helpers
// ---------------------------------------------------------------------------

const LEVEL_CONFIG: Record<number, { label: string; variant: 'default' | 'secondary' | 'outline' }> = {
  0: { label: '总纲', variant: 'default' },
  1: { label: '卷', variant: 'secondary' },
  2: { label: '章节', variant: 'outline' },
};

const STATUS_CONFIG: Record<string, { label: string; variant: 'default' | 'secondary' | 'outline' }> = {
  draft: { label: '草稿', variant: 'secondary' },
  completed: { label: '完成', variant: 'default' },
  active: { label: '进行中', variant: 'outline' },
};

// ---------------------------------------------------------------------------
// TreeNode recursive component
// ---------------------------------------------------------------------------

interface TreeNodeProps {
  node: OutlineNode;
  selectedId: string | null;
  expandedIds: Set<string>;
  onSelect: (id: string) => void;
  onToggle: (id: string) => void;
  onAddChild: (parentId: string) => void;
  onBreakdown: (node: OutlineNode) => void;
}

function TreeNode({
  node,
  selectedId,
  expandedIds,
  onSelect,
  onToggle,
  onAddChild,
  onBreakdown,
}: TreeNodeProps) {
  const isExpanded = expandedIds.has(node.id);
  const isSelected = selectedId === node.id;
  const levelCfg = LEVEL_CONFIG[node.level] ?? LEVEL_CONFIG[2];
  const statusCfg = STATUS_CONFIG[node.status] ?? STATUS_CONFIG.draft;
  const hasChildren = node.children && node.children.length > 0;
  const canAddChild = node.level < 2;

  return (
    <div>
      <div
        className={`flex items-center gap-1.5 py-1.5 px-2 rounded-md cursor-pointer text-sm transition-colors group ${
          isSelected
            ? 'bg-primary/10 border border-primary/20'
            : 'hover:bg-muted'
        }`}
        onClick={() => {
          onSelect(node.id);
          if (hasChildren) onToggle(node.id);
        }}
      >
        {/* Expand / collapse */}
        {hasChildren ? (
          isExpanded ? (
            <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
          )
        ) : (
          <span className="w-4 shrink-0" />
        )}

        <span className="font-medium truncate flex-1">{node.title}</span>

        <Badge variant={levelCfg.variant} className="text-[10px] px-1.5 py-0">
          {levelCfg.label}
        </Badge>

        <Badge variant={statusCfg.variant} className="text-[10px] px-1.5 py-0">
          {statusCfg.label}
        </Badge>

        {/* Action buttons */}
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
          {canAddChild && (
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5"
              onClick={(e) => {
                e.stopPropagation();
                onAddChild(node.id);
              }}
              title="添加子节点"
            >
              <Plus className="h-3 w-3" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-5 w-5"
            onClick={(e) => {
              e.stopPropagation();
              onBreakdown(node);
            }}
            title="AI 拆解"
          >
            <Sparkles className="h-3 w-3" />
          </Button>
        </div>
      </div>

      {/* Children */}
      {isExpanded && hasChildren && (
        <div className="pl-4">
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              selectedId={selectedId}
              expandedIds={expandedIds}
              onSelect={onSelect}
              onToggle={onToggle}
              onAddChild={onAddChild}
              onBreakdown={onBreakdown}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function OutlineWorkflow() {
  const { currentNovel } = useNovelStore();
  const {
    outlineNodes,
    selectedNodeId,
    setOutlineNodes,
    setSelectedNodeId,
    addOutlineNode,
    updateOutlineNode,
    deleteOutlineNode,
  } = useOutlineStore();

  const [isLoading, setIsLoading] = useState(false);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [isGenerating, setIsGenerating] = useState(false);
  const [isBreakingDown, setIsBreakingDown] = useState(false);

  // Add-child dialog state
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [addChildParentId, setAddChildParentId] = useState<string | null>(null);
  const [newChildTitle, setNewChildTitle] = useState('');
  const [newChildContent, setNewChildContent] = useState('');

  // Edit detail form state
  const [editTitle, setEditTitle] = useState('');
  const [editContent, setEditContent] = useState('');
  const [editChapterRange, setEditChapterRange] = useState('');
  const [editStatus, setEditStatus] = useState<'draft' | 'completed' | 'active'>('draft');
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // -----------------------------------------------------------------------
  // Load outline tree
  // -----------------------------------------------------------------------

  const loadOutline = useCallback(async () => {
    if (!currentNovel) return;
    setIsLoading(true);
    try {
      const res = await fetch(`${API_URL}/outlines?novel_id=${currentNovel.id}`);
      if (res.ok) {
        const data = await res.json();
        setOutlineNodes(Array.isArray(data) ? data : data.data ?? []);
      }
    } catch (e) {
      console.error('加载大纲失败:', e);
    } finally {
      setIsLoading(false);
    }
  }, [currentNovel, setOutlineNodes]);

  useEffect(() => {
    loadOutline();
  }, [loadOutline]);

  // -----------------------------------------------------------------------
  // Sync selected node detail into edit form
  // -----------------------------------------------------------------------

  const selectedNode = useMemo<OutlineNode | null>(() => {
    if (!selectedNodeId) return null;
    const findNode = (nodes: OutlineNode[]): OutlineNode | null => {
      for (const n of nodes) {
        if (n.id === selectedNodeId) return n;
        if (n.children) {
          const found = findNode(n.children);
          if (found) return found;
        }
      }
      return null;
    };
    return findNode(outlineNodes);
  }, [selectedNodeId, outlineNodes]);

  useEffect(() => {
    if (selectedNode) {
      setEditTitle(selectedNode.title);
      setEditContent(selectedNode.content);
      setEditChapterRange(selectedNode.chapterRange);
      setEditStatus(selectedNode.status);
    }
  }, [selectedNode]);

  // -----------------------------------------------------------------------
  // Handlers
  // -----------------------------------------------------------------------

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // AI generate master outline
  const handleGenerateMaster = async () => {
    if (!currentNovel) return;
    setIsGenerating(true);
    try {
      const res = await fetch(
        `${API_URL}/outlines/generate-master?novel_id=${currentNovel.id}`,
        { method: 'POST' }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || '生成失败');
      }
      toast.success('总纲生成完成');
      await loadOutline();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : '生成失败');
    } finally {
      setIsGenerating(false);
    }
  };

  // AI breakdown / expand
  const handleBreakdown = async (node: OutlineNode) => {
    setIsBreakingDown(true);
    try {
      const endpoint =
        node.level === 0
          ? `${API_URL}/outlines/${node.id}/breakdown`
          : `${API_URL}/outlines/${node.id}/expand`;
      const res = await fetch(endpoint, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || '拆解失败');
      }
      toast.success('拆解完成');
      await loadOutline();
      // Auto-expand the node after breakdown
      setExpandedIds((prev) => new Set(prev).add(node.id));
    } catch (e) {
      toast.error(e instanceof Error ? e.message : '拆解失败');
    } finally {
      setIsBreakingDown(false);
    }
  };

  // Add child dialog
  const openAddChildDialog = (parentId: string) => {
    setAddChildParentId(parentId);
    setNewChildTitle('');
    setNewChildContent('');
    setAddDialogOpen(true);
  };

  const handleAddChild = async () => {
    if (!addChildParentId || !newChildTitle.trim() || !currentNovel) return;
    try {
      const parentNode = (() => {
        const find = (nodes: OutlineNode[]): OutlineNode | null => {
          for (const n of nodes) {
            if (n.id === addChildParentId) return n;
            if (n.children) {
              const found = find(n.children);
              if (found) return found;
            }
          }
          return null;
        };
        return find(outlineNodes);
      })();

      const res = await fetch(`${API_URL}/outlines`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          novelId: currentNovel.id,
          parentId: addChildParentId,
          level: (parentNode?.level ?? -1) + 1,
          title: newChildTitle.trim(),
          content: newChildContent.trim(),
          chapterRange: '',
          status: 'draft',
        }),
      });
      if (res.ok) {
        toast.success('已添加子节点');
        setAddDialogOpen(false);
        await loadOutline();
        setExpandedIds((prev) => new Set(prev).add(addChildParentId));
      }
    } catch (e) {
      toast.error('添加失败');
    }
  };

  // Save detail
  const handleSave = async () => {
    if (!selectedNodeId) return;
    setIsSaving(true);
    try {
      const res = await fetch(`${API_URL}/outlines/${selectedNodeId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: editTitle,
          content: editContent,
          chapterRange: editChapterRange,
          status: editStatus,
        }),
      });
      if (res.ok) {
        updateOutlineNode(selectedNodeId, {
          title: editTitle,
          content: editContent,
          chapterRange: editChapterRange,
          status: editStatus,
        });
        toast.success('保存成功');
      }
    } catch (e) {
      toast.error('保存失败');
    } finally {
      setIsSaving(false);
    }
  };

  // Delete node
  const handleDelete = async () => {
    if (!selectedNodeId) return;
    if (!confirm('确定要删除该大纲节点及其所有子节点吗？')) return;
    setIsDeleting(true);
    try {
      const res = await fetch(`${API_URL}/outlines/${selectedNodeId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        deleteOutlineNode(selectedNodeId);
        setSelectedNodeId(null);
        toast.success('已删除');
      }
    } catch (e) {
      toast.error('删除失败');
    } finally {
      setIsDeleting(false);
    }
  };

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  if (!currentNovel) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        请先选择一部小说
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Left panel - tree view */}
      <div className="w-80 border-r flex flex-col">
        <div className="p-3 border-b space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold flex items-center gap-1.5 text-sm">
              <ListTree className="h-4 w-4" />
              大纲管理
            </h3>
            <Button
              size="sm"
              className="h-7 text-xs"
              onClick={handleGenerateMaster}
              disabled={isGenerating}
            >
              {isGenerating ? (
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
              ) : (
                <Sparkles className="h-3 w-3 mr-1" />
              )}
              AI 生成总纲
            </Button>
          </div>
        </div>

        <ScrollArea className="flex-1">
          <div className="p-2 space-y-0.5">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : outlineNodes.length === 0 ? (
              <div className="text-sm text-muted-foreground text-center py-8">
                暂无大纲，点击「AI 生成总纲」开始
              </div>
            ) : (
              outlineNodes.map((node) => (
                <TreeNode
                  key={node.id}
                  node={node}
                  selectedId={selectedNodeId}
                  expandedIds={expandedIds}
                  onSelect={setSelectedNodeId}
                  onToggle={toggleExpand}
                  onAddChild={openAddChildDialog}
                  onBreakdown={handleBreakdown}
                />
              ))
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Right panel - detail */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {!selectedNode ? (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            <div className="text-center">
              <ListTree className="h-12 w-12 mx-auto mb-2 opacity-30" />
              <p>选择大纲节点查看详情</p>
            </div>
          </div>
        ) : (
          <ScrollArea className="flex-1">
            <div className="p-4 space-y-4">
              {/* Title */}
              <div>
                <label className="text-sm font-medium">标题</label>
                <Input
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="mt-1"
                />
              </div>

              {/* Content */}
              <div>
                <label className="text-sm font-medium">内容</label>
                <Textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  rows={8}
                  className="mt-1"
                  placeholder="大纲节点详细内容..."
                />
              </div>

              {/* Chapter range */}
              <div>
                <label className="text-sm font-medium">章节范围</label>
                <Input
                  value={editChapterRange}
                  onChange={(e) => setEditChapterRange(e.target.value)}
                  className="mt-1"
                  placeholder="如：第1-10章"
                />
              </div>

              {/* Status */}
              <div>
                <label className="text-sm font-medium">状态</label>
                <div className="flex gap-2 mt-1">
                  {(['draft', 'active', 'completed'] as const).map((s) => (
                    <Button
                      key={s}
                      variant={editStatus === s ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => setEditStatus(s)}
                    >
                      {STATUS_CONFIG[s].label}
                    </Button>
                  ))}
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 pt-2 border-t">
                <Button onClick={handleSave} disabled={isSaving}>
                  {isSaving ? (
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  ) : null}
                  保存
                </Button>

                <Button
                  variant="outline"
                  onClick={() => handleBreakdown(selectedNode)}
                  disabled={isBreakingDown}
                >
                  {isBreakingDown ? (
                    <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                  ) : (
                    <Sparkles className="h-4 w-4 mr-1" />
                  )}
                  AI 拆解
                </Button>

                <div className="flex-1" />

                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleDelete}
                  disabled={isDeleting}
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  删除
                </Button>
              </div>
            </div>
          </ScrollArea>
        )}
      </div>

      {/* Add child dialog */}
      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>添加子节点</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">标题</label>
              <Input
                value={newChildTitle}
                onChange={(e) => setNewChildTitle(e.target.value)}
                placeholder="子节点标题"
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">内容（可选）</label>
              <Textarea
                value={newChildContent}
                onChange={(e) => setNewChildContent(e.target.value)}
                placeholder="描述该节点的内容..."
                rows={4}
                className="mt-1"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleAddChild} disabled={!newChildTitle.trim()}>
              添加
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
