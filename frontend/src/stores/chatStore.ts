import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { Message, ChatSession, AppState, ChatHistoryItem, DocumentSource } from '@/types';
import { chatApi } from '@/services/api';

// Generate unique ID with timestamp and random component
const generateUniqueId = (prefix: string): string => {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
};

interface ChatStore extends AppState {
  // Streaming state
  streamingMessage: { id: string; content: string; sessionId: string; sources?: DocumentSource[] } | null;
  
  // Actions
  setCurrentSession: (sessionId: string | null) => void;
  addMessage: (sessionId: string, message: Message) => void;
  updateMessage: (sessionId: string, messageId: string, updates: Partial<Message>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  createSession: () => Promise<string>;
  loadSessions: () => Promise<void>;
  loadChatHistory: (sessionId: string) => Promise<void>;
  sendMessage: (sessionId: string, content: string) => Promise<void>;
  sendStreamMessage: (sessionId: string, content: string) => Promise<void>;
  startStreamingMessage: (sessionId: string) => string;
  appendToken: (token: string) => void;
  appendDocuments: (documents: DocumentSource[], messageId?: string) => void;
  finishStreamingMessage: () => void;
  clearMessages: (sessionId: string) => void;
  deleteSession: (sessionId: string) => void;
}

export const useChatStore = create<ChatStore>()(
  devtools(
    (set, get) => ({
      // Initial state
      currentSession: null,
      sessions: [],
      messages: {},
      isLoading: false,
      error: null,
      streamingMessage: null,

      // Actions
      setCurrentSession: (sessionId) => {
        set({ currentSession: sessionId });
      },

      addMessage: (sessionId, message) => {
        set((state) => ({
          messages: {
            ...state.messages,
            [sessionId]: [...(state.messages[sessionId] || []), message],
          },
        }));
      },

      updateMessage: (sessionId, messageId, updates) => {
        set((state) => ({
          messages: {
            ...state.messages,
            [sessionId]: state.messages[sessionId]?.map((msg) =>
              msg.id === messageId ? { ...msg, ...updates } : msg
            ) || [],
          },
        }));
      },

      setLoading: (loading) => {
        set({ isLoading: loading });
      },

      setError: (error) => {
        set({ error });
      },

      createSession: async () => {
        try {
          set({ isLoading: true, error: null });
          
          const response = await chatApi.createSession();
          const sessionId = response.session_id;
          
          // 简化逻辑：只设置当前会话状态
          set((state) => ({
            ...state,
            currentSession: sessionId,
            messages: { ...state.messages, [sessionId]: [] },
            isLoading: false,
          }));

          return sessionId;
        } catch (error) {
          console.error('创建会话失败:', error);
          set({ 
            error: error instanceof Error ? error.message : '创建会话失败',
            isLoading: false 
          });
          throw error;
        }
      },

      loadSessions: async () => {
        try {
          set({ isLoading: true, error: null });
          
          const { currentSession: previousCurrentSession } = get();
          const response = await chatApi.getChatSessions(1, 50, false); 
          
          if (response && response.sessions) {
            const sessions: ChatSession[] = response.sessions
              .filter((item: any) => item && item.id)
              .map((item: any) => ({
                id: item.id,
                title: item.title || '未命名对话',
                createdAt: new Date(item.created_at),
                updatedAt: new Date(item.updated_at),
                messageCount: item.message_count || 0,
                status: 'active'
              }));
            
            set((state) => ({
              ...state,
              sessions,
              isLoading: false,
              currentSession: previousCurrentSession
            }));
          } else {
            set((state) => ({
              ...state,
              sessions: [],
              isLoading: false,
              currentSession: previousCurrentSession
            }));
          }
        } catch (error) {
          console.error('加载会话列表失败:', error);
          set({ 
            error: error instanceof Error ? error.message : '加载会话列表失败',
            isLoading: false
          });
        }
      },

      loadChatHistory: async (sessionId) => {
        try {
          set({ isLoading: true, error: null });
          
          const history = await chatApi.getChatHistory(sessionId);
          const messages: Message[] = [];
          
          // 按时间顺序处理每个历史记录项
          history.forEach((item: ChatHistoryItem, index: number) => {
            const baseTimestamp = new Date(item.created_at || item.timestamp || Date.now());
            
            // 添加用户消息
            if (item.question) {
              messages.push({
                id: item.id ? `${item.id}-user` : generateUniqueId('user'),
                type: 'user' as const,
                content: item.question,
                timestamp: new Date(baseTimestamp.getTime() + index * 1000), // 确保时间递增
              });
            }
            
            // 添加助手回复
            if (item.answer) {
              messages.push({
                id: item.id ? `${item.id}-assistant` : generateUniqueId('assistant'),
                type: 'assistant' as const,
                content: item.answer,
                timestamp: new Date(baseTimestamp.getTime() + index * 1000 + 500), // 助手回复稍晚于用户消息
                sources: item.sources || [],
              });
            }
          });
          
          // 按时间戳排序确保正确顺序
          messages.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());

          set((state) => ({
            messages: { ...state.messages, [sessionId]: messages },
            isLoading: false,
          }));
          
        } catch (error) {
          console.error('加载聊天历史失败:', error);
          set({ 
            error: error instanceof Error ? error.message : '加载聊天历史失败',
            isLoading: false 
          });
        }
      },

      sendStreamMessage: async (sessionId, content) => {
        try {
          // 添加用户消息
          const userMessage: Message = {
            id: generateUniqueId('user'),
            type: 'user',
            content,
            timestamp: new Date(),
          };

          get().addMessage(sessionId, userMessage);

          // 开始流式消息
          get().startStreamingMessage(sessionId);
          set({ isLoading: true, error: null });

          // 发送流式请求
          await chatApi.streamQuery(
            {
              query: content,
              session_id: sessionId,
            },
            {
              onChunk: (token: string) => {
                get().appendToken(token);
              },
              onDocuments: (documents: any[], messageId?: string) => {
                get().appendDocuments(documents, messageId);
              },
              onStatus: (status: string) => {
                // 处理状态更新
              },
              onError: (error: string) => {
                set({ error: `发送消息失败: ${error}`, isLoading: false });
                get().finishStreamingMessage();
              },
              onComplete: () => {
                get().finishStreamingMessage();
                set({ isLoading: false });
                
                // 发送消息完成后刷新侧边栏，显示新会话
                setTimeout(() => {
                  get().loadSessions();
                }, 300); // 短延迟确保消息已保存到数据库
              },
            }
          );

        } catch (error) {
          let errorMessage = '发送消息失败';
          if (error instanceof Error) {
            errorMessage = `发送消息失败: ${error.message}`;
          }
          
          set({ 
            error: errorMessage,
            isLoading: false 
          });
          get().finishStreamingMessage();
        }
      },

      startStreamingMessage: (sessionId: string) => {
        const assistantMessage: Message = {
          id: generateUniqueId('assistant'),
          type: 'assistant',
          content: '',
          timestamp: new Date(),
        };

        get().addMessage(sessionId, assistantMessage);
        
        set({
          streamingMessage: {
            id: assistantMessage.id,
            content: '',
            sessionId,
            sources: [],
          },
        });

        return assistantMessage.id;
      },

      appendToken: (token: string) => {
        set((state) => {
          if (!state.streamingMessage) return state;
          
          const newContent = state.streamingMessage.content + token;
          
          // 同时更新streamingMessage和messages中的对应消息
          const updatedMessages = {
            ...state.messages,
            [state.streamingMessage.sessionId]: state.messages[state.streamingMessage.sessionId]?.map(msg =>
              msg.id === state.streamingMessage!.id
                ? { ...msg, content: newContent }
                : msg
            ) || [],
          };
          
          return {
            ...state,
            streamingMessage: {
              ...state.streamingMessage,
              content: newContent,
            },
            messages: updatedMessages,
          };
        });
      },

      appendDocuments: (documents: DocumentSource[], _messageId?: string) => {
        set((state) => {
          if (!state.streamingMessage) return state;
          
          const currentSources = state.streamingMessage.sources || [];
          const newSources = [...currentSources, ...documents];
          
          return {
            ...state,
            streamingMessage: {
              ...state.streamingMessage,
              sources: newSources,
            },
          };
        });
      },

      finishStreamingMessage: () => {
        const { streamingMessage } = get();
        if (streamingMessage) {
          // Update the final message with sources, ensuring type conversion
          const convertedSources = (streamingMessage.sources || []).map((source: any) => ({
            content: source.content || '',
            metadata: {
              filename: source.metadata?.filename || source.filename || '',
              page_number: source.metadata?.page_number || source.page_number,
              document_id: source.metadata?.document_id || source.document_id || '',
              file_type: source.metadata?.file_type || source.file_type || '',
              source: source.metadata?.source || source.source || ''
            }
          }));
          
          get().updateMessage(streamingMessage.sessionId, streamingMessage.id, {
            sources: convertedSources,
            metadata: {
              documents: convertedSources,
            },
          });
        }
        set({ streamingMessage: null });
      },

      sendMessage: async (sessionId, content) => {
        try {
          // 添加用户消息
          const userMessage: Message = {
            id: generateUniqueId('user'),
            type: 'user',
            content,
            timestamp: new Date(),
          };

          get().addMessage(sessionId, userMessage);

          // 创建助手消息占位符
          const assistantMessage: Message = {
            id: generateUniqueId('assistant'),
            type: 'assistant',
            content: '',
            timestamp: new Date(),
          };

          get().addMessage(sessionId, assistantMessage);
          set({ isLoading: true, error: null });

          // 发送请求
          
          const response = await chatApi.sendMessage({
            query: content,
            session_id: sessionId,
          });

          // 更新助手消息
          get().updateMessage(sessionId, assistantMessage.id, {
            content: response.response,
            sources: response.sources ? response.sources.map((source: any) => ({
              content: source.content || '',
              metadata: {
                filename: source.metadata?.filename || source.filename || '',
                page_number: source.metadata?.page_number || source.page_number,
                document_id: source.metadata?.document_id || source.document_id || '',
                file_type: source.metadata?.file_type || source.file_type || '',
                source: source.metadata?.source || source.source || ''
              }
            })) : [],
            metadata: response.metadata,
          });

          set({ isLoading: false }); // 设置加载状态为 false

          // 发送消息完成后刷新侧边栏，显示新会话
          setTimeout(() => {
            get().loadSessions();
          }, 300); // 短延迟确保消息已保存到数据库

        } catch (error) {
          let errorMessage = '发送消息失败';
          if (error instanceof Error) {
            errorMessage = `发送消息失败: ${error.message}`;
          }
          
          set({ 
            error: errorMessage,
            isLoading: false 
          });
        }
      },

      clearMessages: (sessionId) => {
        set((state) => ({
          messages: { ...state.messages, [sessionId]: [] },
        }));
      },

      deleteSession: (sessionId) => {
        set((state) => {
          const newMessages = { ...state.messages };
          delete newMessages[sessionId];
          
          return {
            sessions: state.sessions.filter((s) => s.id !== sessionId),
            messages: newMessages,
            currentSession: state.currentSession === sessionId ? null : state.currentSession,
          };
        });
      },
    }),
    {
      name: 'chat-store',
    }
  )
);