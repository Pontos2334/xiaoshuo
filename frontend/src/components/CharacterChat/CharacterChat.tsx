'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card } from '@/components/ui/card';
import { useCharacterStore } from '@/stores';
import { API_URL } from '@/lib/constants';
import { toast } from 'sonner';
import { Send, MessageSquare, Loader2, User } from 'lucide-react';
import { ChatMessage } from './ChatMessage';

interface CharacterChatProps {
  novelId: string;
  novelName: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  emotion?: string;
  timestamp?: string;
}

const emotionLabelMap: Record<string, string> = {
  happy: '开心 😊',
  sad: '难过 😢',
  angry: '生气 😠',
  surprised: '惊讶 😲',
  fear: '害怕 😨',
  neutral: '平静 😌',
};

export function CharacterChat({ novelId, novelName }: CharacterChatProps) {
  const { characters } = useCharacterStore();

  // Local state
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedCharacterId, setSelectedCharacterId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [currentEmotion, setCurrentEmotion] = useState<string>('neutral');
  const [inputValue, setInputValue] = useState('');

  const scrollEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollEndRef.current) {
      scrollEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Get the currently selected character object
  const selectedCharacter = characters.find((c) => c.id === selectedCharacterId) || null;

  // Create a new chat session
  const createSession = useCallback(
    async (characterId: string) => {
      try {
        setIsLoading(true);
        const response = await fetch(`${API_URL}/chat/session`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            novel_id: novelId,
            character_id: characterId,
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error: ${response.status}`);
        }

        const data = await response.json();

        if (data.success && data.data) {
          setSessionId(data.data.session_id);
          setSelectedCharacterId(characterId);
          setMessages([]);
          setCurrentEmotion('neutral');
          const characterName = data.data.character_name || characters.find((c) => c.id === characterId)?.name || '角色';
          toast.success(`已开始与 ${characterName} 的对话`);
        } else {
          throw new Error(data.error || '创建会话失败');
        }
      } catch (error) {
        console.error('Failed to create session:', error);
        toast.error('创建会话失败，请重试');
      } finally {
        setIsLoading(false);
      }
    },
    [characters, novelId]
  );

  // Load chat history for an existing session
  const loadHistory = useCallback(async (sid: string) => {
    try {
      const response = await fetch(`${API_URL}/chat/history/${sid}`);
      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }
      const data = await response.json();
      if (data.success && data.data && Array.isArray(data.data)) {
        const loadedMessages: Message[] = data.data.map(
          (msg: { role: string; content: string; emotion?: string; timestamp?: string }) => ({
            role: msg.role as 'user' | 'assistant',
            content: msg.content,
            emotion: msg.emotion,
            timestamp: msg.timestamp,
          })
        );
        setMessages(loadedMessages);
      }
    } catch (error) {
      console.error('Failed to load history:', error);
    }
  }, []);

  // Handle character selection
  const handleSelectCharacter = useCallback(
    async (characterId: string) => {
      if (characterId === selectedCharacterId && sessionId) return;

      // If there's an existing session, close it first
      if (sessionId) {
        try {
          await fetch(`${API_URL}/chat/session/${sessionId}`, { method: 'DELETE' });
        } catch {
          // Ignore deletion errors when switching
        }
      }

      await createSession(characterId);
    },
    [selectedCharacterId, sessionId, createSession]
  );

  // Send a message
  const handleSendMessage = useCallback(async () => {
    const trimmed = inputValue.trim();
    if (!trimmed || !sessionId || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: trimmed,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: trimmed,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }

      const data = await response.json();

      if (data.success && data.data) {
        const assistantMessage: Message = {
          role: 'assistant',
          content: data.data.response,
          emotion: data.data.emotion || 'neutral',
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
        if (data.data.emotion) {
          setCurrentEmotion(data.data.emotion);
        }
      } else {
        throw new Error(data.error || '发送消息失败');
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      toast.error('发送消息失败，请重试');
      setMessages((prev) => prev.slice(0, -1));
      setInputValue(trimmed);
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [inputValue, sessionId, isLoading]);

  // Handle keyboard input
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
      }
    },
    [handleSendMessage]
  );

  return (
    <div className="h-full flex gap-4">
      {/* Left panel: Character list (w-60 = 240px) */}
      <div className="w-60 border rounded-lg flex flex-col bg-background shrink-0">
        <div className="px-4 py-3 border-b">
          <h3 className="text-sm font-semibold">人物列表</h3>
        </div>
        <ScrollArea className="flex-1">
          <div className="p-2 space-y-1">
            {characters.length > 0 ? (
              characters.map((char) => {
                const isActive = selectedCharacterId === char.id;
                return (
                  <button
                    key={char.id}
                    onClick={() => handleSelectCharacter(char.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors cursor-pointer ${
                      isActive
                        ? 'bg-primary/10 text-primary border border-primary/20'
                        : 'hover:bg-muted text-foreground'
                    }`}
                  >
                    <div className="size-8 shrink-0">
                      <div
                        className={`size-full rounded-full flex items-center justify-center text-xs font-medium ${
                          isActive
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted text-muted-foreground'
                        }`}
                      >
                        {char.name.charAt(0)}
                      </div>
                    </div>
                    <span className="text-sm truncate">{char.name}</span>
                  </button>
                );
              })
            ) : (
              <div className="text-center py-8">
                <User className="h-8 w-8 mx-auto mb-2 text-muted-foreground opacity-40" />
                <p className="text-xs text-muted-foreground">暂无人物数据</p>
                <p className="text-xs text-muted-foreground mt-1">请先进行人物分析</p>
              </div>
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Right panel: Chat area (flex-1) */}
      <div className="flex-1 flex flex-col border rounded-lg bg-background min-w-0">
        {selectedCharacter && sessionId ? (
          <>
            {/* Header: character name + emotion badge */}
            <div className="flex items-center justify-between px-4 py-2.5 border-b">
              <div className="flex items-center gap-2">
                <MessageSquare className="h-4 w-4 text-primary" />
                <span className="font-medium text-sm">{selectedCharacter.name}</span>
                {currentEmotion && emotionLabelMap[currentEmotion] && (
                  <Badge variant="secondary" className="text-xs">
                    {emotionLabelMap[currentEmotion]}
                  </Badge>
                )}
              </div>
              <span className="text-xs text-muted-foreground">{messages.length} 条消息</span>
            </div>

            {/* Message list */}
            <div className="flex-1 overflow-y-auto p-4">
              {messages.length > 0 ? (
                <div>
                  {messages.map((msg, index) => (
                    <ChatMessage
                      key={index}
                      role={msg.role}
                      content={msg.content}
                      emotion={msg.emotion}
                      characterName={msg.role === 'assistant' ? selectedCharacter.name : undefined}
                      timestamp={msg.timestamp}
                    />
                  ))}
                  {/* Loading indicator */}
                  {isLoading && (
                    <div className="flex justify-start mb-4">
                      <div className="bg-muted rounded-xl rounded-bl-sm px-4 py-3 text-sm text-muted-foreground flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span>正在思考...</span>
                      </div>
                    </div>
                  )}
                  {/* Scroll anchor */}
                  <div ref={scrollEndRef} />
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                  <div className="text-center">
                    <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-40" />
                    <p>开始与 {selectedCharacter.name} 对话吧</p>
                    <p className="text-xs mt-1">输入你想问的问题或想说的话</p>
                  </div>
                </div>
              )}
            </div>

            {/* Input area */}
            <div className="border-t p-3">
              <div className="flex items-center gap-2">
                <Input
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder={`对 ${selectedCharacter.name} 说些什么...`}
                  disabled={isLoading}
                  className="flex-1"
                />
                <Button
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim() || isLoading}
                  size="default"
                >
                  {isLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>
              <div className="mt-1">
                <span className="text-[10px] text-muted-foreground">
                  Enter 发送
                </span>
              </div>
            </div>
          </>
        ) : (
          /* Empty state when no character is selected */
          <div className="flex-1 flex items-center justify-center">
            <Card className="p-8 text-center max-w-md mx-auto border-dashed">
              <div className="space-y-3">
                <div className="mx-auto w-12 h-12 rounded-full bg-muted flex items-center justify-center">
                  <User className="h-6 w-6 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">
                    从左侧选择一个人物开始对话
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    选择人物后将创建对话会话，以人物的身份与你交流
                  </p>
                </div>
                {characters.length === 0 && (
                  <p className="text-xs text-destructive">
                    当前小说暂无人物数据，请先进行人物分析
                  </p>
                )}
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
