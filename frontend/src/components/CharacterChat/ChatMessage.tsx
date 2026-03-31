'use client';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import ReactMarkdown from 'react-markdown';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  emotion?: string;
  characterName?: string;
  timestamp?: string;
}

const emotionMap: Record<string, { label: string; emoji: string }> = {
  happy: { label: '开心', emoji: '😊' },
  sad: { label: '难过', emoji: '😢' },
  angry: { label: '生气', emoji: '😠' },
  surprised: { label: '惊讶', emoji: '😲' },
  fear: { label: '害怕', emoji: '😨' },
  neutral: { label: '平静', emoji: '😌' },
};

export function ChatMessage({ role, content, emotion, characterName, timestamp }: ChatMessageProps) {
  const isUser = role === 'user';
  const emotionInfo = emotion ? emotionMap[emotion] : null;

  return (
    <div className={cn('flex w-full mb-4', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed break-words shadow-sm',
          isUser
            ? 'bg-primary text-primary-foreground rounded-br-md'
            : 'bg-card text-card-foreground border rounded-bl-md'
        )}
      >
        {/* Character name and emotion badge for assistant messages */}
        {!isUser && (characterName || emotionInfo) && (
          <div className="flex items-center gap-2 mb-1.5">
            {characterName && (
              <span className="text-xs font-medium text-primary/70">
                {characterName}
              </span>
            )}
            {emotionInfo && (
              <Badge variant="secondary" className="text-[10px] gap-1 py-0">
                {emotionInfo.emoji} {emotionInfo.label}
              </Badge>
            )}
          </div>
        )}

        {/* Message content */}
        {isUser ? (
          <div className="whitespace-pre-wrap">{content}</div>
        ) : (
          <div className="prose prose-sm max-w-none dark:prose-invert">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        )}

        {/* Timestamp */}
        {timestamp && (
          <div
            className={cn(
              'text-[10px] mt-1.5',
              isUser ? 'text-primary-foreground/50' : 'text-muted-foreground/60'
            )}
          >
            {new Date(timestamp).toLocaleTimeString('zh-CN', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </div>
        )}
      </div>
    </div>
  );
}
