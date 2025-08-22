import React, { useMemo, useCallback } from 'react';
import { FixedSizeList as List } from 'react-window';
import {
  Box,
  ListItem,
  Typography,
  Paper,
  Avatar,
  Chip,
} from '@mui/material';
import {
  Person as PersonIcon,
  SmartToy as BotIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';

import { Message } from '@/types';
import { AnimatedBox, HoverAnimatedBox, Typewriter } from './animations';

interface VirtualizedMessageListProps {
  messages: Message[];
  streamingMessageId?: string | null;
  streamingContent?: string;
  height?: number;
}

interface MessageItemProps {
  index: number;
  style: React.CSSProperties;
  data: {
    messages: Message[];
    streamingMessageId?: string | null;
    streamingContent?: string;
  };
}

const MessageItem: React.FC<MessageItemProps> = ({ index, style, data }) => {
  const { messages, streamingMessageId, streamingContent } = data;
  const message = messages[index];
  const isStreaming = streamingMessageId === message.id;
  const isUser = message.type === 'user';
  const isSystem = message.type === 'system';

  const renderMessageContent = useCallback((msg: Message, streaming = false) => {
    if (msg.type === 'user') {
      return (
        <Typography
          variant="body1"
          sx={{
            color: 'white',
            lineHeight: 1.6,
            wordBreak: 'break-word',
          }}
        >
          {msg.content}
        </Typography>
      );
    }

    const content = streaming ? streamingContent || '' : msg.content;
    
    return (
      <Box>
        {streaming ? (
          <Typewriter
            text={content}
            speed={30}
            sx={{
              color: 'text.primary',
              lineHeight: 1.6,
              '& .markdown': {
                '& p': { mb: 1 },
                '& ul, & ol': { pl: 2, mb: 1 },
                '& li': { mb: 0.5 },
                '& blockquote': {
                  borderLeft: '4px solid',
                  borderColor: 'primary.main',
                  pl: 2,
                  ml: 0,
                  fontStyle: 'italic',
                  opacity: 0.8,
                },
                '& code': {
                  backgroundColor: 'action.hover',
                  px: 0.5,
                  py: 0.25,
                  borderRadius: 1,
                  fontSize: '0.875em',
                },
              },
            }}
          />
        ) : (
          <Box
            sx={{
              color: 'text.primary',
              lineHeight: 1.6,
              '& p': { mb: 1 },
              '& ul, & ol': { pl: 2, mb: 1 },
              '& li': { mb: 0.5 },
              '& blockquote': {
                borderLeft: '4px solid',
                borderColor: 'primary.main',
                pl: 2,
                ml: 0,
                fontStyle: 'italic',
                opacity: 0.8,
              },
              '& code': {
                backgroundColor: 'action.hover',
                px: 0.5,
                py: 0.25,
                borderRadius: 1,
                fontSize: '0.875em',
              },
            }}
          >
            <ReactMarkdown
              components={{
                code({ node, inline, className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '');
                  return !inline && match ? (
                    <SyntaxHighlighter
                      style={tomorrow as any}
                      language={match[1]}
                      PreTag="div"
                      customStyle={{
                         margin: '0',
                         borderRadius: '4px',
                         fontSize: '0.875rem',
                       } as any}
                      {...props}
                    >
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  ) : (
                    <code className={className} {...props}>
                      {children}
                    </code>
                  );
                },
              }}
            >
              {content}
            </ReactMarkdown>
          </Box>
        )}

        {streaming && (
          <Box
            sx={{
              display: 'inline-flex',
              alignItems: 'center',
              ml: 1,
              animation: 'pulse 1.5s ease-in-out infinite',
              '@keyframes pulse': {
                '0%': { opacity: 1 },
                '50%': { opacity: 0.5 },
                '100%': { opacity: 1 },
              },
            }}
          >
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                bgcolor: 'primary.main',
                mr: 0.5,
              }}
            />
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                bgcolor: 'primary.main',
                mr: 0.5,
                animationDelay: '0.2s',
              }}
            />
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                bgcolor: 'primary.main',
                animationDelay: '0.4s',
              }}
            />
          </Box>
        )}

        {msg.sources && msg.sources.length > 0 && (
          <AnimatedBox animation="fadeInUp" delay="0.3s">
            <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>
                参考来源:
              </Typography>
              {msg.sources.map((source, idx) => {
                const sourceTitle = typeof source === 'string' 
                  ? source 
                  : (source as any)?.filename || source?.metadata?.filename || source?.metadata?.source || '未知文档';
                
                return (
                  <AnimatedBox key={idx} animation="fadeInUp" delay={`${0.1 * idx}s`}>
                    <HoverAnimatedBox hoverAnimation="scale">
                      <Chip
                        label={sourceTitle}
                        size="small"
                        variant="outlined"
                        sx={{
                          fontSize: '0.75rem',
                          height: 24,
                          '& .MuiChip-label': {
                            px: 1,
                          },
                        }}
                      />
                    </HoverAnimatedBox>
                  </AnimatedBox>
                );
              })}
            </Box>
          </AnimatedBox>
        )}

        <AnimatedBox animation="fadeInUp" delay="0.4s">
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              display: 'block',
              mt: 1,
              textAlign: isUser ? 'right' : 'left',
            }}
          >
            {new Date(msg.timestamp).toLocaleTimeString()}
          </Typography>
        </AnimatedBox>
      </Box>
    );
  }, [streamingContent, isUser]);

  return (
    <div style={style}>
      <ListItem
        sx={{
          display: 'flex',
          justifyContent: isUser ? 'flex-end' : 'flex-start',
          alignItems: 'flex-start',
          mb: 3,
          px: 2,
        }}
      >
        {!isUser && (
          <HoverAnimatedBox hoverAnimation="scale">
            <Avatar
              sx={{
                bgcolor: isSystem ? 'info.main' : 'primary.main',
                mr: 2,
                mt: 0.5,
                width: 40,
                height: 40,
              }}
            >
              {isSystem ? <InfoIcon /> : <BotIcon />}
            </Avatar>
          </HoverAnimatedBox>
        )}

        <HoverAnimatedBox hoverAnimation="lift">
          <Paper
            elevation={2}
            sx={{
              p: 2,
              maxWidth: '70%',
              minWidth: '200px',
              bgcolor: isUser
                ? 'primary.main'
                : isSystem
                ? 'info.light'
                : 'background.paper',
              borderRadius: 2,
              position: 'relative',
              '&::before': isUser
                ? {
                    content: '""',
                    position: 'absolute',
                    top: 12,
                    right: -8,
                    width: 0,
                    height: 0,
                    borderLeft: '8px solid',
                    borderLeftColor: 'primary.main',
                    borderTop: '8px solid transparent',
                    borderBottom: '8px solid transparent',
                  }
                : {
                    content: '""',
                    position: 'absolute',
                    top: 12,
                    left: -8,
                    width: 0,
                    height: 0,
                    borderRight: '8px solid',
                    borderRightColor: isSystem ? 'info.light' : 'background.paper',
                    borderTop: '8px solid transparent',
                    borderBottom: '8px solid transparent',
                  },
            }}
          >
            {renderMessageContent(message, isStreaming)}
          </Paper>
        </HoverAnimatedBox>

        {isUser && (
          <HoverAnimatedBox hoverAnimation="scale">
            <Avatar
              sx={{
                bgcolor: 'secondary.main',
                ml: 2,
                mt: 0.5,
                width: 40,
                height: 40,
              }}
            >
              <PersonIcon />
            </Avatar>
          </HoverAnimatedBox>
        )}
      </ListItem>
    </div>
  );
};

