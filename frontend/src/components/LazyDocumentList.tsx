import React from 'react';
import {
  Box,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Typography,
  CircularProgress,
  Fade,
  Skeleton,
} from '@mui/material';
import {
  Description as DocumentIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  CheckCircle as CompletedIcon,
  Sync as ProcessingIcon,
  Error as ErrorIcon,
  CloudUpload as UploadedIcon,
  Psychology as MetadataIcon,
  Chat as ChatReadyIcon,
} from '@mui/icons-material';

import { AnimatedBox, HoverAnimatedBox } from './animations';
import { AccessibleIconButton } from './AccessibleButton';
import { DocumentInfo } from '@/types';

// 使用统一的DocumentInfo类型
type Document = DocumentInfo;

interface LazyDocumentListProps {
  documents: Document[];
  onLoadMore?: (startIndex: number, stopIndex: number) => Promise<void>;
  onDelete: (documentId: string) => void;
  onView: (document: Document) => void;
  hasNextPage?: boolean;
  isLoading: boolean;
  height?: number;
}

interface DocumentItemProps {
  document: Document;
  onDelete: (documentId: string) => void;
  onView: (document: Document) => void;
  index: number;
}

const DocumentItem: React.FC<DocumentItemProps> = ({ document, onDelete, onView, index }) => {

  // 获取文档状态显示信息
  const getStatusInfo = (doc: Document) => {
    // 优先使用详细状态字段
    if (doc.chat_ready) {
      return { label: '可聊天', color: 'success' as const, icon: <ChatReadyIcon /> };
    }
    
    if (doc.metadata_generation_status === 'processing') {
      return { label: '生成摘要中', color: 'info' as const, icon: <MetadataIcon /> };
    }
    
    if (doc.vectorization_status === 'processing') {
      return { label: '向量化中', color: 'info' as const, icon: <ProcessingIcon /> };
    }
    
    if (doc.processing_status === 'processing') {
      return { label: '处理中', color: 'info' as const, icon: <ProcessingIcon /> };
    }
    
    // 使用新的状态字段，同时保持对详细状态的支持
    switch (doc.status) {
      case 'uploading':
        return { label: '上传中', color: 'info' as const, icon: <UploadedIcon /> };
      case 'processing':
        return { label: '处理中', color: 'info' as const, icon: <ProcessingIcon /> };
      case 'completed':
        return { label: '已完成', color: 'success' as const, icon: <CompletedIcon /> };
      case 'failed':
        return { label: '失败', color: 'error' as const, icon: <ErrorIcon /> };
      case 'ready':
        return { label: '就绪', color: 'success' as const, icon: <ChatReadyIcon /> };
      // 保持向后兼容的旧状态
      case 'chat_ready':
        return { label: '可聊天', color: 'success' as const, icon: <ChatReadyIcon /> };
      case 'generating_metadata':
        return { label: '生成摘要中', color: 'info' as const, icon: <MetadataIcon /> };
      case 'vectorizing':
        return { label: '向量化中', color: 'info' as const, icon: <ProcessingIcon /> };
      case 'uploaded':
        return { label: '已上传', color: 'primary' as const, icon: <UploadedIcon /> };
      case 'error':
        return { label: '错误', color: 'error' as const, icon: <ErrorIcon /> };
      default:
        return { label: '未知', color: 'default' as const, icon: <ProcessingIcon /> };
    }
  };

  if (!document) {
    return null;
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
                <>
                  <Typography variant="caption" color="text.secondary" component="div">
                    {formatFileSize(document.size)} • {formatDate(document.uploadTime)} • {document.type.toUpperCase()}
                  </Typography>
                  <Box sx={{ mt: 0.5 }}>
                    <Chip
                      size="small"
                      label={getStatusInfo(document).label}
                      color={getStatusInfo(document).color}
                      icon={getStatusInfo(document).icon}
                      sx={{ height: 20, fontSize: '0.7rem' }}
                    />
                  </Box>
                </>
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
                  disabled={document.type !== 'application/pdf'}
                  tooltip={document.type !== 'application/pdf' ? '暂不支持此文档预览' : '查看文档'}
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
  );
};

const LazyDocumentList: React.FC<LazyDocumentListProps> = ({
  documents,
  onDelete,
  onView,
  isLoading,
  height = 400,
}) => {
  if (documents.length === 0 && !isLoading) {
    return (
      <AnimatedBox animation="fadeInUp">
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            height: height,
            color: 'text.secondary',
            textAlign: 'center',
            px: 3,
          }}
        >
          <Box
            sx={{
              width: 80,
              height: 80,
              borderRadius: '50%',
              backgroundColor: 'action.hover',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              mb: 2,
            }}
          >
            <DocumentIcon sx={{ fontSize: 40, color: 'text.disabled' }} />
          </Box>
          <Typography variant="h6" sx={{ mb: 1, fontWeight: 500 }}>
            暂无文档
          </Typography>
          <Typography variant="body2" color="text.secondary">
            您还没有上传任何文档，点击上方的上传按钮开始添加文档
          </Typography>
        </Box>
      </AnimatedBox>
    );
  }

  // 骨架屏组件
  const SkeletonItem = () => (
    <ListItem sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
      <ListItemIcon>
        <Skeleton variant="circular" width={24} height={24} />
      </ListItemIcon>
      <ListItemText
        primary={<Skeleton variant="text" width="60%" height={24} />}
        secondary={
          <>
            <Skeleton variant="text" width="40%" height={16} sx={{ mt: 0.5 }} />
            <Skeleton variant="rectangular" width={80} height={20} sx={{ mt: 0.5, borderRadius: 1 }} />
          </>
        }
      />
      <ListItemSecondaryAction>
        <Skeleton variant="circular" width={32} height={32} sx={{ mr: 1 }} />
        <Skeleton variant="circular" width={32} height={32} />
      </ListItemSecondaryAction>
    </ListItem>
  );

  if (isLoading && documents.length === 0) {
    return (
      <Box sx={{ height: height, overflow: 'auto' }}>
        <List>
          {Array.from({ length: 5 }).map((_, index) => (
            <SkeletonItem key={index} />
          ))}
        </List>
      </Box>
    );
  }

  return (
    <Box sx={{ height: height, overflow: 'auto' }}>
      <List>
        {documents.map((document, index) => (
          <DocumentItem
            key={document.id}
            document={document}
            onDelete={onDelete}
            onView={onView}
            index={index}
          />
        ))}
      </List>
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