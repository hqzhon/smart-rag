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
  getChatSessions: async (page: number = 1, pageSize: number = 20, includeEmpty: boolean = false): Promise<any> => {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
      include_empty: includeEmpty.toString()
    });
    const response = await apiClient.get(`/chat/sessions?${params.toString()}`);
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

  // 重命名会话
  renameSession: async (sessionId: string, newTitle: string): Promise<{ success: boolean; message?: string }> => {
    try {
      const response = await apiClient.patch(`/chat/sessions/${sessionId}`, {
        title: newTitle.trim()
      });
      return { 
        success: true, 
        message: response.data.message || '重命名成功' 
      };
    } catch (error: any) {
      console.error('Rename session error:', error);
      if (error.response?.status === 404) {
        return { success: false, message: '会话不存在' };
      } else if (error.response?.status === 400) {
        return { success: false, message: '请提供有效的会话名称' };
      }
      return { success: false, message: '重命名失败' };
    }
  },
};

// 文档相关API
export const documentApi = {
  // 上传文档
  uploadDocument: async (file: File, sessionId?: string): Promise<DocumentInfo> => {
    const formData = new FormData();
    formData.append('file', file);
    if (sessionId) {
      formData.append('session_id', sessionId);
    }
    const response = await apiClient.post<DocumentInfo>('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // 获取支持的文档格式
  getSupportedFormats: async (): Promise<{
    formats: Array<{
      extension: string;
      format_name: string;
      description: string;
      max_size: number;
      mime_type: string;
      features: string[];
    }>;
    max_file_size: number;
    processing_timeout: number;
    total_formats: number;
  }> => {
    const response = await apiClient.get('/documents/supported-formats');
    return response.data;
  },

  // 获取文档处理状态
  getDocumentStatus: async (documentId: string): Promise<{
    document_id: string;
    filename: string;
    file_format: string;
    processing_status: string;
    vectorization_status: string;
    metadata_generation_status: string;
    processing_start_time?: string;
    processing_end_time?: string;
    total_pages?: number;
    total_sheets?: number;
    total_slides?: number;
    element_types?: string[];
    error_message?: string;
  }> => {
    const response = await apiClient.get(`/documents/${documentId}/status`);
    return response.data;
  },

  // 验证文件格式
  validateFileFormat: async (filename: string): Promise<{
    is_supported: boolean;
    file_format?: string;
    max_size_mb?: number;
    timeout_seconds?: number;
    error_message?: string;
  }> => {
    const response = await apiClient.get(`/documents/formats/validate/${encodeURIComponent(filename)}`);
    return response.data;
  },

  // 获取文档列表
  getDocuments: async (params?: {
    sessionId?: string;
    page?: number;
    page_size?: number;
  }): Promise<{
    documents: DocumentInfo[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
  }> => {
    const searchParams = new URLSearchParams();
    
    if (params?.sessionId) {
      searchParams.append('session_id', params.sessionId);
    }
    if (params?.page) {
      searchParams.append('page', params.page.toString());
    }
    if (params?.page_size) {
      searchParams.append('page_size', params.page_size.toString());
    }
    
    const url = searchParams.toString() ? `/documents?${searchParams.toString()}` : '/documents';
    const response = await apiClient.get(url);
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