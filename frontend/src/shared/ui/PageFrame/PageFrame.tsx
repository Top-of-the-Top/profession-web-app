import type { ComponentPropsWithoutRef } from 'react';
import { cn } from '@shared/lib/utils';
import styles from './PageFrame.module.css';

export function PageFrame({
  className,
  children,
  ...rest
}: ComponentPropsWithoutRef<'div'>) {
  return (
    <div className={cn(styles.root, className)} {...rest}>
      {children}
    </div>
  );
}
