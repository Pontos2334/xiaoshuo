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
    '正义': 'bg-blue-100 border-blue-400',
    '邪恶': 'bg-red-100 border-red-400',
    '中立': 'bg-gray-100 border-gray-400',
    'default': 'bg-indigo-100 border-indigo-400',
  };

  const bgColor = emotionColors[data.basicInfo?.身份] || emotionColors.default;

  return (
    <div className={`px-4 py-3 rounded-lg border-2 min-w-[120px] shadow-md ${bgColor}`}>
      <Handle type="target" position={Position.Top} className="!bg-transparent !border-0" />

      <div className="font-bold text-sm text-center mb-1">{data.name}</div>

      {data.basicInfo?.身份 && (
        <Badge variant="outline" className="text-xs block text-center mb-1">
          {data.basicInfo.身份}
        </Badge>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-transparent !border-0" />
    </div>
  );
}

export const CharacterNode = memo(CharacterNodeComponent);