const VirtualizedMessageList: React.FC<VirtualizedMessageListProps> = ({
  messages,
  streamingMessageId,
  streamingContent,
  height = 400,
}) => {
  const itemData = useMemo(
    () => ({
      messages,
      streamingMessageId,
      streamingContent,
    }),
    [messages, streamingMessageId, streamingContent]
  );

  // 估算每个消息项的高度
  // const getItemSize = useCallback((index: number) => {
  //   const message = messages[index];
  //   if (!message) return 120;
  //   
  //   // 基础高度
  //   let height = 120;
  //   
  //   // 根据内容长度调整高度
  //   const contentLength = message.content.length;
  //   if (contentLength > 100) {
  //     height += Math.floor(contentLength / 100) * 20;
  //   }
  //   
  //   // 如果有来源，增加高度
  //   if (message.sources && message.sources.length > 0) {
  //     height += 40;
  //   }
  //   
  //   return Math.min(height, 600); // 最大高度限制
  // }, [messages]);

  if (messages.length === 0) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100%',
          color: 'text.secondary',
        }}
      >
        <Typography variant="body1">暂无消息</Typography>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        height: '100%',
        '& .react-window-list': {
          scrollbarWidth: 'thin',
          scrollbarColor: 'rgba(0,0,0,0.2) transparent',
          '&::-webkit-scrollbar': {
            width: '8px',
          },
          '&::-webkit-scrollbar-track': {
            background: 'transparent',
          },
          '&::-webkit-scrollbar-thumb': {
            background: 'rgba(0,0,0,0.2)',
            borderRadius: '4px',
            '&:hover': {
              background: 'rgba(0,0,0,0.3)',
            },
          },
        },
      }}
    >
      <List
        className="react-window-list"
        height={height}
        width="100%"
        itemCount={messages.length}
        itemSize={120}
        itemData={itemData}
        overscanCount={5}
      >
        {MessageItem}
      </List>
    </Box>
  );
};

export default VirtualizedMessageList;