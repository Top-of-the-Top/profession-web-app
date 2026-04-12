import type { ReactNode } from 'react';
import { cn } from '@shared/lib/utils';
import styles from './PageTransition.module.css';

interface PageTransitionProps {
  children: ReactNode;
  className?: string;
}

export function PageTransition({ children, className }: PageTransitionProps) {
  return (
    <div className={cn(styles.enter, className)}>
      {children}
    </div>
  );
}
