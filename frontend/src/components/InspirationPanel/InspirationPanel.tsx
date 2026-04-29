'use client';

import { useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useInspirationStore, useCharacterStore, usePlotStore } from '@/stores';
import {
  Sparkles, MessageSquare, User, GitBranch, Heart, Loader2, Users, BookOpen,
  Copy, Check, Save, Eye, Edit3, Trash2, ChevronDown, ChevronUp
} from 'lucide-react';
import { toast } from 'sonner';

interface InspirationPanelProps {
  onGenerateInspiration?: (type: string, targetIds?: string[], context?: string) => Promise<void>;
  isAnalyzing?: boolean;
}

// Markdown 样式
const markdownStyles = `
  .markdown-preview h1 { font-size: 1.5rem; font-weight: bold; margin-bottom: 0.5rem; }
  .markdown-preview h2 { font-size: 1.25rem; font-weight: bold; margin-bottom: 0.5rem; }
  .markdown-preview h3 { font-size: 1.1rem; font-weight: bold; margin-bottom: 0.5rem; }
  .markdown-preview p { margin-bottom: 0.5rem; line-height: 1.6; }
  .markdown-preview ul, .markdown-preview ol { padding-left: 1.5rem; margin-bottom: 0.5rem; }
  .markdown-preview li { margin-bottom: 0.25rem; }
  .markdown-preview code { background: rgba(0,0,0,0.1); padding: 0.125rem 0.25rem; border-radius: 0.25rem; font-size: 0.875em; }
  .markdown-preview pre { background: rgba(0,0,0,0.1); padding: 0.5rem; border-radius: 0.375rem; overflow-x: auto; margin-bottom: 0.5rem; }
  .markdown-preview pre code { background: transparent; padding: 0; }
  .markdown-preview blockquote { border-left: 3px solid #6366f1; padding-left: 0.75rem; margin: 0.5rem 0; color: #6b7280; }
  .markdown-preview a { color: #6366f1; text-decoration: underline; }
  .markdown-preview strong { font-weight: 600; }
  .markdown-preview em { font-style: italic; }
  .markdown-preview hr { border-color: #e5e7eb; margin: 0.75rem 0; }
`;

