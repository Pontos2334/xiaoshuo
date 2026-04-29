// 人物类型定义
export interface Character {
  id: string;
  name: string;
  aliases: string[];
  basicInfo: Record<string, string | number>;
  personality: string[];
  abilities: string[];
  storySummary: string;
  firstAppear: string;
  createdAt: string;
  updatedAt: string;
  [key: string]: unknown; // 添加索引签名以兼容G6
}

// 人物关系类型
export interface CharacterRelation {
  id: string;
  sourceId: string;
  targetId: string;
  relationType: string;
  description: string;
  strength: number; // 1-10
  [key: string]: unknown; // 添加索引签名以兼容G6
}

// 情节节点类型
export interface PlotNode {
  id: string;
  title: string;
  chapter: string;
  summary: string;
  characters: string[]; // 涉及的人物ID
  emotion: string;
  importance: number; // 1-10
  contentRef: string;
  createdAt: string;
  updatedAt: string;
  [key: string]: unknown; // 添加索引签名以兼容React Flow
}

// 情节连接类型
export interface PlotConnection {
  id: string;
  sourceId: string;
  targetId: string;
  connectionType: 'cause' | 'parallel' | 'foreshadow' | 'flashback' | 'next';
  description: string;
}

// 小说类型
export interface Novel {
  id: string;
  name: string;
  path: string;
  contentPath: string;
  outlinePath?: string;
  chapterCount: number;
  wordCount: number;
  createdAt: string;
  updatedAt: string;
  [key: string]: unknown; // 添加索引签名以兼容 snake_case 字段
}

// 灵感类型
export interface Inspiration {
  id: string;
  novelId?: string;
  type: 'scene' | 'plot' | 'continue' | 'character' | 'emotion';
  targetId?: string; // 关联的情节/人物ID（多个用逗号分隔）
  content: string;
  createdAt: string;
}

// API响应类型
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

// 分析模式
export type AnalyzeMode = 'full' | 'incremental';

// 章节类型
export interface Chapter {
  id: string;
  novelId: string;
  chapterNumber: number;
  title: string;
  wordCount: number;
  status: 'draft' | 'completed' | 'revised';
  summary?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ChapterDetail extends Chapter {
  content?: string;
}

// 世界观实体类型
export interface WorldEntity {
  id: string;
  novelId: string;
  name: string;
  entityType: 'location' | 'item' | 'organization' | 'event' | 'concept' | 'terminology';
  description: string;
  attributes: Record<string, unknown>;
  rules?: string;
  source: 'ai' | 'manual';
  createdAt: string;
  updatedAt: string;
}

export interface EntityRelation {
  id: string;
  novelId: string;
  sourceId: string;
  targetId: string;
  relationType: string;
  description: string;
  sourceName?: string;
  targetName?: string;
}

// 一致性检查结果
export interface ConsistencyIssue {
  type: 'character' | 'timeline' | 'rule' | 'relation' | 'power_system' | 'geography' | 'naming';
  severity: 'error' | 'warning' | 'info';
  description: string;
  chapterA?: string;
  chapterB?: string;
  detail?: string;
  suggestion?: string;
}

// 伏笔追踪
export interface Foreshadow {
  id: string;
  novelId: string;
  title: string;
  description: string;
  plantChapter: number;
  plantDescription: string;
  status: 'planted' | 'partially_revealed' | 'resolved' | 'abandoned';
  resolveChapter: number | null;
  resolveDescription: string | null;
  relatedCharacters: string[];
  relatedPlots: string[];
  importance: number;
  source: 'ai' | 'user';
  createdAt: string;
  updatedAt: string;
}

// 角色成长弧线
export interface CharacterArcPoint {
  id: string;
  characterId: string;
  novelId: string;
  chapterNumber: number;
  psychologicalState: string;
  emotionalState: string;
  abilityDescription: string;
  abilityLevel: number | null;
  relationshipChanges: { targetId: string; change: string }[];
  keyEvents: string[];
  growthNotes: string;
  source: 'ai' | 'user';
  createdAt: string;
  updatedAt: string;
}

// 节奏张力点
export interface TensionPoint {
  id: string;
  novelId: string;
  chapterNumber: number;
  tensionLevel: number;
  emotionTags: string[];
  keyEventsSummary: string;
  pacingNote: string;
  readerHookScore: number | null;
  cliffhangerScore: number | null;
  source: 'ai' | 'user';
  createdAt: string;
  updatedAt: string;
}

// 大纲节点
export interface OutlineNode {
  id: string;
  novelId: string;
  parentId: string | null;
  level: number;
  title: string;
  content: string;
  chapterRange: string;
  status: 'draft' | 'completed' | 'active';
  sortOrder: number;
  aiContext: Record<string, unknown> | null;
  children: OutlineNode[];
  createdAt: string;
  updatedAt: string;
}

// 节奏问题
export interface PacingIssue {
  issueType: string;
  description: string;
  chapters: number[];
  suggestion: string;
}

// 弧线不一致性
export interface ArcInconsistency {
  description: string;
  fromChapter: number;
  toChapter: number;
  severity: 'error' | 'warning' | 'info';
}
