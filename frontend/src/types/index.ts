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
  [key: string]: unknown; // 添加索引签名以兼容React Flow
}

// 情节连接类型
export interface PlotConnection {
  id: string;
  sourceId: string;
  targetId: string;
  connectionType: 'cause' | 'parallel' | 'foreshadow' | 'flashback' | 'next';
  description: string;
  // 后端 snake_case 兼容
  source_id?: string;
  target_id?: string;
  connection_type?: string;
}

// 小说类型
export interface Novel {
  id: string;
  name: string;
  path: string;
  contentPath: string;
  content_path?: string; // 后端 snake_case 兼容
  outlinePath?: string;
  outline_path?: string; // 后端 snake_case 兼容
  chapterCount: number;
  chapter_count?: number; // 后端 snake_case 兼容
  wordCount: number;
  word_count?: number; // 后端 snake_case 兼容
  createdAt: string;
  created_at?: string; // 后端 snake_case 兼容
}

// 灵感类型
export interface Inspiration {
  id: string;
  novelId?: string;
  type: 'plot' | 'continue' | 'character' | 'emotion';
  targetId?: string; // 关联的情节/人物ID
  content: string;
  createdAt: string;
}

// API响应类型
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

// 分页请求
export interface PaginationParams {
  page: number;
  pageSize: number;
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}
