'use client';

import { useState, useMemo, useEffect, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Search, Users } from 'lucide-react';
import { useCharacterStore, useUIStore } from '@/stores';
import type { Character } from '@/types';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface CharacterQuickSearchProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CharacterQuickSearch({ open, onOpenChange }: CharacterQuickSearchProps) {
  const { characters } = useCharacterStore();
  const { setActiveTab } = useUIStore();
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-focus the search input when the dialog opens
  useEffect(() => {
    if (open) {
      // Small delay so the DOM is ready
      const timer = setTimeout(() => {
        inputRef.current?.focus();
      }, 50);
      return () => clearTimeout(timer);
    } else {
      setQuery('');
    }
  }, [open]);

  // Fuzzy local search
  const results = useMemo<Character[]>(() => {
    if (!query.trim()) return [];
    const q = query.trim().toLowerCase();
    const matched = characters.filter((c) => {
      const nameMatch = c.name.toLowerCase().includes(q);
      const aliasMatch = c.aliases?.some((a) => a.toLowerCase().includes(q));
      const summaryMatch = (c.storySummary || '').toLowerCase().includes(q);
      return nameMatch || aliasMatch || summaryMatch;
    });
    return matched.slice(0, 10);
  }, [query, characters]);

  const handleSelect = () => {
    setActiveTab('characters');
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            人物快速搜索
          </DialogTitle>
        </DialogHeader>

        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索人物名称、别名或简介..."
            className="pl-8"
          />
        </div>

        <ScrollArea className="max-h-[340px]">
          {query.trim() && results.length === 0 && (
            <div className="py-6 text-center text-sm text-muted-foreground">
              未找到匹配的人物
            </div>
          )}

          <div className="space-y-1.5">
            {results.map((char) => (
              <div
                key={char.id}
                className="flex items-start gap-3 p-2.5 rounded-md hover:bg-muted cursor-pointer transition-colors"
                onClick={handleSelect}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{char.name}</span>
                    {char.aliases && char.aliases.length > 0 && (
                      <span className="text-xs text-muted-foreground truncate">
                        {char.aliases.join(', ')}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2 mt-0.5">
                    {(() => {
                      const identity = char.basicInfo?.identity || char.basicInfo?.身份;
                      return identity ? (
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                          {String(identity)}
                        </Badge>
                      ) : null;
                    })()}
                    {char.firstAppear && (
                      <span className="text-xs text-muted-foreground">
                        首次出场：{char.firstAppear}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
