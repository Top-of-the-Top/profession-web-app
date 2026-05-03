import {
  useCallback,
  useEffect,
  useRef,
  type ReactNode,
} from 'react';
import { createPortal } from 'react-dom';
import { cn } from '@shared/lib/utils';
import styles from './Modal.module.css';

export type ModalProps = {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  backdropClassName?: string;
  panelClassName?: string;
  closeOnBackdrop?: boolean;
  labelledBy?: string;
  describedBy?: string;
};

export function Modal({
  open,
  onClose,
  children,
  backdropClassName,
  panelClassName,
  closeOnBackdrop = true,
  labelledBy,
  describedBy,
}: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  const requestClose = useCallback(() => {
    onClose();
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prevOverflow;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        requestClose();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [open, requestClose]);

  useEffect(() => {
    if (!open) return;
    const node = panelRef.current;
    if (node) node.focus();
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div
      className={cn(styles.backdrop, backdropClassName)}
      role="presentation"
      onMouseDown={(e) => {
        if (e.target !== e.currentTarget) return;
        if (closeOnBackdrop) requestClose();
      }}
    >
      <div
        ref={panelRef}
        className={cn(styles.panel, panelClassName)}
        role="dialog"
        aria-modal="true"
        aria-labelledby={labelledBy}
        aria-describedby={describedBy}
        tabIndex={-1}
        onMouseDown={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>,
    document.body,
  );
}
