'use client';

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Character } from '@/types';
import { Badge } from '@/components/ui/badge';

interface CharacterNodeProps {
  data: Character;
}

function CharacterNodeComponent({ data }: CharacterNodeProps) {
  const emotionColors: Record<string, string> = {
    '正义': 'bg-blue-50/90 border-blue-200/80 shadow-sm shadow-blue-100/40',
    '邪恶': 'bg-red-50/90 border-red-200/80 shadow-sm shadow-red-100/40',
    '中立': 'bg-slate-50/90 border-slate-200/80 shadow-sm shadow-slate-100/40',
    'default': 'bg-primary/[0.03] border-primary/15 shadow-sm shadow-primary/5',
  };

  const bgColor = emotionColors[data.basicInfo?.身份] || emotionColors.default;

  return (
    <div className={`px-4 py-3 rounded-xl border min-w-[120px] backdrop-blur-sm transition-shadow hover:shadow-md ${bgColor}`}>
      <Handle type="target" position={Position.Top} className="!bg-transparent !border-0" />

      <div className="font-semibold text-sm text-center mb-1">{data.name}</div>

      {data.basicInfo?.身份 && (
        <Badge variant="outline" className="text-[10px] block text-center mx-auto">
          {data.basicInfo.身份}
        </Badge>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-transparent !border-0" />
    </div>
  );
}

export const CharacterNode = memo(CharacterNodeComponent);
