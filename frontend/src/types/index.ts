// 文档来源类型 - 匹配后端返回的数据结构
export interface DocumentSource {
  content: string;
  metadata: {
    filename: string;
    page_number?: number;
    document_id: string;
    file_type?: string;
    source: string;
  };
}

// 消息类型
export interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  sources?: DocumentSource[];
  metadata?: Record<string, any>;
}

// 聊天会话类型
export interface ChatSession {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
  messageCount: number;
  status?: 'active' | 'empty';  // 新增状态字段：活跃或空会话
}

// API响应类型
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

// 聊天历史项类型
export interface ChatHistoryItem {
  id: string;
  question: string;
  answer: string;
  timestamp: string;
  created_at?: string;
  session_id: string;
  sources?: DocumentSource[];
  metadata?: Record<string, any>;
}

// 会话信息类型
export interface SessionInfo {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  documents: DocumentInfo[];
}

// 搜索结果类型
export interface SearchResult {
  id: string;
  title: string;
  content: string;
  score: number;
  document_id: string;
  metadata?: Record<string, any>;
}

// 健康检查响应类型
export interface HealthCheckResponse {
  status: string;
  timestamp: string;
  version?: string;
  uptime?: number;
}

// 查询请求类型
export interface QueryRequest {
  query: string;
  session_id: string;
  context?: string;
  language?: string;
  max_results?: number;
  include_sources?: boolean;
}

// 查询响应类型
export interface QueryResponse {
  query: string;
  response: string;
  documents: string[];
  sources: Array<Record<string, any>>;  // 修改为对象数组，与后端一致
  session_id: string;
  confidence_score?: number;            // 添加置信度分数
  processing_time?: number;             // 改为可选，与后端一致
  feedback?: string;                    // 添加反馈字段
  metadata?: Record<string, any>;
}

// 文档上传类型
export interface DocumentUpload {
  file: File;
  sessionId?: string;
}

// 文档信息类型
export interface DocumentInfo {
  id: string;
  name: string;
  size: number;
  uploadTime: string;
  type: string;
  progress?: number;
  document_id?: string;
  session_id?: string;
  filename?: string;
  status?: 'uploading' | 'processing' | 'completed' | 'failed' | 'ready' | 'chat_ready' | 'generating_metadata' | 'vectorizing' | 'uploaded' | 'error';  // 支持所有状态值
  chunks?: number;
  message?: string;
  // 新增详细状态字段
  processing_status?: 'pending' | 'processing' | 'completed' | 'failed';
  vectorization_status?: 'pending' | 'processing' | 'completed' | 'failed';
  metadata_generation_status?: 'pending' | 'processing' | 'completed' | 'failed';
  chat_ready?: boolean;
}



// 应用状态类型
export interface AppState {
  currentSession: string | null;
  sessions: ChatSession[];
  messages: Record<string, Message[]>;
  isLoading: boolean;
  error: string | null;
}

// 主题类型
export interface Theme {
  mode: 'light' | 'dark';
  primaryColor: string;
  backgroundColor: string;
  textColor: string;
}