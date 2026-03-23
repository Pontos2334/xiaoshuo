'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useInspirationStore, useCharacterStore, usePlotStore } from '@/stores';
import { Sparkles, MessageSquare, User, GitBranch, Heart, Loader2 } from 'lucide-react';

interface InspirationPanelProps {
  onGenerateInspiration?: (type: string, targetId?: string, context?: string) => Promise<void>;
  isAnalyzing?: boolean;
}

export function InspirationPanel({ onGenerateInspiration, isAnalyzing }: InspirationPanelProps) {
  const { inspirations } = useInspirationStore();
  const { characters } = useCharacterStore();
  const { plotNodes } = usePlotStore();
  const [activeType, setActiveType] = useState('plot');
  const [selectedTargetId, setSelectedTargetId] = useState<string | null>(null);
  const [customContext, setCustomContext] = useState('');

  const handleGenerate = async () => {
    if (onGenerateInspiration) {
      await onGenerateInspiration(activeType, selectedTargetId || undefined, customContext || undefined);
    }
  };

  const typeOptions = [
    { value: 'plot', label: '情节灵感', icon: GitBranch, description: '为指定情节提供写作灵感' },
    { value: 'continue', label: '情节延续', icon: MessageSquare, description: '后续情节发展建议' },
    { value: 'character', label: '角色发展', icon: User, description: '角色成长弧线建议' },
    { value: 'emotion', label: '情绪渲染', icon: Heart, description: '如何增强情绪表达' },
  ];

  const getTypeLabel = (type: string) => {
    const option = typeOptions.find((o) => o.value === type);
    return option?.label || type;
  };

  return (
    <div className="h-full flex flex-col">
      <Card className="flex-1 flex flex-col">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-yellow-500" />
            灵感提示
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col space-y-4">
          {/* 灵感类型选择 */}
          <Tabs value={activeType} onValueChange={setActiveType}>
            <TabsList className="grid grid-cols-4">
              {typeOptions.map((option) => (
                <TabsTrigger key={option.value} value={option.value}>
                  <option.icon className="h-4 w-4 mr-1" />
                  {option.label}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>

          {/* 目标选择 */}
          <div className="space-y-2">
            <label className="text-sm font-medium">选择目标</label>
            {activeType === 'plot' || activeType === 'emotion' ? (
              <Select value={selectedTargetId} onValueChange={setSelectedTargetId}>
                <SelectTrigger>
                  <SelectValue placeholder="选择情节节点" />
                </SelectTrigger>
                <SelectContent>
                  {plotNodes.map((node) => (
                    <SelectItem key={node.id} value={node.id}>
                      第{node.chapter}章 - {node.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : activeType === 'character' ? (
              <Select value={selectedTargetId} onValueChange={setSelectedTargetId}>
                <SelectTrigger>
                  <SelectValue placeholder="选择角色" />
                </SelectTrigger>
                <SelectContent>
                  {characters.map((char) => (
                    <SelectItem key={char.id} value={char.id}>
                      {char.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <div className="text-sm text-muted-foreground">
                基于当前所有人物和情节生成后续发展建议
              </div>
            )}
          </div>

          {/* 自定义上下文 */}
          <div className="space-y-2">
            <label className="text-sm font-medium">补充说明（可选）</label>
            <Textarea
              value={customContext}
              onChange={(e) => setCustomContext(e.target.value)}
              placeholder="输入你希望灵感侧重的方向..."
              rows={3}
            />
          </div>

          {/* 生成按钮 */}
          <Button
            onClick={handleGenerate}
            disabled={isAnalyzing || (!selectedTargetId && activeType !== 'continue')}
            className="w-full"
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                生成中...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4 mr-2" />
                生成灵感
              </>
            )}
          </Button>

          {/* 灵感历史 */}
          <div className="flex-1 min-h-0">
            <h3 className="text-sm font-medium mb-2">灵感记录</h3>
            <ScrollArea className="h-[200px] rounded-md border p-2">
              {inspirations.length > 0 ? (
                <div className="space-y-3">
                  {inspirations.map((inspiration) => (
                    <div key={inspiration.id} className="p-3 rounded-lg bg-muted/50">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="outline">{getTypeLabel(inspiration.type)}</Badge>
                        <span className="text-xs text-muted-foreground">
                          {new Date(inspiration.createdAt).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-sm whitespace-pre-wrap">{inspiration.content}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-muted-foreground py-8">
                  点击&quot;生成灵感&quot;获取写作建议
                </div>
              )}
            </ScrollArea>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
