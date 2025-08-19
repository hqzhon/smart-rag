import React, { forwardRef, useRef, useImperativeHandle } from 'react';
import {
  Button,
  ButtonProps,
  IconButton,
  IconButtonProps,
  Tooltip,
  CircularProgress,
  Box,
} from '@mui/material';
import { useAccessibility } from './AccessibilityProvider';

interface BaseAccessibleButtonProps {
  loadingText?: string;
  successMessage?: string;
  errorMessage?: string;
  confirmAction?: boolean;
  confirmMessage?: string;
  tooltip?: string;
  shortcut?: string;
  announceOnClick?: boolean;
}

interface AccessibleButtonProps extends Omit<ButtonProps, 'loading'>, BaseAccessibleButtonProps {
  variant?: 'text' | 'outlined' | 'contained';
  loading?: boolean;
}

interface AccessibleIconButtonProps extends Omit<IconButtonProps, 'loading'>, BaseAccessibleButtonProps {
  'aria-label': string;
  loading?: boolean;
}

type ButtonRef = {
  focus: () => void;
  click: () => void;
};

const BaseAccessibleButton = forwardRef<
  ButtonRef,
  (AccessibleButtonProps | AccessibleIconButtonProps) & {
    isIconButton?: boolean;
  }
>((
  {
    loading = false,
    loadingText = '加载中...',
    successMessage,
    errorMessage,
    confirmAction = false,
    confirmMessage = '确定要执行此操作吗？',
    tooltip,
    shortcut,
    announceOnClick = true,
    onClick,
    disabled,
    children,
    isIconButton = false,
    ...props
  },
  ref
) => {
  const { announceMessage } = useAccessibility();
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [isConfirming, setIsConfirming] = React.useState(false);
  const [actionState, setActionState] = React.useState<'idle' | 'success' | 'error'>('idle');

  useImperativeHandle(ref, () => ({
    focus: () => buttonRef.current?.focus(),
    click: () => buttonRef.current?.click(),
  }));

  const handleClick = async (event: React.MouseEvent<HTMLButtonElement>) => {
    if (loading || disabled) return;

    // 确认操作
    if (confirmAction && !isConfirming) {
      setIsConfirming(true);
      announceMessage(confirmMessage);
      return;
    }

    try {
      if (announceOnClick) {
        const buttonText = typeof children === 'string' ? children : props['aria-label'] || '按钮';
        announceMessage(`${buttonText}已点击`);
      }

      await onClick?.(event);

      if (successMessage) {
        setActionState('success');
        announceMessage(successMessage);
        setTimeout(() => setActionState('idle'), 3000);
      }
    } catch (error) {
      if (errorMessage) {
        setActionState('error');
        announceMessage(errorMessage);
        setTimeout(() => setActionState('idle'), 3000);
      }
    } finally {
      setIsConfirming(false);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>) => {
    // 空格键和回车键都可以激活按钮
    if (event.key === ' ' || event.key === 'Enter') {
      event.preventDefault();
      handleClick(event as any);
    }
    // Escape键取消确认
    if (event.key === 'Escape' && isConfirming) {
      setIsConfirming(false);
      announceMessage('操作已取消');
    }
  };

  const isDisabled = disabled || loading;
  const showLoading = loading;

  // 构建aria-label
  const getAriaLabel = () => {
    let label = props['aria-label'] || (typeof children === 'string' ? children : '');
    
    if (shortcut) {
      label += ` (快捷键: ${shortcut})`;
    }
    
    if (loading) {
      label += ` - ${loadingText}`;
    }
    
    if (isConfirming) {
      label += ' - 等待确认';
    }
    
    return label;
  };

  // 构建按钮内容
  const buttonContent = (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      {showLoading && (
        <CircularProgress
          size={isIconButton ? 20 : 16}
          color="inherit"
          aria-hidden="true"
        />
      )}
      {children}
      {isConfirming && !showLoading && (
        <Box
          component="span"
          sx={{
            ml: 1,
            fontSize: '0.875em',
            opacity: 0.7,
          }}
        >
          (再次点击确认)
        </Box>
      )}
    </Box>
  );

  const buttonProps = {
    ...props,
    ref: buttonRef,
    disabled: isDisabled,
    onClick: handleClick,
    onKeyDown: handleKeyDown,
    'aria-label': getAriaLabel(),
    'aria-busy': loading,
    'aria-pressed': isConfirming ? true : undefined,
    'data-state': actionState,
    sx: {
      ...props.sx,
      position: 'relative',
      '&:focus-visible': {
        outline: '2px solid',
        outlineColor: 'primary.main',
        outlineOffset: 2,
      },
      ...(actionState === 'success' && {
        borderColor: 'success.main',
        color: 'success.main',
      }),
      ...(actionState === 'error' && {
        borderColor: 'error.main',
        color: 'error.main',
      }),
      ...(isConfirming && {
        animation: 'pulse 1s infinite',
        '@keyframes pulse': {
          '0%': { opacity: 1 },
          '50%': { opacity: 0.7 },
          '100%': { opacity: 1 },
        },
      }),
    },
  };

  const ButtonComponent = isIconButton ? (
    <IconButton {...(buttonProps as IconButtonProps)}>
      {buttonContent}
    </IconButton>
  ) : (
    <Button {...(buttonProps as ButtonProps)}>
      {buttonContent}
    </Button>
  );

  if (tooltip) {
    return (
      <Tooltip
        title={tooltip}
        arrow
        enterDelay={500}
        leaveDelay={200}
      >
        <span>
          {ButtonComponent}
        </span>
      </Tooltip>
    );
  }

  return ButtonComponent;
});

BaseAccessibleButton.displayName = 'BaseAccessibleButton';

export const AccessibleButton = forwardRef<ButtonRef, AccessibleButtonProps>(
  (props, ref) => (
    <BaseAccessibleButton {...props} ref={ref} isIconButton={false} />
  )
);

AccessibleButton.displayName = 'AccessibleButton';

export const AccessibleIconButton = forwardRef<ButtonRef, AccessibleIconButtonProps>(
  (props, ref) => (
    <BaseAccessibleButton {...props} ref={ref} isIconButton={true} />
  )
);

AccessibleIconButton.displayName = 'AccessibleIconButton';

export default AccessibleButton;