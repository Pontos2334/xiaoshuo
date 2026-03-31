'use client';

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { PlotNode as PlotNodeType } from '@/types';
import { Badge } from '@/components/ui/badge';

interface PlotNodeProps {
  data: PlotNodeType;
}

function PlotNode({ data }: PlotNodeProps) {
  const emotionColors: Record<string, string> = {
    '紧张': 'bg-red-50/90 border-red-200/80 shadow-sm shadow-red-100/40',
    '温馨': 'bg-pink-50/90 border-pink-200/80 shadow-sm shadow-pink-100/40',
    '悲伤': 'bg-blue-50/90 border-blue-200/80 shadow-sm shadow-blue-100/40',
    '欢乐': 'bg-amber-50/90 border-amber-200/80 shadow-sm shadow-amber-100/40',
    '愤怒': 'bg-orange-50/90 border-orange-200/80 shadow-sm shadow-orange-100/40',
    '平静': 'bg-emerald-50/90 border-emerald-200/80 shadow-sm shadow-emerald-100/40',
  };

  const bgColor = emotionColors[data.emotion] || 'bg-primary/[0.03] border-primary/15 shadow-sm shadow-primary/5';

  return (
    <div className={`px-4 py-3 rounded-xl border min-w-[150px] backdrop-blur-sm transition-shadow hover:shadow-md ${bgColor}`}>
      <Handle type="target" position={Position.Left} className="!bg-transparent !border-0" />

      <div className="font-semibold text-sm mb-1">{data.title}</div>
      <div className="text-xs text-muted-foreground/70 mb-1">第{data.chapter}章</div>

      {data.emotion && (
        <Badge variant="outline" className="text-[10px]">
          {data.emotion}
        </Badge>
      )}

      <Handle type="source" position={Position.Right} className="!bg-transparent !border-0" />
    </div>
  );
}

export const PlotNodeComponent = memo(PlotNode);
