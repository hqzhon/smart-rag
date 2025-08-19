import React, { useState, useCallback, useMemo } from 'react';
import {
  Box,

  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Typography,
  CircularProgress,
  Skeleton,
  Fade,
} from '@mui/material';
import {
  Description as DocumentIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
} from '@mui/icons-material';
import { FixedSizeList as VirtualList } from 'react-window';
// @ts-ignore
import InfiniteLoader from 'react-window-infinite-loader';

import { AnimatedBox, HoverAnimatedBox } from './animations';
import { AccessibleIconButton } from './AccessibleButton';
import { DocumentInfo } from '@/types';

// 使用统一的DocumentInfo类型
type Document = DocumentInfo;

interface LazyDocumentListProps {
  documents: Document[];
  onLoadMore: (startIndex: number, stopIndex: number) => Promise<void>;
  onDelete: (documentId: string) => void;
  onView: (document: Document) => void;
  hasNextPage: boolean;
  isLoading: boolean;
  height?: number;
}

interface DocumentItemProps {
  index: number;
  style: React.CSSProperties;
  data: {
    documents: Document[];
    onDelete: (documentId: string) => void;
    onView: (document: Document) => void;
    isLoading: boolean;
  };
}

const DocumentItem: React.FC<DocumentItemProps> = ({ index, style, data }) => {
  const { documents, onDelete, onView } = data;
  const document = documents[index];

  // 如果文档不存在（正在加载），显示骨架屏
  if (!document) {
    return (
      <div style={style}>
        <ListItem>
          <ListItemIcon>
            <Skeleton variant="circular" width={24} height={24} />
          </ListItemIcon>
          <ListItemText
            primary={<Skeleton variant="text" width="60%" />}
            secondary={<Skeleton variant="text" width="40%" />}
          />
          <ListItemSecondaryAction>
            <Skeleton variant="circular" width={40} height={40} />
            <Skeleton variant="circular" width={40} height={40} sx={{ ml: 1 }} />
          </ListItemSecondaryAction>
        </ListItem>
      </div>
    );
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div style={style}>
      <AnimatedBox animation="fadeInUp" delay={`${(index % 10) * 0.05}s`}>
        <Fade in timeout={300}>
          <ListItem
            sx={{
              borderBottom: '1px solid',
              borderColor: 'divider',
              '&:hover': {
                bgcolor: 'action.hover',
              },
            }}
          >
            <ListItemIcon>
              <HoverAnimatedBox hoverAnimation="scale">
                <DocumentIcon color="primary" />
              </HoverAnimatedBox>
            </ListItemIcon>
            <ListItemText
              primary={
                <Typography
                  variant="body1"
                  sx={{
                    fontWeight: 500,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {document.name}
                </Typography>
              }
              secondary={
                <React.Fragment>
                  <Typography variant="caption" color="text.secondary" component="span" sx={{ mr: 2 }}>
                    {formatFileSize(document.size)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" component="span" sx={{ mr: 2 }}>
                    {formatDate(document.uploadTime)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" component="span">
                    {document.type.toUpperCase()}
                  </Typography>
                </React.Fragment>
              }
            />
            <ListItemSecondaryAction>
              <HoverAnimatedBox hoverAnimation="scale">
                <AccessibleIconButton
                  edge="end"
                  onClick={() => onView(document)}
                  size="small"
                  aria-label="查看文档"
                  sx={{ mr: 1 }}
                >
                  <ViewIcon />
                </AccessibleIconButton>
              </HoverAnimatedBox>
              <HoverAnimatedBox hoverAnimation="scale">
                <AccessibleIconButton
                  edge="end"
                  onClick={() => onDelete(document.id)}
                  size="small"
                  color="error"
                  aria-label="删除文档"
                >
                  <DeleteIcon />
                </AccessibleIconButton>
              </HoverAnimatedBox>
            </ListItemSecondaryAction>
          </ListItem>
        </Fade>
      </AnimatedBox>
    </div>
  );
};

const LazyDocumentList: React.FC<LazyDocumentListProps> = ({
  documents,
  onLoadMore,
  onDelete,
  onView,
  hasNextPage,
  isLoading,
  height = 400,
}) => {
  const [loadingItems, setLoadingItems] = useState<Set<number>>(new Set());

  const itemData = useMemo(
    () => ({
      documents,
      onDelete,
      onView,
      isLoading,
    }),
    [documents, onDelete, onView, isLoading]
  );

  // 检查项目是否已加载
  const isItemLoaded = useCallback(
    (index: number) => {
      return !!documents[index];
    },
    [documents]
  );

  // 加载更多项目
  const loadMoreItems = useCallback(
    async (startIndex: number, stopIndex: number) => {
      if (isLoading) return;
      
      // 标记正在加载的项目
      const newLoadingItems = new Set(loadingItems);
      for (let i = startIndex; i <= stopIndex; i++) {
        newLoadingItems.add(i);
      }
      setLoadingItems(newLoadingItems);

      try {
        await onLoadMore(startIndex, stopIndex);
      } finally {
        // 清除加载状态
        setLoadingItems(prev => {
          const newSet = new Set(prev);
          for (let i = startIndex; i <= stopIndex; i++) {
            newSet.delete(i);
          }
          return newSet;
        });
      }
    },
    [onLoadMore, isLoading, loadingItems]
  );

  // 计算总项目数（包括可能需要加载的项目）
  const itemCount = hasNextPage ? documents.length + 10 : documents.length;

  if (documents.length === 0 && !isLoading) {
    return (
      <AnimatedBox animation="fadeInUp">
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '200px',
            color: 'text.secondary',
          }}
        >
          <DocumentIcon sx={{ fontSize: 48, mb: 2, opacity: 0.5 }} />
          <Typography variant="body1">暂无文档</Typography>
          <Typography variant="caption" sx={{ mt: 1 }}>
            上传文档后将在此处显示
          </Typography>
        </Box>
      </AnimatedBox>
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
      <InfiniteLoader
        isItemLoaded={isItemLoaded}
        itemCount={itemCount}
        loadMoreItems={loadMoreItems}
        threshold={5}
      >
        {({ onItemsRendered, ref }: any) => (
          <VirtualList
            ref={ref}
            className="react-window-list"
            height={height}
            width="100%"
            itemCount={itemCount}
            itemSize={80}
            itemData={itemData}
            onItemsRendered={onItemsRendered}
            overscanCount={5}
          >
            {DocumentItem}
          </VirtualList>
        )}
      </InfiniteLoader>
      
      {isLoading && (
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            p: 2,
          }}
        >
          <CircularProgress size={24} sx={{ mr: 1 }} />
          <Typography variant="body2" color="text.secondary">
            加载中...
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default LazyDocumentList;
export type { Document };