export function InspirationPanel({ onGenerateInspiration, isAnalyzing }: InspirationPanelProps) {
  const { inspirations, addInspiration, updateInspiration, deleteInspiration } = useInspirationStore();
  const { characters } = useCharacterStore();
  const { plotNodes } = usePlotStore();
  const [activeType, setActiveType] = useState('scene');
  const [selectedCharacters, setSelectedCharacters] = useState<string[]>([]);
  const [selectedPlots, setSelectedPlots] = useState<string[]>([]);
  const [customContext, setCustomContext] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<Record<string, 'preview' | 'edit'>>({});
  const [editContent, setEditContent] = useState<Record<string, string>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const toggleCharacter = (id: string) => {
    setSelectedCharacters((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    );
  };

  const togglePlot = (id: string) => {
    setSelectedPlots((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  };

  const toggleAllCharacters = () => {
    setSelectedCharacters(selectedCharacters.length === characters.length ? [] : characters.map((c) => c.id));
  };

  const toggleAllPlots = () => {
    setSelectedPlots(selectedPlots.length === plotNodes.length ? [] : plotNodes.map((p) => p.id));
  };

  const handleGenerate = async () => {
    if (onGenerateInspiration) {
      const targetIds = [...selectedCharacters, ...selectedPlots];
      await onGenerateInspiration(activeType, targetIds.length > 0 ? targetIds : undefined, customContext || undefined);
    }
  };

  // 复制到剪贴板
  const handleCopy = useCallback(async (id: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedId(id);
      toast.success('已复制到剪贴板');
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      toast.error('复制失败');
    }
  }, []);

  // 保存为文件
  const handleSave = useCallback((id: string, content: string, type: string) => {
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `灵感_${type}_${new Date().toISOString().slice(0, 10)}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success('已保存为文件');
  }, []);

  // 删除灵感
  const handleDelete = useCallback((id: string) => {
    deleteInspiration(id);
    toast.success('已删除');
  }, [deleteInspiration]);

  // 切换视图模式
  const toggleViewMode = useCallback((id: string) => {
    setViewMode(prev => ({
      ...prev,
      [id]: prev[id] === 'edit' ? 'preview' : 'edit'
    }));
    // 同步编辑内容
    const insp = inspirations.find(i => i.id === id);
    if (insp && !editContent[id]) {
      setEditContent(prev => ({ ...prev, [id]: insp.content }));
    }
  }, [inspirations, editContent]);

  // 更新编辑内容
  const handleEditChange = useCallback((id: string, content: string) => {
    setEditContent(prev => ({ ...prev, [id]: content }));
  }, []);

  // 保存编辑
  const handleSaveEdit = useCallback((id: string) => {
    const content = editContent[id];
    if (content) {
      updateInspiration(id, { content });
      toast.success('已保存修改');
    }
    setViewMode(prev => ({ ...prev, [id]: 'preview' }));
  }, [editContent, updateInspiration]);

  const typeOptions = [
    { value: 'scene', label: '场景', icon: BookOpen },
    { value: 'plot', label: '情节', icon: GitBranch },
    { value: 'continue', label: '延续', icon: MessageSquare },
    { value: 'character', label: '角色', icon: User },
    { value: 'emotion', label: '情绪', icon: Heart },
  ];

  const getTypeLabel = (type: string) => typeOptions.find((o) => o.value === type)?.label || type;
  const getTypeIcon = (type: string) => typeOptions.find((o) => o.value === type)?.icon || Sparkles;

  const canGenerate = !isAnalyzing && (activeType === 'continue' || selectedCharacters.length > 0 || selectedPlots.length > 0);

  return (
    <div className="space-y-4">
      {/* Markdown 样式 */}
      <style>{markdownStyles}</style>

      {/* 灵感类型 */}
      <Tabs value={activeType} onValueChange={setActiveType}>
        <TabsList className="grid grid-cols-5 h-9">
          {typeOptions.map((opt) => (
            <TabsTrigger key={opt.value} value={opt.value} className="text-xs">
              <opt.icon className="h-3.5 w-3.5 mr-1" />
              {opt.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {/* 选择区域 */}
      <div className="grid grid-cols-2 gap-4">
        {/* 人物 */}
        <Card>
          <CardHeader className="py-2 px-3 flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm flex items-center gap-1.5">
              <Users className="h-4 w-4" /> 人物
            </CardTitle>
            <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={toggleAllCharacters}>
              {selectedCharacters.length === characters.length ? '取消全选' : '全选'}
            </Button>
          </CardHeader>
          <CardContent className="max-h-48 overflow-auto p-0">
            <div className="px-3 pb-3 space-y-1">
              {characters.length > 0 ? characters.filter(c => c.id).map((char) => (
                <label key={char.id} className="flex items-center gap-2 p-1.5 rounded hover:bg-muted cursor-pointer">
                  <Checkbox checked={selectedCharacters.includes(char.id)} onCheckedChange={() => toggleCharacter(char.id)} className="h-4 w-4" />
                  <span className="text-sm truncate flex-1">{char.name}</span>
                  {char.basicInfo?.身份 && <Badge variant="outline" className="text-[10px]">{char.basicInfo.身份}</Badge>}
                </label>
              )) : <div className="text-xs text-muted-foreground text-center py-4">暂无人物</div>}
            </div>
          </CardContent>
        </Card>

        {/* 情节 */}
        <Card>
          <CardHeader className="py-2 px-3 flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm flex items-center gap-1.5">
              <GitBranch className="h-4 w-4" /> 情节
            </CardTitle>
            <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={toggleAllPlots}>
              {selectedPlots.length === plotNodes.length ? '取消全选' : '全选'}
            </Button>
          </CardHeader>
          <CardContent className="max-h-48 overflow-auto p-0">
            <div className="px-3 pb-3 space-y-1">
              {plotNodes.length > 0 ? plotNodes.map((plot) => (
                <label key={plot.id} className="flex items-center gap-2 p-1.5 rounded hover:bg-muted cursor-pointer">
                  <Checkbox checked={selectedPlots.includes(plot.id)} onCheckedChange={() => togglePlot(plot.id)} className="h-4 w-4" />
                  <span className="text-sm truncate flex-1">{plot.title}</span>
                  <Badge variant="outline" className="text-[10px]">第{plot.chapter}章</Badge>
                </label>
              )) : <div className="text-xs text-muted-foreground text-center py-4">暂无情节</div>}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 补充说明 */}
      <div>
        <label className="text-sm font-medium mb-1.5 block">补充说明</label>
        <Textarea value={customContext} onChange={(e) => setCustomContext(e.target.value)} placeholder="描述你想要的灵感方向..." rows={2} className="text-sm" />
      </div>

      {/* 生成按钮 */}
      <Button onClick={handleGenerate} disabled={!canGenerate} className="w-full">
        {isAnalyzing ? (
          <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> 生成中...</>
        ) : (
          <><Sparkles className="h-4 w-4 mr-2" /> 生成灵感</>
        )}
      </Button>

      {/* 灵感记录 */}
      <Card>
        <CardHeader className="py-2 px-3 flex-row items-center justify-between">
          <CardTitle className="text-sm">灵感记录 ({inspirations.length})</CardTitle>
          {inspirations.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-xs"
              onClick={() => {
                const allContent = inspirations.map(i => `## ${getTypeLabel(i.type)}\n\n${i.content}`).join('\n\n---\n\n');
                handleSave('all', allContent, '全部');
              }}
            >
              <Save className="h-3 w-3 mr-1" /> 导出全部
            </Button>
          )}
        </CardHeader>
        <CardContent className="max-h-96 overflow-auto p-0">
          <div className="px-3 pb-3 space-y-2">
            {inspirations.length > 0 ? [...inspirations].reverse().map((insp) => {
              const isExpanded = expandedId === insp.id;
              const isEditing = viewMode[insp.id] === 'edit';
              const TypeIcon = getTypeIcon(insp.type);

              return (
                <div key={insp.id} className="border rounded-lg overflow-hidden">
                  {/* 头部 */}
                  <div
                    className="flex items-center justify-between p-2 bg-muted/30 cursor-pointer hover:bg-muted/50"
                    onClick={() => setExpandedId(isExpanded ? null : insp.id)}
                  >
                    <div className="flex items-center gap-2">
                      <TypeIcon className="h-3.5 w-3.5 text-muted-foreground" />
                      <Badge variant="outline" className="text-[10px]">{getTypeLabel(insp.type)}</Badge>
                      <span className="text-[10px] text-muted-foreground">
                        {new Date(insp.createdAt).toLocaleString()}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      {isExpanded && (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0"
                            onClick={(e) => { e.stopPropagation(); toggleViewMode(insp.id); }}
                            title={isEditing ? '预览' : '编辑'}
                          >
                            {isEditing ? <Eye className="h-3 w-3" /> : <Edit3 className="h-3 w-3" />}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0"
                            onClick={(e) => { e.stopPropagation(); handleCopy(insp.id, isEditing ? (editContent[insp.id] || insp.content) : insp.content); }}
                            title="复制"
                          >
                            {copiedId === insp.id ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3" />}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0"
                            onClick={(e) => { e.stopPropagation(); handleSave(insp.id, isEditing ? (editContent[insp.id] || insp.content) : insp.content, getTypeLabel(insp.type)); }}
                            title="保存"
                          >
                            <Save className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-6 w-6 p-0 text-destructive hover:text-destructive"
                            onClick={(e) => { e.stopPropagation(); handleDelete(insp.id); }}
                            title="删除"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </>
                      )}
                      {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </div>
                  </div>

                  {/* 内容区域 */}
                  {isExpanded && (
                    <div className="p-3 border-t">
                      {isEditing ? (
                        <div className="space-y-2">
                          <Textarea
                            value={editContent[insp.id] || insp.content}
                            onChange={(e) => handleEditChange(insp.id, e.target.value)}
                            rows={8}
                            className="text-sm font-mono"
                          />
                          <div className="flex justify-end gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setViewMode(prev => ({ ...prev, [insp.id]: 'preview' }));
                                setEditContent(prev => ({ ...prev, [insp.id]: insp.content }));
                              }}
                            >
                              取消
                            </Button>
                            <Button size="sm" onClick={() => handleSaveEdit(insp.id)}>
                              保存修改
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div className="markdown-preview text-sm">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {insp.content}
                          </ReactMarkdown>
                        </div>
                      )}
                    </div>
                  )}

                  {/* 收起时的预览 */}
                  {!isExpanded && (
                    <div className="px-3 py-2 text-xs text-muted-foreground line-clamp-2">
                      {insp.content.slice(0, 100)}...
                    </div>
                  )}
                </div>
              );
            }) : (
              <div className="text-center text-muted-foreground py-8 text-xs">
                选择人物和情节，点击生成灵感
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
