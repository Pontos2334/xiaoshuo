'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useInspirationStore, useCharacterStore, usePlotStore } from '@/stores';
import { Sparkles, MessageSquare, User, GitBranch, Heart, Loader2, Users, BookOpen } from 'lucide-react';

interface InspirationPanelProps {
  onGenerateInspiration?: (type: string, targetIds?: string[], context?: string) => Promise<void>;
  isAnalyzing?: boolean;
}

export function InspirationPanel({ onGenerateInspiration, isAnalyzing }: InspirationPanelProps) {
  const { inspirations } = useInspirationStore();
  const { characters } = useCharacterStore();
  const { plotNodes } = usePlotStore();
  const [activeType, setActiveType] = useState('scene');
  const [selectedCharacters, setSelectedCharacters] = useState<string[]>([]);
  const [selectedPlots, setSelectedPlots] = useState<string[]>([]);
  const [customContext, setCustomContext] = useState('');

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

  const typeOptions = [
    { value: 'scene', label: '场景', icon: BookOpen },
    { value: 'plot', label: '情节', icon: GitBranch },
    { value: 'continue', label: '延续', icon: MessageSquare },
    { value: 'character', label: '角色', icon: User },
    { value: 'emotion', label: '情绪', icon: Heart },
  ];

  const getTypeLabel = (type: string) => typeOptions.find((o) => o.value === type)?.label || type;

  const canGenerate = !isAnalyzing && (activeType === 'continue' || selectedCharacters.length > 0 || selectedPlots.length > 0);

  return (
    <div className="space-y-4">
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
              {characters.length > 0 ? characters.map((char) => (
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
        <CardHeader className="py-2 px-3">
          <CardTitle className="text-sm">灵感记录</CardTitle>
        </CardHeader>
        <CardContent className="max-h-64 overflow-auto p-0">
          <div className="px-3 pb-3 space-y-2">
            {inspirations.length > 0 ? inspirations.map((insp) => (
              <div key={insp.id} className="p-2 rounded bg-muted/50">
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant="outline" className="text-[10px]">{getTypeLabel(insp.type)}</Badge>
                  <span className="text-[10px] text-muted-foreground">{new Date(insp.createdAt).toLocaleString()}</span>
                </div>
                <p className="text-xs whitespace-pre-wrap">{insp.content}</p>
              </div>
            )) : (
              <div className="text-center text-muted-foreground py-4 text-xs">选择人物和情节，生成灵感</div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
