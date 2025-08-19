import React, { memo, useMemo, useState } from 'react';
import {
  Box,
  ListItem,
  Typography,
  Paper,
  Avatar,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  IconButton,
} from '@mui/material';
import {
  Person as PersonIcon,
  SmartToy as BotIcon,
  Info as InfoIcon,
  Close as CloseIcon,
  Description as DocumentIcon,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';

import { Message, DocumentSource } from '@/types';
import { AnimatedBox, HoverAnimatedBox, Typewriter } from './animations';

interface OptimizedMessageItemProps {
  message: Message;
  isStreaming?: boolean;
  streamingContent?: string;
  index: number;
}

const OptimizedMessageItem: React.FC<OptimizedMessageItemProps> = memo(
  ({ message, isStreaming = false, streamingContent, index }) => {
    const isUser = message.type === 'user';
    const isSystem = message.type === 'system';
    const [selectedSource, setSelectedSource] = useState<any>(null);
    const [dialogOpen, setDialogOpen] = useState(false);

    const handleSourceClick = (source: any) => {
      setSelectedSource(source);
      setDialogOpen(true);
    };

    const handleCloseDialog = () => {
      setDialogOpen(false);
      setSelectedSource(null);
    };

    // 缓存头像组件
    const avatarComponent = useMemo(() => {
      if (isUser) {
        return (
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
        );
      }

      return (
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
      );
    }, [isUser, isSystem]);

    // 缓存消息内容渲染
    const messageContent = useMemo(() => {
      if (message.type === 'user') {
        return (
          <Typography
            variant="body1"
            sx={{
              color: 'white',
              lineHeight: 1.6,
              wordBreak: 'break-word',
            }}
          >
            {message.content}
          </Typography>
        );
      }

      const content = isStreaming ? streamingContent || '' : message.content;
      
      return (
        <Box>
          {isStreaming ? (
            <Box sx={{ color: 'text.primary', lineHeight: 1.6 }}>
              <Typewriter text={content} speed={30} />
            </Box>
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

          {isStreaming && (
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
        </Box>
      );
    }, [message.content, message.type, isStreaming, streamingContent]);

    // 缓存来源组件
    const sourcesComponent = useMemo(() => {
      if (!message.sources || message.sources.length === 0) return null;

      // 按document_id分组合并相同文档的引用
      const groupedSources = message.sources.reduce((groups: any, source: DocumentSource) => {
        const documentId = source.metadata?.document_id || 'unknown';
        const sourceTitle = source.metadata?.filename || 
                           source.metadata?.source || 
                           '未知文档';
        const pageNumber = source.metadata?.page_number;
        
        if (!groups[documentId]) {
          groups[documentId] = {
            title: sourceTitle,
            sources: [],
            pageNumbers: new Set()
          };
        }
        
        groups[documentId].sources.push(source);
        if (pageNumber) {
          groups[documentId].pageNumbers.add(pageNumber);
        }
        
        return groups;
      }, {});

      return (
        <AnimatedBox animation="fadeInUp" delay="0.3s">
          <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>
              参考来源:
            </Typography>
            {Object.entries(groupedSources).map(([documentId, group]: [string, any], idx) => {
              // 构建显示标签，包含页码范围信息
              const pageArray = Array.from(group.pageNumbers).sort((a: any, b: any) => a - b);
              let displayLabel = group.title;
              
              if (pageArray.length > 0) {
                if (pageArray.length === 1) {
                  displayLabel += ` (第${pageArray[0]}页)`;
                } else if (pageArray.length <= 3) {
                  displayLabel += ` (第${pageArray.join('、')}页)`;
                } else {
                  displayLabel += ` (第${pageArray[0]}-${pageArray[pageArray.length - 1]}页等${pageArray.length}页)`;
                }
              }
              
              return (
                <AnimatedBox key={documentId} animation="fadeInUp" delay={`${0.1 * idx}s`}>
                  <HoverAnimatedBox hoverAnimation="scale">
                    <Chip
                      icon={<DocumentIcon sx={{ fontSize: '0.75rem' }} />}
                      label={displayLabel}
                      size="small"
                      variant="outlined"
                      clickable
                      onClick={() => handleSourceClick(group)}
                      sx={{
                        fontSize: '0.75rem',
                        height: 24,
                        cursor: 'pointer',
                        '& .MuiChip-label': {
                          px: 1,
                        },
                        '&:hover': {
                          backgroundColor: 'action.hover',
                          borderColor: 'primary.main',
                        },
                      }}
                    />
                  </HoverAnimatedBox>
                </AnimatedBox>
              );
            })}
          </Box>
        </AnimatedBox>
      );
    }, [message.sources]);

    // 缓存时间戳组件
    const timestampComponent = useMemo(() => (
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
          {new Date(message.timestamp).toLocaleTimeString()}
        </Typography>
      </AnimatedBox>
    ), [message.timestamp, isUser]);

    // 缓存纸张样式
    const paperSx = useMemo(() => ({
      p: 2,
      maxWidth: '70%',
      minWidth: '200px',
      bgcolor: isUser
        ? 'primary.main'
        : isSystem
        ? 'info.light'
        : 'background.paper',
      borderRadius: 2,
      position: 'relative' as const,
      '&::before': isUser
        ? {
            content: '""',
            position: 'absolute' as const,
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
            position: 'absolute' as const,
            top: 12,
            left: -8,
            width: 0,
            height: 0,
            borderRight: '8px solid',
            borderRightColor: isSystem ? 'info.light' : 'background.paper',
            borderTop: '8px solid transparent',
            borderBottom: '8px solid transparent',
          },
    }), [isUser, isSystem]);

    return (
      <AnimatedBox animation="fadeInUp" duration="0.5s" delay={`${(index % 5) * 0.1}s`}>
        <ListItem
          sx={{
            display: 'flex',
            justifyContent: isUser ? 'flex-end' : 'flex-start',
            alignItems: 'flex-start',
            mb: 3,
            px: 2,
          }}
        >
          {!isUser && avatarComponent}

          <HoverAnimatedBox hoverAnimation="scale">
            <Paper elevation={2} sx={paperSx}>
              {messageContent}
              {sourcesComponent}
              {timestampComponent}
            </Paper>
          </HoverAnimatedBox>

          {isUser && avatarComponent}
        </ListItem>

        {/* Document Reference Dialog */}
        <Dialog
          open={dialogOpen}
          onClose={handleCloseDialog}
          maxWidth="md"
          fullWidth
          PaperProps={{
            sx: {
              borderRadius: 2,
              maxHeight: '80vh',
            },
          }}
        >
          <DialogTitle
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              pb: 1,
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <DocumentIcon color="primary" />
              <Typography variant="h6">文档引用</Typography>
            </Box>
            <IconButton
              onClick={handleCloseDialog}
              size="small"
              sx={{ color: 'text.secondary' }}
            >
              <CloseIcon />
            </IconButton>
          </DialogTitle>
          <DialogContent dividers>
            <Box sx={{ py: 1 }}>
              <Typography variant="subtitle2" color="primary" gutterBottom>
                文档名称:
              </Typography>
              <Typography variant="body2" sx={{ mb: 2, fontWeight: 500 }}>
                {selectedSource?.title || '未知文档'}
              </Typography>
              
              <Typography variant="subtitle2" color="primary" gutterBottom>
                引用内容 ({selectedSource?.sources?.length || 0} 个引用):
              </Typography>
              
              {selectedSource?.sources?.length > 0 ? (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {selectedSource.sources.map((source: DocumentSource, index: number) => {
                    let content = '此文档被用作回答您问题的参考资料。';
                    
                    // 尝试将source.content解析为JSON，如果存在content键则使用其值
                    if (source.content) {
                      try {
                        const parsedContent = JSON.parse(source.content);
                        if (parsedContent && typeof parsedContent === 'object' && parsedContent.content) {
                          content = parsedContent.content;
                        } else {
                          content = source.content;
                        }
                      } catch (error) {
                        // 如果解析失败，直接使用原始内容
                        content = source.content;
                      }
                    }
                    
                    const pageInfo = source.metadata?.page_number ? ` (第${source.metadata.page_number}页)` : '';
                    
                    return (
                      <Box 
                        key={index} 
                        sx={{ 
                          border: '1px solid',
                          borderColor: 'divider',
                          borderRadius: 2,
                          overflow: 'hidden'
                        }}
                      >
                        {/* 引用标题栏 */}
                        <Box sx={{ 
                          backgroundColor: 'primary.main',
                          color: 'primary.contrastText',
                          px: 2,
                          py: 1,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between'
                        }}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                            引用片段 #{index + 1}
                          </Typography>
                          {pageInfo && (
                            <Typography variant="caption" sx={{ 
                              backgroundColor: 'rgba(255,255,255,0.2)',
                              px: 1,
                              py: 0.5,
                              borderRadius: 1
                            }}>
                              {pageInfo}
                            </Typography>
                          )}
                        </Box>
                        
                        {/* 引用内容 */}
                        <Box sx={{ p: 2 }}>
                          <Typography variant="body2" sx={{ 
                            lineHeight: 1.6,
                            maxHeight: '200px',
                            overflow: 'auto',
                            whiteSpace: 'pre-wrap',
                            '&::-webkit-scrollbar': {
                              width: '6px',
                            },
                            '&::-webkit-scrollbar-track': {
                              backgroundColor: 'grey.100',
                              borderRadius: '3px',
                            },
                            '&::-webkit-scrollbar-thumb': {
                              backgroundColor: 'grey.400',
                              borderRadius: '3px',
                              '&:hover': {
                                backgroundColor: 'grey.600',
                              },
                            },
                          }}>
                            {content}
                          </Typography>
                        </Box>
                      </Box>
                    );
                  })}
                </Box>
              ) : (
                <Box sx={{ 
                  textAlign: 'center',
                  py: 4,
                  color: 'text.secondary'
                }}>
                  <DocumentIcon sx={{ fontSize: 48, mb: 1, opacity: 0.5 }} />
                  <Typography variant="body2">
                    暂无引用内容
                  </Typography>
                </Box>
              )}
            </Box>
          </DialogContent>
          <DialogActions sx={{ px: 3, py: 2 }}>
            <Button onClick={handleCloseDialog} color="inherit">
              关闭
            </Button>
          </DialogActions>
        </Dialog>
      </AnimatedBox>
    );
  },
  // 自定义比较函数，只在关键属性变化时重新渲染
  (prevProps, nextProps) => {
    return (
      prevProps.message.id === nextProps.message.id &&
      prevProps.message.content === nextProps.message.content &&
      prevProps.isStreaming === nextProps.isStreaming &&
      prevProps.streamingContent === nextProps.streamingContent &&
      prevProps.index === nextProps.index &&
      JSON.stringify(prevProps.message.sources) === JSON.stringify(nextProps.message.sources)
    );
  }
);

OptimizedMessageItem.displayName = 'OptimizedMessageItem';

export default OptimizedMessageItem;