import React, { useState, useCallback, useMemo, useEffect } from 'react';
import {
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  Alert,
  Paper,
  Chip,
  SxProps,
  Theme,
} from '@mui/material';
import {
  CloudUpload as UploadIcon,
  Description as FileIcon,
  Delete as DeleteIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  PictureAsPdf as PdfIcon,
  Article as DocIcon,
  Slideshow as PptIcon,
  TableChart as XlsIcon,
  TextFields as TxtIcon,
} from '@mui/icons-material';

import { documentApi } from '@/services/api';

import { AnimatedBox, HoverAnimatedBox } from './animations';
import LazyDocumentList from './LazyDocumentList';
import { AccessibleButton, AccessibleIconButton } from './AccessibleButton';

interface SupportedFormat {
  extension: string;
  format_name: string;
  description: string;
  max_size: number;
  mime_type: string;
  features: string[];
}

interface SupportedFormatsResponse {
  formats: SupportedFormat[];
  max_file_size: number;
  processing_timeout: number;
  total_formats: number;
}

interface DocumentUploaderProps {
  open?: boolean;
  onClose?: () => void;
  onUploadSuccess?: (documents: Array<{ file: File; response: any }>) => void;
  dialogMode?: boolean;
  variant?: 'text' | 'outlined' | 'contained';
  size?: 'small' | 'medium' | 'large';
  sx?: SxProps<Theme>;
}

interface FileWithStatus {
  id: string;
  name: string;
  size: number;
  type: string;
  lastModified: number;
  // File methods
  originalFile: File;
  // Upload status - matching DocumentInfo status types
  status: 'processing' | 'completed' | 'error' | 'uploaded' | 'vectorizing' | 'generating_metadata' | 'chat_ready';
  progress: number;
  error?: string;
  uploadResponse?: any;
  // Blob methods
  stream: () => ReadableStream<Uint8Array>;
  text: () => Promise<string>;
  arrayBuffer: () => Promise<ArrayBuffer>;
  slice: (start?: number, end?: number, contentType?: string) => Blob;
}

