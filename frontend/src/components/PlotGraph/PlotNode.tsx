'use client';

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { PlotNode } from '@/types';
import { Badge } from '@/components/ui/badge';

interface PlotNodeProps {
  data: PlotNode;
}

function PlotNode({ data }: PlotNodeProps) {
  const emotionColors: Record<string, string> = {
    '紧张': 'bg-red-100 border-red-400',
    '温馨': 'bg-pink-100 border-pink-400',
    '悲伤': 'bg-blue-100 border-blue-400',
    '欢乐': 'bg-yellow-100 border-yellow-400',
    '愤怒': 'bg-orange-100 border-orange-400',
    '平静': 'bg-green-100 border-green-400',
  };

  const bgColor = emotionColors[data.emotion] || 'bg-gray-100 border-gray-400';

  return (
    <div className={`px-4 py-3 rounded-lg border-2 min-w-[150px] shadow-md ${bgColor}`}>
      <Handle type="target" position={Position.Left} className="!bg-transparent !border-0" />

      <div className="font-bold text-sm mb-1">{data.title}</div>
      <div className="text-xs text-muted-foreground mb-1">第{data.chapter}章</div>

      {data.emotion && (
        <Badge variant="outline" className="text-xs">
          {data.emotion}
        </Badge>
      )}

      <Handle type="source" position={Position.Right} className="!bg-transparent !border-0" />
    </div>
  );
}

export const PlotNodeComponent = memo(PlotNode);
