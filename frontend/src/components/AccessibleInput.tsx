import React, { forwardRef, useId } from 'react';
import {
  TextField,
  TextFieldProps,
  FormControl,
  FormHelperText,
  Box,
  Chip,
} from '@mui/material';
import { useAccessibility } from './AccessibilityProvider';

interface AccessibleInputProps extends Omit<TextFieldProps, 'id'> {
  label: string;
  description?: string;
  errorMessage?: string;
  successMessage?: string;
  required?: boolean;
  showCharacterCount?: boolean;
  maxLength?: number;
  suggestions?: string[];
  onSuggestionSelect?: (suggestion: string) => void;
}

export const AccessibleInput = forwardRef<HTMLInputElement, AccessibleInputProps>(
  (
    {
      label,
      description,
      errorMessage,
      successMessage,
      required = false,
      showCharacterCount = false,
      maxLength,
      suggestions = [],
      onSuggestionSelect,
      value = '',
      onChange,
      onFocus,
      onBlur,
      ...props
    },
    ref
  ) => {
    const { announceMessage } = useAccessibility();
    const inputId = useId();
    const descriptionId = useId();
    const errorId = useId();
    const successId = useId();
    const characterCountId = useId();
    const suggestionsId = useId();

    const [focused, setFocused] = React.useState(false);
    const [selectedSuggestionIndex, setSelectedSuggestionIndex] = React.useState(-1);

    const characterCount = typeof value === 'string' ? value.length : 0;
    const isError = Boolean(errorMessage);
    const isSuccess = Boolean(successMessage && !isError);

    const handleFocus = (event: React.FocusEvent<HTMLInputElement>) => {
      setFocused(true);
      if (description) {
        announceMessage(`${label}输入框已聚焦。${description}`);
      }
      onFocus?.(event);
    };

    const handleBlur = (event: React.FocusEvent<HTMLInputElement>) => {
      setFocused(false);
      setSelectedSuggestionIndex(-1);
      onBlur?.(event);
    };

    const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
      if (suggestions.length > 0 && focused) {
        switch (event.key) {
          case 'ArrowDown':
            event.preventDefault();
            setSelectedSuggestionIndex(prev => 
              prev < suggestions.length - 1 ? prev + 1 : 0
            );
            break;
          case 'ArrowUp':
            event.preventDefault();
            setSelectedSuggestionIndex(prev => 
              prev > 0 ? prev - 1 : suggestions.length - 1
            );
            break;
          case 'Enter':
            if (selectedSuggestionIndex >= 0) {
              event.preventDefault();
              onSuggestionSelect?.(suggestions[selectedSuggestionIndex]);
              setSelectedSuggestionIndex(-1);
            }
            break;
          case 'Escape':
            setSelectedSuggestionIndex(-1);
            break;
        }
      }
    };

    const handleSuggestionClick = (suggestion: string) => {
      onSuggestionSelect?.(suggestion);
      setSelectedSuggestionIndex(-1);
    };

    // 构建aria-describedby
    const describedBy = [
      description && descriptionId,
      errorMessage && errorId,
      successMessage && successId,
      showCharacterCount && characterCountId,
    ].filter(Boolean).join(' ');

    return (
      <FormControl fullWidth error={isError}>
        <Box position="relative">
          <TextField
            {...props}
            ref={ref}
            id={inputId}
            label={label}
            value={value}
            onChange={onChange}
            onFocus={handleFocus}
            onBlur={handleBlur}
            onKeyDown={handleKeyDown}
            error={isError}
            required={required}
            inputProps={{
              ...props.inputProps,
              'aria-describedby': describedBy || undefined,
              'aria-invalid': isError,
              'aria-required': required,
              maxLength,
              role: 'textbox',
              'aria-expanded': suggestions.length > 0 && focused,
              'aria-haspopup': suggestions.length > 0 ? 'listbox' : undefined,
              'aria-owns': suggestions.length > 0 ? suggestionsId : undefined,
            }}
            sx={{
              '& .MuiOutlinedInput-root': {
                '&.Mui-focused': {
                  '& .MuiOutlinedInput-notchedOutline': {
                    borderColor: isError ? 'error.main' : isSuccess ? 'success.main' : 'primary.main',
                    borderWidth: 2,
                  },
                },
              },
            }}
          />

          {/* 建议列表 */}
          {suggestions.length > 0 && focused && (
            <Box
              id={suggestionsId}
              role="listbox"
              aria-label={`${label}的建议选项`}
              sx={{
                position: 'absolute',
                top: '100%',
                left: 0,
                right: 0,
                zIndex: 1300,
                bgcolor: 'background.paper',
                border: 1,
                borderColor: 'divider',
                borderRadius: 1,
                boxShadow: 3,
                maxHeight: 200,
                overflow: 'auto',
                mt: 0.5,
              }}
            >
              {suggestions.map((suggestion, index) => (
                <Box
                  key={suggestion}
                  role="option"
                  aria-selected={index === selectedSuggestionIndex}
                  onClick={() => handleSuggestionClick(suggestion)}
                  sx={{
                    p: 1.5,
                    cursor: 'pointer',
                    bgcolor: index === selectedSuggestionIndex ? 'action.selected' : 'transparent',
                    '&:hover': {
                      bgcolor: 'action.hover',
                    },
                    borderBottom: index < suggestions.length - 1 ? 1 : 0,
                    borderColor: 'divider',
                  }}
                >
                  <Chip
                    label={suggestion}
                    size="small"
                    variant={index === selectedSuggestionIndex ? 'filled' : 'outlined'}
                    sx={{ fontSize: '0.875rem' }}
                  />
                </Box>
              ))}
            </Box>
          )}
        </Box>

        {/* 描述文本 */}
        {description && (
          <FormHelperText id={descriptionId} sx={{ mt: 1 }}>
            {description}
          </FormHelperText>
        )}

        {/* 错误消息 */}
        {errorMessage && (
          <FormHelperText id={errorId} error sx={{ mt: 1 }}>
            {errorMessage}
          </FormHelperText>
        )}

        {/* 成功消息 */}
        {successMessage && !isError && (
          <FormHelperText id={successId} sx={{ mt: 1, color: 'success.main' }}>
            {successMessage}
          </FormHelperText>
        )}

        {/* 字符计数 */}
        {showCharacterCount && (
          <FormHelperText
            id={characterCountId}
            sx={{
              mt: 1,
              textAlign: 'right',
              color: maxLength && characterCount > maxLength * 0.9 ? 'warning.main' : 'text.secondary',
            }}
          >
            {characterCount}{maxLength && `/${maxLength}`}
          </FormHelperText>
        )}
      </FormControl>
    );
  }
);

AccessibleInput.displayName = 'AccessibleInput';

export default AccessibleInput;