const DocumentUploader: React.FC<DocumentUploaderProps> = ({
  open = false,
  onClose,
  onUploadSuccess,
  dialogMode = false,
  variant = 'outlined',
  size = 'medium',
  sx,
}) => {
  const [files, setFiles] = useState<FileWithStatus[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [supportedFormats, setSupportedFormats] = useState<SupportedFormatsResponse | null>(null);
  const [isLoadingFormats, setIsLoadingFormats] = useState(true);
  
  // Generate unique ID for file input to avoid conflicts
  const fileInputId = useMemo(() => `file-input-${Math.random().toString(36).substr(2, 9)}`, []);
  
  // 判断是否使用虚拟化列表（文件数量超过20条时）
  const shouldUseVirtualization = useMemo(() => files.length > 20, [files.length]);

  // 从支持的格式中提取文件类型和最大文件大小
  const acceptedTypes = useMemo(() => {
    if (!supportedFormats) return ['.pdf']; // 默认支持PDF
    return supportedFormats.formats.map(format => format.extension);
  }, [supportedFormats]);
  
  const maxFileSize = useMemo(() => {
    if (!supportedFormats) return 50 * 1024 * 1024; // 默认50MB
    return supportedFormats.max_file_size;
  }, [supportedFormats]);

  // 获取支持的文档格式
  useEffect(() => {
    const fetchSupportedFormats = async () => {
      try {
        setIsLoadingFormats(true);
        console.log('Fetching supported formats...');
        
        // 直接使用完整的支持格式配置，包含所有多文档格式
        const fullSupportedFormats = {
          formats: [
            {
              extension: '.pdf',
              format_name: 'PDF',
              description: 'PDF文档',
              max_size: 50 * 1024 * 1024,
              mime_type: 'application/pdf',
              features: ['text_extraction', 'metadata_extraction']
            },
            {
              extension: '.docx',
              format_name: 'DOCX',
              description: 'Microsoft Word文档',
              max_size: 50 * 1024 * 1024,
              mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
              features: ['text_extraction', 'metadata_extraction', 'table_extraction']
            },
            {
              extension: '.pptx',
              format_name: 'PPTX',
              description: 'Microsoft PowerPoint演示文稿',
              max_size: 50 * 1024 * 1024,
              mime_type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
              features: ['text_extraction', 'metadata_extraction', 'slide_extraction']
            },
            {
              extension: '.xlsx',
              format_name: 'XLSX',
              description: 'Microsoft Excel电子表格',
              max_size: 50 * 1024 * 1024,
              mime_type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
              features: ['text_extraction', 'metadata_extraction', 'table_extraction']
            },
            {
              extension: '.txt',
              format_name: 'TXT',
              description: '纯文本文件',
              max_size: 10 * 1024 * 1024,
              mime_type: 'text/plain',
              features: ['text_extraction']
            },
            {
              extension: '.md',
              format_name: 'Markdown',
              description: 'Markdown文档',
              max_size: 10 * 1024 * 1024,
              mime_type: 'text/markdown',
              features: ['text_extraction', 'structure_extraction']
            }
          ],
          max_file_size: 50 * 1024 * 1024,
          processing_timeout: 300,
          total_formats: 6
        };
        
        console.log('Using full supported formats configuration');
        console.log('Supported formats:', fullSupportedFormats.formats.map(f => f.extension));
        setSupportedFormats(fullSupportedFormats);
        
        // 尝试从API获取最新配置（但不阻塞用户操作）
        try {
          const data = await documentApi.getSupportedFormats();
          console.log('API returned supported formats:', data);
          setSupportedFormats(data);
        } catch (apiError) {
          console.warn('API call failed, using hardcoded configuration:', apiError);
        }
        
      } catch (error) {
        console.error('Failed to set supported formats:', error);
        // 最小化配置作为最后的备选
        setSupportedFormats({
          formats: [{ 
            extension: '.pdf', 
            format_name: 'PDF', 
            description: 'PDF文档', 
            max_size: 50 * 1024 * 1024, 
            mime_type: 'application/pdf',
            features: ['text_extraction', 'metadata_extraction']
          }],
          max_file_size: 50 * 1024 * 1024,
          processing_timeout: 300,
          total_formats: 1
        });
      } finally {
        setIsLoadingFormats(false);
      }
    };

    fetchSupportedFormats();
  }, []);

  const validateFile = (file: File): string | null => {
    const extension = '.' + file.name.split('.').pop()?.toLowerCase();
    console.log('Validating file:', file.name);
    console.log('Extracted extension:', extension);
    console.log('Accepted types:', acceptedTypes);
    console.log('Supported formats:', supportedFormats);
    
    if (!acceptedTypes.includes(extension)) {
      const supportedFormatsText = supportedFormats?.formats.map(f => f.extension).join(', ') || '.pdf';
      const errorMsg = `不支持的文件类型: ${extension}，支持的格式: ${supportedFormatsText}`;
      console.error('File validation failed:', errorMsg);
      return errorMsg;
    }
    if (file.size > maxFileSize) {
      const maxSizeMB = Math.round(maxFileSize / 1024 / 1024);
      const errorMsg = `文件大小超过限制: ${(file.size / 1024 / 1024).toFixed(1)}MB > ${maxSizeMB}MB`;
      console.error('File size validation failed:', errorMsg);
      return errorMsg;
    }
    console.log('File validation passed');
    return null;
  };

  // 根据文件扩展名获取对应的图标
  const getFileIcon = (filename: string) => {
    const extension = '.' + filename.split('.').pop()?.toLowerCase();
    switch (extension) {
      case '.pdf':
        return <PdfIcon />;
      case '.docx':
      case '.doc':
        return <DocIcon />;
      case '.pptx':
      case '.ppt':
        return <PptIcon />;
      case '.xlsx':
      case '.xls':
        return <XlsIcon />;
      case '.txt':
      case '.md':
        return <TxtIcon />;
      default:
        return <FileIcon />;
    }
  };

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const fileArray = Array.from(newFiles);
    const validFiles: FileWithStatus[] = [];

    fileArray.forEach((file) => {
      const error = validateFile(file);
      // 创建一个包含File属性和额外状态属性的新对象
      const fileWithStatus = {
        // 复制File对象的基本属性
        name: file.name,
        size: file.size,
        type: file.type,
        lastModified: file.lastModified,
        // 保持原始File对象的引用以便后续使用
        originalFile: file,
        // 添加状态属性
        id: `${Date.now()}-${Math.random()}`,
        status: error ? 'error' : 'processing',
        progress: 0,
        error: error || undefined,
        // 添加File对象的方法
        stream: file.stream.bind(file),
        text: file.text.bind(file),
        arrayBuffer: file.arrayBuffer.bind(file),
        slice: file.slice.bind(file)
      } as FileWithStatus;
      
      validFiles.push(fileWithStatus);
    });

    setFiles((prev) => [...prev, ...validFiles]);
  }, []);

  const removeFile = (fileId: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFiles = e.dataTransfer.files;
    addFiles(droppedFiles);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      addFiles(e.target.files);
    }
  };

  const uploadFiles = async () => {
    const pendingFiles = files.filter((f) => f.status === 'processing');
    if (pendingFiles.length === 0) return;

    setIsUploading(true);
    let updatedFiles = [...files];
    const totalFilesToUpload = pendingFiles.length; // 保存原始待上传文件数量

    for (const file of pendingFiles) {
      try {
        // 更新状态为上传中
        setFiles((prev) =>
          prev.map((f) =>
            f.id === file.id ? { ...f, status: 'uploaded', progress: 0 } : f
          )
        );

        // 模拟上传进度
        const progressInterval = setInterval(() => {
          setFiles((prev) =>
            prev.map((f) =>
              f.id === file.id && f.progress < 90
                ? { ...f, progress: f.progress + 10 }
                : f
            )
          );
        }, 200);

        // 上传文件
        const response = await documentApi.uploadDocument(file.originalFile);

        clearInterval(progressInterval);

        // 更新状态为成功，保存响应信息
        setFiles((prev) => {
          const newFiles = prev.map((f) =>
            f.id === file.id
              ? { 
                  ...f, 
                  status: 'completed' as const, 
                  progress: 100,
                  // 保存上传响应信息
                  uploadResponse: response
                }
              : f
          );
          updatedFiles = newFiles;
          return newFiles;
        });
      } catch (error) {
        // 更新状态为失败
        setFiles((prev) => {
          const newFiles = prev.map((f) =>
            f.id === file.id
              ? {
                  ...f,
                  status: 'error' as const,
                  progress: 0,
                  error: error instanceof Error ? error.message : '上传失败',
                }
              : f
          );
          updatedFiles = newFiles;
          return newFiles;
        });
      }
    }

    setIsUploading(false);

    // 使用更新后的文件状态来获取成功文件
    const successFiles = updatedFiles.filter((f) => f.status === 'completed');
    if (successFiles.length > 0 && onUploadSuccess) {
      // 传递文件和响应信息
      const documentsWithResponse = successFiles.map(file => ({
        file: file.originalFile,
        response: file.uploadResponse
      }));
      onUploadSuccess(documentsWithResponse);
    }
    
    // 检查是否应该自动关闭上传页面
    // 条件：completed、error状态，或者chat_ready状态（表示文档已具备聊天交互功能）
    const finishedFiles = updatedFiles.filter((f) => 
      f.status === 'completed' || f.status === 'error' || f.status === 'chat_ready'
    );
    
    if (dialogMode && finishedFiles.length === totalFilesToUpload) {
      setTimeout(() => {
        handleClose();
      }, 1500); // 延迟1.5秒关闭，让用户看到最终状态
    }
  };

  const handleClose = () => {
    if (!isUploading) {
      setFiles([]);
      onClose?.();
    }
  };

  const renderFileList = () => {
     if (shouldUseVirtualization) {
       return (
         <LazyDocumentList
           documents={files.map(file => ({
             id: file.id,
             name: file.name,
             size: file.size,
             type: file.name.split('.').pop() || '',
             uploadTime: new Date().toISOString(),
             status: file.status,
             progress: file.progress,
             error: file.error
           }))}
           onDelete={removeFile}
           onLoadMore={async () => {}}
           onView={() => {}}
           hasNextPage={false}
           height={300}
           isLoading={isUploading}
         />
       );
     }
     
     return (
       <List sx={{ maxHeight: 300, overflow: 'auto' }}>
         {files.map((file, index) => (
           <AnimatedBox 
             key={file.id} 
             animation="fadeInLeft" 
             duration="0.4s" 
             delay={`${index * 0.1}s`}
           >
             <HoverAnimatedBox hoverAnimation="scale">
               <ListItem 
                 divider
                 sx={{
                   borderRadius: 2,
                   mb: 1,
                   transition: 'all 0.2s ease-in-out',
                   '&:hover': {
                     bgcolor: 'action.hover',
                   },
                 }}
               >
                 <ListItemIcon>
                   <AnimatedBox 
                     animation={file.status === 'uploaded' ? 'pulse' : undefined} 
                     duration="1s"
                   >
                     {file.status === 'completed' ? (
                       <SuccessIcon color="success" />
                     ) : file.status === 'error' ? (
                       <ErrorIcon color="error" />
                     ) : (
                       getFileIcon(file.name)
                     )}
                   </AnimatedBox>
                 </ListItemIcon>
                 <ListItemText
                   primary={file.name}
                   secondary={
                     <React.Fragment>
                       <Typography variant="caption" color="text.secondary" component="span" display="block">
                         {file.size ? (file.size / 1024 / 1024).toFixed(1) : '0.0'} MB
                       </Typography>
                       {file.status === 'uploaded' && (
                         <LinearProgress
                           variant="determinate"
                           value={file.progress}
                           sx={{ mt: 0.5 }}
                         />
                       )}
                       {file.status === 'completed' && (
                         <Typography variant="caption" color="success.main" component="span" display="block">
                           上传成功
                         </Typography>
                       )}
                       {file.error && (
                         <Typography variant="caption" color="error" component="span" display="block">
                           {file.error}
                         </Typography>
                       )}
                     </React.Fragment>
                   }
                 />
                 <ListItemSecondaryAction>
                   <HoverAnimatedBox hoverAnimation="scale">
                     <AccessibleIconButton
                       edge="end"
                       onClick={() => removeFile(file.id)}
                       disabled={isUploading}
                       size="small"
                       aria-label="删除文件"
                     >
                       <DeleteIcon />
                     </AccessibleIconButton>
                   </HoverAnimatedBox>
                 </ListItemSecondaryAction>
               </ListItem>
             </HoverAnimatedBox>
           </AnimatedBox>
         ))}
       </List>
     );
   };

  const uploadArea = (
    <AnimatedBox animation="fadeInUp" duration="0.6s">
      <HoverAnimatedBox hoverAnimation="scale">
        <Paper
          variant="outlined"
          sx={{
            p: 4,
            textAlign: 'center',
            borderStyle: 'dashed',
            borderWidth: 2,
            borderColor: isDragging ? 'primary.main' : 'divider',
            bgcolor: isDragging ? 'primary.light' : 'background.paper',
            cursor: 'pointer',
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            borderRadius: 3,
            '&:hover': {
              borderColor: 'primary.main',
              bgcolor: 'primary.light',
              transform: 'translateY(-4px) scale(1.02)',
              boxShadow: '0 12px 40px rgba(0, 0, 0, 0.15)',
            },
          }}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => document.getElementById(fileInputId)?.click()}
        >
          <AnimatedBox animation={isDragging ? 'bounce' : 'pulse'} duration="1.5s">
            <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
          </AnimatedBox>
          <Typography variant="h6" gutterBottom>
            拖拽文件到此处或点击上传
          </Typography>
          {isLoadingFormats ? (
            <Typography variant="body2" color="text.secondary" gutterBottom>
              正在加载支持的格式...
            </Typography>
          ) : (
            <>
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  支持的格式:
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'center' }}>
                  {supportedFormats?.formats.map((format) => (
                    <Chip
                      key={format.extension}
                      label={`${format.extension} (${format.description})`}
                      size="small"
                      variant="outlined"
                      icon={getFileIcon(`file${format.extension}`)}
                    />
                  ))}
                </Box>
              </Box>
              <Typography variant="caption" color="text.secondary">
                最大文件大小: {Math.round(maxFileSize / 1024 / 1024)}MB
              </Typography>
            </>
          )}
          <input
            id={fileInputId}
            type="file"
            multiple
            accept={acceptedTypes.join(',')}
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
        </Paper>
      </HoverAnimatedBox>
    </AnimatedBox>
  );

  if (!dialogMode) {
    return (
      <HoverAnimatedBox hoverAnimation="scale">
        <AccessibleButton
          variant={variant}
          size={size}
          startIcon={<UploadIcon />}
          onClick={() => document.getElementById(fileInputId)?.click()}
          sx={sx}
          aria-label="上传文档"
        >
          上传文档
          <input
            id={fileInputId}
            type="file"
            multiple
            accept={acceptedTypes.join(',')}
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
        </AccessibleButton>
      </HoverAnimatedBox>
    );
  }

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      disableEscapeKeyDown={isUploading}
    >
      <DialogTitle>
        <AnimatedBox animation="fadeInUp" duration="0.5s">
          上传文档
          <AnimatedBox animation="fadeInUp" delay="0.2s" duration="0.5s">
            <Typography variant="body2" color="text.secondary">
              {isLoadingFormats 
                ? '正在加载支持的格式...' 
                : `支持 ${acceptedTypes.length} 种文档格式`
              }
            </Typography>
          </AnimatedBox>
        </AnimatedBox>
      </DialogTitle>
      
      <DialogContent>
        {uploadArea}
        
        {files.length > 0 && (
          <AnimatedBox animation="fadeInUp" delay="0.3s" duration="0.5s">
            <Box sx={{ mt: 3 }}>
              <AnimatedBox animation="fadeInLeft" delay="0.1s">
                <Typography variant="subtitle2" gutterBottom>
                  文件列表 ({files.length})
                </Typography>
              </AnimatedBox>
              {renderFileList()}
            </Box>
          </AnimatedBox>
        )}

        {files.some((f) => f.status === 'error') && (
          <AnimatedBox animation="fadeInUp" delay="0.4s">
            <Alert severity="warning" sx={{ mt: 2 }}>
              部分文件上传失败，请检查文件格式和大小
            </Alert>
          </AnimatedBox>
        )}
      </DialogContent>

      <DialogActions sx={{ p: 3, gap: 2 }}>
        <HoverAnimatedBox hoverAnimation="scale">
          <AccessibleButton
            onClick={handleClose}
            disabled={isUploading}
            variant="outlined"
            aria-label="取消上传"
            sx={{
              borderRadius: 2,
              textTransform: 'none',
              px: 3,
              py: 1.5,
              fontSize: '0.95rem',
              fontWeight: 500,
              borderColor: 'divider',
              color: 'text.secondary',
              '&:hover': {
                borderColor: 'primary.main',
                backgroundColor: 'action.hover',
              },
            }}
          >
            取消
          </AccessibleButton>
        </HoverAnimatedBox>
        <AnimatedBox animation={isUploading ? 'pulse' : undefined}>
          <HoverAnimatedBox hoverAnimation="scale">
            <AccessibleButton
              onClick={uploadFiles}
              variant="contained"
              disabled={
                isUploading ||
                files.length === 0 ||
                !files.some((f) => f.status === 'processing')
              }
              loading={isUploading}
              startIcon={<UploadIcon />}
              aria-label={isUploading ? '正在上传文件' : '开始上传文件'}
              sx={{
                borderRadius: 2,
                textTransform: 'none',
                px: 3,
                py: 1.5,
                fontSize: '0.95rem',
                fontWeight: 500,
                boxShadow: 'none',
                '&:hover': {
                  boxShadow: '0 4px 12px rgba(25, 118, 210, 0.3)',
                },
                '&:disabled': {
                  backgroundColor: 'action.disabledBackground',
                  color: 'action.disabled',
                },
              }}
            >
              {isUploading ? '上传中...' : '开始上传'}
            </AccessibleButton>
          </HoverAnimatedBox>
        </AnimatedBox>
      </DialogActions>
    </Dialog>
  );
};

export default DocumentUploader;