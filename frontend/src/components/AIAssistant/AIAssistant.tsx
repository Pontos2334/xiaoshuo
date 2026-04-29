'use client';

import { useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { API_URL } from '@/lib/constants';
import { toast } from 'sonner';
import {
  Sparkles,
  Activity,
  PenTool,
  List,
  Zap,
  Loader2,
  Wand2,
  Lightbulb,
  Flame,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface AIAssistantProps {
  novelId: string;
  novelName: string;
}

// ---------------------------------------------------------------------------
// Tab config
// ---------------------------------------------------------------------------

interface TabConfig {
  key: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  endpoint: string;
  hasContext: boolean;
  contextPlaceholder: string;
  resultKey: string;
}

const TABS: TabConfig[] = [
  {
    key: 'predict',
    label: '情节预测',
    icon: Sparkles,
    endpoint: '/assistant/predict',
    hasContext: true,
    contextPlaceholder: '补充上下文信息，帮助 AI 更准确地预测...',
    resultKey: 'predictions',
  },
  {
    key: 'pace',
    label: '节奏分析',
    icon: Activity,
    endpoint: '/assistant/pace',
    hasContext: false,
    contextPlaceholder: '',
    resultKey: 'analysis',
  },
  {
    key: 'advice',
    label: '写作建议',
    icon: PenTool,
    endpoint: '/assistant/advice',
    hasContext: true,
    contextPlaceholder: '描述你想获取哪方面的写作建议...',
    resultKey: 'advice',
  },
  {
    key: 'outline',
    label: '大纲生成',
    icon: List,
    endpoint: '/assistant/outline',
    hasContext: true,
    contextPlaceholder: '描述故事前提或大纲方向...',
    resultKey: 'outline',
  },
  {
    key: 'twist',
    label: '情节转折',
    icon: Zap,
    endpoint: '/assistant/twist',
    hasContext: true,
    contextPlaceholder: '描述当前的情节上下文...',
    resultKey: 'twist',
  },
  {
    key: 'writers-block',
    label: '卡文急救',
    icon: Lightbulb,
    endpoint: '/assistant/writers-block-rescue',
    hasContext: true,
    contextPlaceholder: '描述你当前的写作困境...',
    resultKey: 'suggestions',
  },
  {
    key: 'satisfaction',
    label: '爽点设计',
    icon: Flame,
    endpoint: '/assistant/satisfaction-designer',
    hasContext: true,
    contextPlaceholder: '描述你想要的爽点场景...',
    resultKey: 'scenario',
  },
];

// ---------------------------------------------------------------------------
// Markdown styles
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Helper: extract result string from API response
// ---------------------------------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function extractResult(data: any, resultKey: string): string {
  // Response may wrap content in { success: true, data: { <key>: "..." } }
  // or return { success: true, <key>: "..." }
  // or data itself could be the string
  if (typeof data === 'string') return data;

  const inner = data.data ?? data;

  if (typeof inner === 'string') return inner;
  if (typeof inner[resultKey] === 'string') return inner[resultKey];
  // If the value is an object, stringify it nicely
  if (inner[resultKey] !== undefined) return JSON.stringify(inner[resultKey], null, 2);

  // Fallback: try to find any string value in the response
  for (const value of Object.values(inner)) {
    if (typeof value === 'string' && value.length > 0) return value;
  }

  return JSON.stringify(data, null, 2);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AIAssistant({ novelId, novelName }: AIAssistantProps) {
  const [loadingTab, setLoadingTab] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, string>>({});
  const [contexts, setContexts] = useState<Record<string, string>>({});
  const [satisfactionType, setSatisfactionType] = useState<string>('打脸');

  // -------------------------------------------------------------------------
  // Generic generate handler
  // -------------------------------------------------------------------------

  const handleGenerate = useCallback(
    async (tab: TabConfig) => {
      setLoadingTab(tab.key);
      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const body: any = { novel_id: novelId };
        if (tab.hasContext && contexts[tab.key]?.trim()) {
          body.context = contexts[tab.key].trim();
        }
        if (tab.key === 'satisfaction') {
          body.type = satisfactionType;
        }

        const res = await fetch(`${API_URL}${tab.endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });

        if (!res.ok) {
          const errorData = await res.json().catch(() => null);
          throw new Error(errorData?.detail || `请求失败 (${res.status})`);
        }

        const data = await res.json();
        const text = extractResult(data, tab.resultKey);
        setResults((prev) => ({ ...prev, [tab.key]: text }));
        toast.success(`${tab.label}生成完成`);
      } catch (err) {
        toast.error(err instanceof Error ? err.message : `${tab.label}生成失败`);
      } finally {
        setLoadingTab(null);
      }
    },
    [novelId, contexts, satisfactionType],
  );

  // =========================================================================
  // JSX
  // =========================================================================

  return (
    <div className="h-full">
      <style>{markdownStyles}</style>

      <Card className="h-full flex flex-col">
        {/* Header */}
        <CardHeader className="shrink-0 pb-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <Wand2 className="h-5 w-5" />
            AI 智能助手
          </CardTitle>
          <p className="text-xs text-muted-foreground">{novelName}</p>
        </CardHeader>

        <CardContent className="flex-1 flex flex-col overflow-hidden pt-0">
          <Tabs defaultValue="predict" className="flex-1 flex flex-col overflow-hidden">
            {/* Tab bar */}
            <TabsList className="grid grid-cols-7 w-full shrink-0">
              {TABS.map((tab) => {
                const Icon = tab.icon;
                return (
                  <TabsTrigger key={tab.key} value={tab.key} className="text-xs">
                    <Icon className="h-3.5 w-3.5 mr-1" />
                    {tab.label}
                  </TabsTrigger>
                );
              })}
            </TabsList>

            {/* Tab panels */}
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const isLoading = loadingTab === tab.key;
              const result = results[tab.key];
              const context = contexts[tab.key] ?? '';

              return (
                <TabsContent
                  key={tab.key}
                  value={tab.key}
                  className="flex-1 flex flex-col gap-3 mt-3 overflow-hidden"
                >
                  {/* Context input (optional) */}
                  {tab.hasContext && (
                    <Textarea
                      value={context}
                      onChange={(e) =>
                        setContexts((prev) => ({ ...prev, [tab.key]: e.target.value }))
                      }
                      placeholder={tab.contextPlaceholder}
                      rows={2}
                      className="text-sm shrink-0"
                    />
                  )}

                  {/* Satisfaction type selector */}
                  {tab.key === 'satisfaction' && (
                    <div className="flex gap-2 shrink-0">
                      {['打脸', '逆袭', '装逼', '反转'].map((t) => (
                        <Button
                          key={t}
                          variant={satisfactionType === t ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => setSatisfactionType(t)}
                          className="flex-1"
                        >
                          {t}
                        </Button>
                      ))}
                    </div>
                  )}

                  {/* Generate button */}
                  <div className="flex justify-end shrink-0">
                    <Button
                      onClick={() => handleGenerate(tab)}
                      disabled={isLoading}
                      className="w-full sm:w-auto"
                    >
                      {isLoading ? (
                        <>
                          <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                          正在生成...
                        </>
                      ) : (
                        <>
                          <Icon className="h-4 w-4 mr-2" />
                          {tab.label}
                        </>
                      )}
                    </Button>
                  </div>

                  {/* Result area */}
                  <ScrollArea className="flex-1 max-h-[calc(100vh-320px)]">
                    {isLoading && (
                      <div className="flex items-center justify-center py-12">
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground mr-2" />
                        <span className="text-sm text-muted-foreground">正在生成...</span>
                      </div>
                    )}

                    {!isLoading && !result && (
                      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                        <Sparkles className="h-8 w-8 mb-2 opacity-40" />
                        <p className="text-sm">
                          {tab.hasContext
                            ? `输入上下文，点击按钮生成${tab.label}`
                            : `点击按钮生成${tab.label}`}
                        </p>
                      </div>
                    )}

                    {!isLoading && result && (
                      <div className="markdown-preview text-sm pr-2">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {result}
                        </ReactMarkdown>
                      </div>
                    )}
                  </ScrollArea>
                </TabsContent>
              );
            })}
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
