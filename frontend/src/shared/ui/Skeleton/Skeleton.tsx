import type { HTMLAttributes } from 'react';
import { cn } from '../../lib/utils';
import styles from './Skeleton.module.css';

type SkeletonShape = 'rect' | 'text' | 'circle';

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  shape?: SkeletonShape;
  animated?: boolean;
}

export function Skeleton({
  className,
  shape = 'rect',
  animated = true,
  ...props
}: SkeletonProps) {
  return (
    <div
      className={cn(styles.skeleton, styles[shape], animated && styles.animated, className)}
      aria-hidden
      {...props}
    />
  );
}
