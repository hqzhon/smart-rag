import React, { useState, useRef, useEffect, memo } from 'react';
import { Box, Skeleton, IconButton } from '@mui/material';
import { ImageNotSupported as ImageNotSupportedIcon } from '@mui/icons-material';
import { AnimatedBox } from './animations';

interface LazyImageProps {
  src: string;
  alt: string;
  width?: number | string;
  height?: number | string;
  placeholder?: React.ReactNode;
  fallback?: React.ReactNode;
  threshold?: number;
  className?: string;
  onLoad?: () => void;
  onError?: () => void;
}

const LazyImage: React.FC<LazyImageProps> = memo((
  {
    src,
    alt,
    width = '100%',
    height = 'auto',
    placeholder,
    fallback,
    threshold = 0.1,
    className,
    onLoad,
    onError,
  }
) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isError, setIsError] = useState(false);
  const [isInView, setIsInView] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Intersection Observer for lazy loading
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.disconnect();
        }
      },
      {
        threshold,
        rootMargin: '50px',
      }
    );

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => observer.disconnect();
  }, [threshold]);

  // Handle image loading
  useEffect(() => {
    if (!isInView || !src) return;

    const img = new Image();
    img.onload = () => {
      setIsLoaded(true);
      onLoad?.();
    };
    img.onerror = () => {
      setIsError(true);
      onError?.();
    };
    img.src = src;
  }, [isInView, src, onLoad, onError]);

  const defaultPlaceholder = (
    <Skeleton
      variant="rectangular"
      width={width}
      height={height}
      animation="wave"
      sx={{
        borderRadius: 1,
        bgcolor: 'action.hover',
      }}
    />
  );

  const defaultFallback = (
    <Box
      sx={{
        width,
        height,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: 'action.hover',
        borderRadius: 1,
        border: '1px dashed',
        borderColor: 'divider',
      }}
    >
      <IconButton disabled>
        <ImageNotSupportedIcon sx={{ fontSize: 48, color: 'text.disabled' }} />
      </IconButton>
    </Box>
  );

  return (
    <Box
      ref={containerRef}
      className={className}
      sx={{
        width,
        height,
        position: 'relative',
        overflow: 'hidden',
        borderRadius: 1,
      }}
    >
      {!isInView && (placeholder || defaultPlaceholder)}
      
      {isInView && isError && (fallback || defaultFallback)}
      
      {isInView && !isError && (
        <>
          {!isLoaded && (placeholder || defaultPlaceholder)}
          <AnimatedBox
            animation="fadeInUp"
            duration="0.3s"
            sx={{
              opacity: isLoaded ? 1 : 0,
              transition: 'opacity 0.3s ease-in-out',
            }}
          >
            <img
              ref={imgRef}
              src={src}
              alt={alt}
              style={{
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                display: isLoaded ? 'block' : 'none',
              }}
              onLoad={() => {
                setIsLoaded(true);
                onLoad?.();
              }}
              onError={() => {
                setIsError(true);
                onError?.();
              }}
            />
          </AnimatedBox>
        </>
      )}
    </Box>
  );
});

LazyImage.displayName = 'LazyImage';

export default LazyImage;