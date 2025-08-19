import React, { useState, useRef, KeyboardEvent } from 'react';
import {
  Paper,
  Tooltip,
} from '@mui/material';
import {
  Send as SendIcon,
  Mic as MicIcon,
  AttachFile as AttachFileIcon,
} from '@mui/icons-material';
import { AnimatedBox, HoverAnimatedBox, Ripple } from './animations';
import AccessibleInput from './AccessibleInput';
import { AccessibleIconButton } from './AccessibleButton';
import { useAccessibility } from './AccessibilityProvider';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  disabled = false,
  placeholder = '输入消息...',
}) => {
  const [message, setMessage] = useState('');
  const [isComposing, setIsComposing] = useState(false);
  const [showRipple, setShowRipple] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { announceMessage } = useAccessibility();

  const handleSend = () => {
    const trimmedMessage = message.trim();
    if (trimmedMessage && !disabled) {
      setShowRipple(true);
      onSendMessage(trimmedMessage);
      setMessage('');
      inputRef.current?.focus();
      announceMessage('消息已发送');
      setTimeout(() => setShowRipple(false), 100);
    }
  };

  const handleKeyPress = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !isComposing) {
      event.preventDefault();
      handleSend();
    }
  };

  const handleCompositionStart = () => {
    setIsComposing(true);
  };

  const handleCompositionEnd = () => {
    setIsComposing(false);
  };

  return (
    <AnimatedBox animation="fadeInUp" duration="0.4s">
      <HoverAnimatedBox hoverAnimation="scale">
        <Paper
          component="form"
          role="search"
          aria-label="消息输入区域"
          elevation={0}
          sx={{
            display: 'flex',
            alignItems: 'flex-end',
            gap: 1.5,
            p: 1.5,
            border: '2px solid',
            borderColor: message.trim() ? 'primary.main' : 'divider',
            borderRadius: '24px',
            bgcolor: 'background.paper',
            position: 'relative',
            overflow: 'hidden',
            transition: 'all 0.2s ease-in-out',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.08)',
            '&:hover': {
              borderColor: 'primary.main',
              boxShadow: '0 6px 25px rgba(0, 0, 0, 0.12)',
            },
            '&:focus-within': {
              borderColor: 'primary.main',
              boxShadow: '0 0 0 3px rgba(103, 126, 234, 0.1)',
            },
          }}
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
        >
          <Ripple trigger={showRipple} />
      {/* 现代化附件按钮 */}
      <Tooltip title="附加文件">
        <HoverAnimatedBox hoverAnimation="scale">
          <AccessibleIconButton
            size="medium"
            disabled={disabled}
            aria-label="附加文件"
            sx={{ 
              mb: 0.5,
              color: 'text.secondary',
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                bgcolor: 'action.hover',
                color: 'primary.main',
                transform: 'rotate(15deg)',
              },
            }}
          >
            <AttachFileIcon fontSize="small" />
          </AccessibleIconButton>
        </HoverAnimatedBox>
      </Tooltip>

      {/* 输入框 */}
      <AccessibleInput
        ref={inputRef}
        label="消息输入"
        description="输入您的消息，按Enter发送，Shift+Enter换行"
        fullWidth
        multiline
        maxRows={4}
        variant="standard"
        placeholder={placeholder}
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyPress={handleKeyPress}
        onCompositionStart={handleCompositionStart}
        onCompositionEnd={handleCompositionEnd}
        disabled={disabled}
        showCharacterCount
        maxLength={2000}
        data-testid="search-input"
        InputProps={{
          disableUnderline: true,
          sx: {
            fontSize: '0.95rem',
            lineHeight: 1.5,
          },
        }}
        sx={{
          '& .MuiInputBase-root': {
            py: 1,
          },
        }}
      />

      {/* 现代化语音按钮 */}
      <Tooltip title="语音输入">
        <HoverAnimatedBox hoverAnimation="scale">
          <AccessibleIconButton
            size="medium"
            disabled={disabled}
            aria-label="语音输入"
            sx={{ 
              mb: 0.5,
              color: 'text.secondary',
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                bgcolor: 'action.hover',
                color: 'primary.main',
                animation: 'pulse 1s infinite',
                '@keyframes pulse': {
                  '0%': { transform: 'scale(1)' },
                  '50%': { transform: 'scale(1.1)' },
                  '100%': { transform: 'scale(1)' },
                },
              },
            }}
          >
            <MicIcon fontSize="small" />
          </AccessibleIconButton>
        </HoverAnimatedBox>
      </Tooltip>

      {/* 现代化发送按钮 */}
      <Tooltip title="发送消息 (Enter)">
        <AnimatedBox
                animation={message.trim() ? "fadeInUp" : undefined}
                duration="0.3s"
              >
          <HoverAnimatedBox hoverAnimation="scale">
            <AccessibleIconButton
              onClick={handleSend}
              disabled={disabled || !message.trim()}
              loading={disabled}
              loadingText="发送中"
              successMessage="消息发送成功"
              tooltip="发送消息"
              shortcut="Enter"
              aria-label="发送消息"
              sx={{
                mb: 0.5,
                width: 40,
                height: 40,
                bgcolor: message.trim() && !disabled ? 'primary.main' : 'action.hover',
                color: message.trim() && !disabled ? 'primary.contrastText' : 'text.secondary',
                background: message.trim() && !disabled 
                  ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                  : 'transparent',
                boxShadow: message.trim() && !disabled 
                  ? '0 4px 12px rgba(103, 126, 234, 0.3)'
                  : 'none',
                transition: 'all 0.2s ease-in-out',
                animation: showRipple ? 'sendPulse 0.3s ease-out' : 'none',
                '@keyframes sendPulse': {
                  '0%': { transform: 'scale(1)' },
                  '50%': { transform: 'scale(1.2)' },
                  '100%': { transform: 'scale(1)' },
                },
                '&:hover': {
                  bgcolor: message.trim() && !disabled ? 'primary.dark' : 'action.hover',
                  transform: message.trim() && !disabled ? 'scale(1.05) translateY(-2px)' : 'none',
                  boxShadow: message.trim() && !disabled 
                    ? '0 6px 16px rgba(103, 126, 234, 0.4)'
                    : 'none',
                },
                '&:disabled': {
                  bgcolor: 'action.disabledBackground',
                  color: 'action.disabled',
                },
              }}
            >
              <SendIcon fontSize="small" />
            </AccessibleIconButton>
          </HoverAnimatedBox>
        </AnimatedBox>
      </Tooltip>
        </Paper>
      </HoverAnimatedBox>
    </AnimatedBox>
  );
};

export default ChatInput;