import React, { useState, useCallback, useMemo, useEffect } from 'react';
import {
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
  LinearProgress,
  Card,
  CardContent,
  Alert,
  Chip,
  SxProps,
  Theme,
  Fade,
  Slide,
  CircularProgress,
  Stack,
  IconButton,
  Tooltip,
  Avatar,
  Divider,
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
  Refresh as RetryIcon,
  FileUpload as DragIcon,
  Close as CloseIcon,
} from '@mui/icons-material';
import { keyframes } from '@mui/system';

import { documentApi } from '@/services/api';
import { AccessibleButton } from './AccessibleButton';

// Animation keyframes
const pulseAnimation = keyframes`
  0% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.8;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
`;

const slideUpAnimation = keyframes`
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
`;

const progressAnimation = keyframes`
  0% {
    background-position: -200px 0;
  }
  100% {
    background-position: calc(200px + 100%) 0;
  }
`;

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
  originalFile: File;
  status: 'pending' | 'uploading' | 'connected' | 'parsed' | 'chunking' | 'chunked' | 'saved_content' | 'processing' | 'vectorizing' | 'vectorized' | 'generating_metadata' | 'completed' | 'error' | 'uploaded' | 'chat_ready';
  progress: number;
  error?: string;
  uploadResponse?: any;
  documentId?: string;
  canRetry?: boolean;
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
  
  
  const fileInputId = useMemo(() => `modern-file-input-${Math.random().toString(36).substr(2, 9)}`, []);

  // Get supported formats and file size limits
  const acceptedTypes = useMemo(() => {
    if (!supportedFormats) return ['.pdf'];
    return supportedFormats.formats.map(format => format.extension);
  }, [supportedFormats]);
  
  const maxFileSize = useMemo(() => {
    if (!supportedFormats) return 50 * 1024 * 1024;
    return supportedFormats.max_file_size;
  }, [supportedFormats]);

  // Reset files when dialog opens
  useEffect(() => {
    if (open && dialogMode) {
      setFiles([]);
      setIsUploading(false);
    }
  }, [open, dialogMode]);

  // Load supported formats
  useEffect(() => {
    const fetchSupportedFormats = async () => {
      try {
        setIsLoadingFormats(true);
        
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
              description: 'Word文档',
              max_size: 50 * 1024 * 1024,
              mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
              features: ['text_extraction', 'metadata_extraction', 'table_extraction']
            },
            {
              extension: '.pptx',
              format_name: 'PPTX',
              description: 'PowerPoint',
              max_size: 50 * 1024 * 1024,
              mime_type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
              features: ['text_extraction', 'metadata_extraction', 'slide_extraction']
            },
            {
              extension: '.xlsx',
              format_name: 'XLSX',
              description: 'Excel表格',
              max_size: 50 * 1024 * 1024,
              mime_type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
              features: ['text_extraction', 'metadata_extraction', 'table_extraction']
            },
            {
              extension: '.txt',
              format_name: 'TXT',
              description: '纯文本文件',
              max_size: 50 * 1024 * 1024,
              mime_type: 'text/plain',
              features: ['text_extraction']
            },
            {
              extension: '.md',
              format_name: 'Markdown',
              description: 'Markdown文档',
              max_size: 50 * 1024 * 1024,
              mime_type: 'text/markdown',
              features: ['text_extraction', 'structure_preservation']
            }
          ],
          max_file_size: 50 * 1024 * 1024,
          processing_timeout: 300,
          total_formats: 6
        };
        
        setSupportedFormats(fullSupportedFormats);
        
        try {
          const data = await documentApi.getSupportedFormats();
          setSupportedFormats(data);
        } catch (apiError) {
          console.warn('API call failed, using hardcoded configuration:', apiError);
        }
        
      } catch (error) {
        console.error('Failed to set supported formats:', error);
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

  // File validation
  const validateFile = useCallback((file: File): { isValid: boolean; error?: string } => {
    if (file.size > maxFileSize) {
      return {
        isValid: false,
        error: `文件大小超过限制 (${(maxFileSize / 1024 / 1024).toFixed(1)}MB)`
      };
    }

    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!acceptedTypes.includes(fileExtension)) {
      return {
        isValid: false,
        error: `不支持的文件格式 (${fileExtension})`
      };
    }

    if (file.name.length > 255) {
      return {
        isValid: false,
        error: '文件名过长 (最多255个字符)'
      };
    }

    const problematicChars = /[<>:"/\\|?*]/;
    if (problematicChars.test(file.name)) {
      return {
        isValid: false,
        error: '文件名包含不允许的字符'
      };
    }

    return { isValid: true };
  }, [maxFileSize, acceptedTypes]);

  // Get file icon
  const getFileIcon = useCallback((fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    const iconProps = { sx: { fontSize: 24 } };
    
    switch (extension) {
      case 'pdf':
        return <PdfIcon {...iconProps} sx={{ ...iconProps.sx, color: '#d32f2f' }} />;
      case 'doc':
      case 'docx':
        return <DocIcon {...iconProps} sx={{ ...iconProps.sx, color: '#1976d2' }} />;
      case 'ppt':
      case 'pptx':
        return <PptIcon {...iconProps} sx={{ ...iconProps.sx, color: '#ed6c02' }} />;
      case 'xls':
      case 'xlsx':
        return <XlsIcon {...iconProps} sx={{ ...iconProps.sx, color: '#2e7d32' }} />;
      case 'txt':
      case 'md':
        return <TxtIcon {...iconProps} sx={{ ...iconProps.sx, color: '#757575' }} />;
      default:
        return <FileIcon {...iconProps} />;
    }
  }, []);

  // Add files
  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const filesToAdd: FileWithStatus[] = [];
    const fileArray = Array.from(newFiles);

    fileArray.forEach(file => {
      const validation = validateFile(file);
      const fileId = `${file.name}-${file.lastModified}-${Math.random()}`;
      
      if (validation.isValid) {
        filesToAdd.push({
          id: fileId,
          name: file.name,
          size: file.size,
          type: file.type,
          lastModified: file.lastModified,
          originalFile: file,
          status: 'pending',
          progress: 0,
          canRetry: false,
        });
      } else {
        filesToAdd.push({
          id: fileId,
          name: file.name,
          size: file.size,
          type: file.type,
          lastModified: file.lastModified,
          originalFile: file,
          status: 'error',
          progress: 0,
          error: validation.error,
          canRetry: false,
        });
      }
    });

    setFiles(prev => [...prev, ...filesToAdd]);
  }, [validateFile]);

  // Remove file
  const removeFile = useCallback((fileId: string) => {
    setFiles(prev => prev.filter(file => file.id !== fileId));
  }, []);

  // Retry file upload
  const retryFile = useCallback((fileId: string) => {
    setFiles(prev => prev.map(file => 
      file.id === fileId 
        ? { ...file, status: 'pending', progress: 0, error: undefined, canRetry: false }
        : file
    ));
  }, []);

  // Drag and drop handlers
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // A more robust way to handle this is to check relatedTarget, but for now, we'll simplify
    // and rely on a short timeout or a different logic if this becomes buggy.
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    const droppedFiles = e.dataTransfer.files;
    if (droppedFiles.length > 0) {
      addFiles(droppedFiles);
    }
  }, [addFiles]);

  // File input change handler
  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files;
    if (selectedFiles && selectedFiles.length > 0) {
      addFiles(selectedFiles);
    }
    e.target.value = '';
  }, [addFiles]);

  // SSE connection for progress tracking
  const connectSSE = useCallback((documentId: string, fileId: string) => {
    const eventSource = new EventSource(`/api/v1/documents/${documentId}/status-stream`);
    
    const timeout = setTimeout(() => {
      eventSource.close();
      setFiles(prev => prev.map(file => 
        file.id === fileId && file.status === 'processing'
          ? { ...file, status: 'error', error: '处理超时', canRetry: true }
          : file
      ));
    }, 300000); // 5 minutes timeout

    eventSource.onopen = () => {
      console.log(`SSE connection opened for document ${documentId}`);
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('SSE message received:', data);
        
        setFiles(prev => {
          const updatedFiles = prev.map(file => {
            if (file.id === fileId) {
              const updatedFile = { ...file };
              
              if (data.status) {
                updatedFile.status = data.status;
              }
              
              // Map status to progress instead of using backend progress directly
              // This ensures consistent progress display regardless of backend progress values
              const getProgressByStatus = (status: string) => {
                switch (status) {
                  case 'connected':
                    return 5;
                  case 'parsed':
                    return 25;
                  case 'chunking':
                    return 40;
                  case 'chunked':
                    return 55;
                  case 'saved_content':
                    return 70;
                  case 'vectorizing':
                    return 80;
                  case 'vectorized':
                    return 95;
                  case 'chat_ready':
                  case 'completed':
                    return 100;
                  case 'processing':
                    return Math.max(updatedFile.progress || 10, 15); // Keep current progress or minimum 15%
                  case 'uploading':
                    return Math.max(updatedFile.progress || 0, 5); // Keep current progress or minimum 5%
                  default:
                    return updatedFile.progress || 0;
                }
              };
              
              // Update progress based on status
              if (data.status) {
                const newProgress = getProgressByStatus(data.status);
                updatedFile.progress = Math.max(updatedFile.progress || 0, newProgress);
              }
              
              // Handle error status and messages
              if (data.status === 'error' || data.status === 'failed' || data.error) {
                // Use specific error message from SSE if available, otherwise use data.error or data.message
                let errorMessage = data.error || data.message || '处理失败';
                
                // Set error status and message
                updatedFile.status = 'error';
                updatedFile.error = errorMessage;
                updatedFile.canRetry = true;
                
                // Close SSE connection on error
                clearTimeout(timeout);
                eventSource.close();
              } else if (data.error) {
                // Handle general error field
                updatedFile.error = data.error;
                updatedFile.canRetry = true;
              }
              
              if (data.status === 'completed' || data.status === 'chat_ready') {
                clearTimeout(timeout);
                eventSource.close();
                
                // Trigger onUploadSuccess when file reaches completed/chat_ready status
                if (onUploadSuccess) {
                  setTimeout(() => {
                    onUploadSuccess([{
                      file: updatedFile.originalFile,
                      response: updatedFile.uploadResponse || { id: updatedFile.documentId, status: updatedFile.status }
                    }]);
                  }, 0);
                }
              }
              
              return updatedFile;
            }
            return file;
          });
          
          return updatedFiles;
        });
      } catch (error) {
        console.error('Error parsing SSE message:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      clearTimeout(timeout);
      eventSource.close();
      
      setFiles(prev => prev.map(file => 
        file.id === fileId && (file.status === 'processing' || file.status === 'uploading')
          ? { ...file, status: 'error', error: '连接中断', canRetry: true }
          : file
      ));
    };

    return () => {
      clearTimeout(timeout);
      eventSource.close();
    };
  }, [onUploadSuccess]);

  // Upload files
  const uploadFiles = useCallback(async () => {
    const pendingFiles = files.filter(file => file.status === 'pending');
    if (pendingFiles.length === 0) return;

    setIsUploading(true);
    const uploadedDocuments: Array<{ file: File; response: any }> = [];

    for (const file of pendingFiles) {
      try {
        setFiles(prev => prev.map(f => 
          f.id === file.id ? { ...f, status: 'uploading', progress: 0 } : f
        ));

        const response = await documentApi.uploadDocument(file.originalFile);
        console.log('Upload response:', response);

        const documentId = response.document_id;
        if (!documentId) {
          throw new Error('No document_id in response');
        }

        setFiles(prev => prev.map(f => 
          f.id === file.id 
            ? { 
                ...f, 
                status: 'processing', 
                progress: 10, 
                uploadResponse: response,
                documentId: documentId
              } 
            : f
        ));

        uploadedDocuments.push({ file: file.originalFile, response });
        connectSSE(documentId, file.id);

      } catch (error: any) {
        console.error('Upload failed for file:', file.name, error);
        
        let errorMessage = '上传失败';
        let canRetry = true;
        
        if (error.response) {
          const status = error.response.status;
          switch (status) {
            case 413:
              errorMessage = '文件过大';
              canRetry = false;
              break;
            case 415:
              errorMessage = '不支持的文件格式';
              canRetry = false;
              break;
            case 403:
              errorMessage = '权限不足';
              canRetry = false;
              break;
            case 429:
              errorMessage = '请求过于频繁，请稍后重试';
              break;
            case 500:
            case 502:
            case 503:
            case 504:
              errorMessage = '服务器错误，请稍后重试';
              break;
            default:
              errorMessage = `上传失败 (${status})`;
          }
        } else if (error.code === 'NETWORK_ERROR' || !navigator.onLine) {
          errorMessage = '网络连接失败';
        } else if (error.message) {
          errorMessage = error.message;
        }

        setFiles(prev => prev.map(f => 
          f.id === file.id 
            ? { ...f, status: 'error', error: errorMessage, canRetry }
            : f
        ));
      }
    }

    setIsUploading(false);
    
    // onUploadSuccess will be triggered by SSE status updates when files reach completed/chat_ready status
  }, [files, connectSSE, onUploadSuccess]);

  // Check if all files are completed or ready for chat (allow close only when all files are done)
  const canClose = useMemo(() => {
    if (files.length === 0) return true;
    return files.every(file => 
      file.status === 'completed' || file.status === 'chat_ready'
    );
  }, [files]);

  // onUploadSuccess is now handled entirely by SSE status updates above

  // Handle close
  const handleClose = useCallback(() => {
    if (!isUploading && canClose && onClose) {
      onClose();
    }
  }, [isUploading, canClose, onClose]);

  // Format file size
  const formatFileSize = useCallback((bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }, []);

  // Get status color
  const getStatusColor = useCallback((status: FileWithStatus['status']) => {
    switch (status) {
      case 'completed':
      case 'chat_ready':
        return 'success';
      case 'error':
        return 'error';
      case 'uploading':
      case 'processing':
      case 'vectorizing':
      case 'generating_metadata':
        return 'primary';
      default:
        return 'default';
    }
  }, []);

  // Get status text
  const getStatusText = useCallback((status: FileWithStatus['status']) => {
    switch (status) {
      case 'pending':
        return '等待上传';
      case 'uploading':
        return '上传中';
      case 'connected':
        return '连接中';
      case 'parsed':
        return '解析完成';
      case 'chunking':
        return '分块中';
      case 'chunked':
        return '分块完成';
      case 'saved_content':
        return '内容已保存';
      case 'processing':
        return '处理中';
      case 'vectorizing':
        return '向量化中';
      case 'vectorized':
        return '向量化完成';
      case 'generating_metadata':
        return '生成元数据';
      case 'completed':
      case 'chat_ready':
        return '完成';
      case 'error':
        return '错误';
      default:
        return '处理中';
    }
  }, []);

  // Render file list
  const renderFileList = () => {
    if (files.length === 0) return null;

    return (
      <Box sx={{ mt: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: 1,
          mb: 2
        }}>
          <FileIcon />
          文件列表 ({files.length})
        </Typography>
        
        <Stack spacing={2}>
          {files.map((file, index) => (
            <Fade in timeout={300 + index * 100} key={file.id}>
              <Card 
                elevation={2}
                sx={{
                  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                  animation: `${slideUpAnimation} 0.5s ease-out ${index * 0.1}s both`,
                  '&:hover': {
                    elevation: 4,
                    transform: 'translateY(-2px)',
                    boxShadow: '0 8px 25px rgba(0,0,0,0.15)',
                  }
                }}
              >
                <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Avatar sx={{ 
                      bgcolor: 'transparent',
                      border: '2px solid',
                      borderColor: `${getStatusColor(file.status)}.main`,
                    }}>
                      {getFileIcon(file.name)}
                    </Avatar>
                    
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Typography 
                        variant="subtitle1" 
                        sx={{ 
                          fontWeight: 600,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}
                      >
                        {file.name}
                      </Typography>
                      
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 0.5 }}>
                        <Typography variant="body2" color="text.secondary">
                          {formatFileSize(file.size)}
                        </Typography>
                        
                        <Chip 
                          label={getStatusText(file.status)}
                          color={getStatusColor(file.status)}
                          size="small"
                          sx={{ 
                            fontWeight: 500,
                            animation: (file.status === 'uploading' || file.status === 'connected' || file.status === 'parsed' || file.status === 'chunking' || file.status === 'chunked' || file.status === 'saved_content' || file.status === 'processing' || file.status === 'vectorizing' || file.status === 'vectorized' || file.status === 'generating_metadata')
                              ? `${pulseAnimation} 2s infinite` 
                              : 'none'
                          }}
                        />
                      </Box>
                      
                      {file.error && (
                        <Alert 
                          severity="error" 
                          sx={{ mt: 1, py: 0.5 }}
                          action={
                            file.canRetry ? (
                              <Tooltip title="重试">
                                <IconButton
                                  size="small"
                                  onClick={() => retryFile(file.id)}
                                  sx={{ ml: 1 }}
                                >
                                  <RetryIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            ) : undefined
                          }
                        >
                          {file.error}
                        </Alert>
                      )}
                      
                      {(file.status === 'uploading' || file.status === 'connected' || file.status === 'parsed' || file.status === 'chunking' || file.status === 'chunked' || file.status === 'saved_content' || file.status === 'processing' || file.status === 'vectorizing' || file.status === 'vectorized' || file.status === 'generating_metadata') && (
                        <Box sx={{ mt: 1 }}>
                          <LinearProgress 
                            variant="determinate" 
                            value={file.progress} 
                            sx={{
                              height: 6,
                              borderRadius: 3,
                              backgroundColor: 'rgba(0,0,0,0.1)',
                              '& .MuiLinearProgress-bar': {
                                borderRadius: 3,
                                background: file.status === 'uploading' 
                                  ? 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)'
                                  : 'linear-gradient(90deg, #f093fb 0%, #f5576c 100%)',
                                '&::after': {
                                  content: '""',
                                  position: 'absolute',
                                  top: 0,
                                  left: 0,
                                  bottom: 0,
                                  right: 0,
                                  background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)',
                                  animation: `${progressAnimation} 2s infinite`,
                                }
                              }
                            }}
                          />
                          <Typography 
                            variant="caption" 
                            color="text.secondary"
                            sx={{ mt: 0.5, display: 'block' }}
                          >
                            {file.progress}%
                          </Typography>
                        </Box>
                      )}
                    </Box>
                    
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {file.status === 'completed' || file.status === 'chat_ready' ? (
                        <Tooltip title="上传成功">
                          <SuccessIcon color="success" sx={{ fontSize: 24 }} />
                        </Tooltip>
                      ) : file.status === 'error' ? (
                        <Tooltip title="上传失败">
                          <ErrorIcon color="error" sx={{ fontSize: 24 }} />
                        </Tooltip>
                      ) : (file.status === 'uploading' || file.status === 'processing' || file.status === 'vectorizing' || file.status === 'generating_metadata') ? (
                        <Tooltip title="处理中">
                          <CircularProgress size={24} thickness={4} />
                        </Tooltip>
                      ) : null}
                      
                      <Tooltip title="删除">
                        <IconButton
                          size="small"
                          onClick={() => removeFile(file.id)}
                          disabled={file.status === 'uploading' || file.status === 'connected' || file.status === 'parsed' || file.status === 'chunking' || file.status === 'chunked' || file.status === 'saved_content' || file.status === 'processing' || file.status === 'vectorizing' || file.status === 'vectorized' || file.status === 'generating_metadata'}
                          sx={{ 
                            color: 'text.secondary',
                            '&:hover': {
                              color: 'error.main',
                              backgroundColor: 'error.light',
                            }
                          }}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Fade>
          ))}
        </Stack>
      </Box>
    );
  };

  // Upload area component
  const uploadArea = (
    <Box
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      sx={{
        border: '2px dashed',
        borderColor: isDragging ? 'primary.main' : 'grey.300',
        borderRadius: 3,
        p: 4,
        textAlign: 'center',
        cursor: 'pointer',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        background: isDragging 
          ? 'linear-gradient(135deg, rgba(25, 118, 210, 0.1) 0%, rgba(25, 118, 210, 0.05) 100%)'
          : 'linear-gradient(135deg, rgba(0, 0, 0, 0.02) 0%, rgba(0, 0, 0, 0.01) 100%)',
        backdropFilter: 'blur(10px)',
        position: 'relative',
        overflow: 'hidden',
        '&:hover': {
          borderColor: 'primary.main',
          backgroundColor: 'rgba(25, 118, 210, 0.04)',
          transform: 'translateY(-2px)',
          boxShadow: '0 8px 25px rgba(0,0,0,0.1)',
        },
        '&::before': {
          content: '""',
          position: 'absolute',
          top: 0,
          left: '-100%',
          width: '100%',
          height: '100%',
          background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)',
          transition: 'left 0.5s',
        },
        '&:hover::before': {
          left: '100%',
        }
      }}
      onClick={() => document.getElementById(fileInputId)?.click()}
    >
      <input
        id={fileInputId}
        type="file"
        multiple
        accept={acceptedTypes.join(',')}
        onChange={handleFileInputChange}
        style={{ display: 'none' }}
      />
      
      <Box sx={{ 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center', 
        gap: 2,
        position: 'relative',
        zIndex: 1
      }}>
        <Avatar sx={{ 
          width: 64, 
          height: 64, 
          bgcolor: 'primary.main',
          animation: isDragging ? `${pulseAnimation} 1s infinite` : 'none',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          boxShadow: '0 8px 32px rgba(102, 126, 234, 0.3)',
        }}>
          {isDragging ? <DragIcon sx={{ fontSize: 32 }} /> : <UploadIcon sx={{ fontSize: 32 }} />}
        </Avatar>
        
        <Box>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
            {isDragging ? '释放文件以上传' : '拖拽文件到此处或点击选择'}
          </Typography>
          
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            支持多文件上传，最大 {(maxFileSize / 1024 / 1024).toFixed(0)}MB
          </Typography>
          
          {supportedFormats && (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'center' }}>
              {supportedFormats.formats.map((format) => (
                <Chip
                  key={format.extension}
                  label={format.format_name}
                  size="small"
                  variant="outlined"
                  sx={{
                    borderColor: 'primary.main',
                    color: 'primary.main',
                    '&:hover': {
                      backgroundColor: 'primary.main',
                      color: 'primary.contrastText',
                    }
                  }}
                />
              ))}
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  );

  if (!dialogMode) {
    return (
      <AccessibleButton
        variant={variant}
        size={size}
        startIcon={<UploadIcon />}
        onClick={() => document.getElementById(fileInputId)?.click()}
        sx={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          '&:hover': {
            background: 'linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%)',
            transform: 'translateY(-2px)',
            boxShadow: '0 8px 25px rgba(102, 126, 234, 0.3)',
          },
          ...sx
        }}
      >
        上传文档
        <input
          id={fileInputId}
          type="file"
          multiple
          accept={acceptedTypes.join(',')}
          onChange={handleFileInputChange}
          style={{ display: 'none' }}
        />
      </AccessibleButton>
    );
  }

  return (
    <Dialog 
      open={open} 
      onClose={canClose ? handleClose : undefined}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 3,
          background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.95) 100%)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.2)',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.1)',
        }
      }}
      TransitionComponent={Slide}
      TransitionProps={{ direction: 'up' } as any}
    >
      <DialogTitle sx={{ 
        py: 2.5,
        px: 3,
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <UploadIcon />
          文档上传
        </Box>
        <IconButton
          onClick={onClose}
          sx={{
            color: 'white',
            '&:hover': {
              backgroundColor: 'rgba(255, 255, 255, 0.1)',
            }
          }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      
      <DialogContent sx={{ p: 3, pt: 2 }}>
        {isLoadingFormats ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            <Box sx={{ mt: 1, mb: 2 }}>
              {uploadArea}
            </Box>
            {renderFileList()}
          </>
        )}
      </DialogContent>
      
      <Divider />
      
      <DialogActions sx={{ p: 3, pt: 2, gap: 2 }}>
        <AccessibleButton 
          onClick={handleClose}
          disabled={isUploading || !canClose}
          variant="outlined"
        >
          {!canClose ? '处理中...' : '取消'}
        </AccessibleButton>
        
        <AccessibleButton
          onClick={uploadFiles}
          disabled={isUploading || files.filter(f => f.status === 'pending').length === 0}
          variant="contained"
          startIcon={isUploading ? <CircularProgress size={20} /> : <UploadIcon />}
          sx={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            '&:hover': {
              background: 'linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%)',
            }
          }}
        >
          {isUploading ? '上传中...' : `上传 (${files.filter(f => f.status === 'pending').length})`}
        </AccessibleButton>
      </DialogActions>
    </Dialog>
  );
};

export default DocumentUploader;