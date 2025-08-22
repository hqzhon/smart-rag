import axios, { AxiosResponse } from 'axios';
import { QueryRequest, QueryResponse, DocumentInfo, ChatHistoryItem, SessionInfo, SearchResult, HealthCheckResponse } from '@/types';

// 创建axios实例
const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token等
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

// 聊天相关API
export const chatApi = {
  // 发送消息
  sendMessage: async (request: QueryRequest): Promise<QueryResponse> => {
    const response = await apiClient.post<QueryResponse>('/chat/query', request);
    return response.data;
  },

  // 流式发送消息 (SSE)
  streamQuery: async (
    request: QueryRequest,
    callbacks: {
      onChunk: (token: string) => void;
      onDocuments: (documents: any[], messageId?: string) => void;
      onStatus: (status: string) => void;
      onError: (error: string) => void;
      onComplete: () => void;
    }
  ): Promise<void> => {
    try {
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error('Response body is null');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) break;
          
          buffer += decoder.decode(value, { stream: true });
          
          // 处理SSE消息
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // 保留不完整的行
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6); // 移除 'data: ' 前缀
              
              if (data === '[DONE]') {
                callbacks.onComplete();
                return;
              }
              
              try {
                const parsed = JSON.parse(data);
                
                switch (parsed.type) {
                  case 'chunk':
                    if (parsed.content) {
                      callbacks.onChunk(parsed.content);
                    }
                    break;
                  case 'documents':
                    if (parsed.documents) {
                      callbacks.onDocuments(parsed.documents, parsed.message_id);
                    }
                    break;
                  case 'status':
                    if (parsed.message) {
                      callbacks.onStatus(parsed.message);
                    }
                    break;
                  case 'error':
                    callbacks.onError(parsed.message || 'Unknown error');
                    return;
                  case 'end':
                    callbacks.onComplete();
                    return;
                  default:
                    // 兼容旧格式
                    if (parsed.token) {
                      callbacks.onChunk(parsed.token);
                    } else if (parsed.error) {
                      callbacks.onError(parsed.error);
                      return;
                    }
                }
              } catch (parseError) {
                // 如果不是JSON，直接作为文本处理
                if (data.trim()) {
                  callbacks.onChunk(data);
                }
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
    } catch (error) {
      console.error('Stream error:', error);
      callbacks.onError(error instanceof Error ? error.message : 'Unknown error');
    }
  },

  // 创建新会话
  createSession: async (): Promise<{ session_id: string }> => {
    const response = await apiClient.post<{ session_id: string }>('/chat/sessions');
    return response.data;
  },

  // 获取会话信息
  getSessionInfo: async (sessionId: string): Promise<SessionInfo> => {
    const response = await apiClient.get(`/chat/sessions/${sessionId}`);
    return response.data;
  },

  // 获取会话列表
  getChatSessions: async (page: number = 1, pageSize: number = 20): Promise<any> => {
    const response = await apiClient.get(`/chat/sessions?page=${page}&page_size=${pageSize}`);
    return response.data;
  },

  // 获取聊天历史
  getChatHistory: async (sessionId: string, limit = 50): Promise<ChatHistoryItem[]> => {
    const response = await apiClient.get(`/chat/history/${sessionId}?limit=${limit}`);
    return response.data;
  },

  // 删除会话
  deleteSession: async (sessionId: string): Promise<{ success: boolean; message?: string }> => {
    try {
      const response = await apiClient.delete(`/chat/sessions/${sessionId}`);
      return { success: true, message: response.data.message };
    } catch (error) {
      console.error('Delete session error:', error);
      return { success: false, message: 'Failed to delete session' };
    }
  },
};

// 文档相关API
export const documentApi = {
  // 上传文档
  uploadDocument: async (file: File, sessionId?: string): Promise<DocumentInfo> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<DocumentInfo>('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // 获取文档列表
  getDocuments: async (sessionId?: string): Promise<DocumentInfo[]> => {
    const url = sessionId ? `/documents?session_id=${sessionId}` : '/documents';
    const response = await apiClient.get<DocumentInfo[]>(url);
    return response.data;
  },

  // 删除文档
  deleteDocument: async (documentId: string): Promise<void> => {
    await apiClient.delete(`/documents/${documentId}`);
  },

  // 获取智能分块统计
  getChunkingStats: async (): Promise<any> => {
    const response = await apiClient.get('/documents/chunking/stats');
    return response.data;
  },

  // 重置智能分块统计
  resetChunkingStats: async (): Promise<void> => {
    await apiClient.post('/documents/chunking/reset-stats');
  },

  // 更新智能分块配置
  updateChunkingConfig: async (config: {
    chunk_size?: number;
    chunk_overlap?: number;
    enable_semantic?: boolean;
  }): Promise<void> => {
    await apiClient.post('/documents/chunking/config', config);
  },
};

// 搜索相关API
export const searchApi = {
  // 搜索文档
  searchDocuments: async (query: string, sessionId?: string): Promise<SearchResult[]> => {
    const params = new URLSearchParams({ query });
    if (sessionId) {
      params.append('session_id', sessionId);
    }
    
    const response = await apiClient.get(`/search?${params.toString()}`);
    return response.data;
  },
};

// 健康检查API
export const healthApi = {
  // 检查系统健康状态
  checkHealth: async (): Promise<HealthCheckResponse> => {
    const response = await apiClient.get('/health');
    return response.data;
  },
};

export default apiClient;