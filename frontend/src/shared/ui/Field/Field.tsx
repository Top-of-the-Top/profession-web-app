import styles from './styles.module.css';
import { Label } from '../Label';
import { Separator } from '../Separator';
import { useMemo, type ComponentProps } from 'react';

export function FieldSet({ className, ...props }: ComponentProps<'fieldset'>) {
  return (
    <fieldset
      data-slot="field-set"
      className={`${styles['field-set']} ${className ?? ''}`.trim()}
      {...props}
    />
  );
}

export function FieldLegend({
  className,
  variant = 'legend',
  ...props
}: ComponentProps<'legend'> & { variant?: 'legend' | 'label' }) {
  return (
    <legend
      data-slot="field-legend"
      data-variant={variant}
      className={`${styles['field-legend']} ${className ?? ''}`.trim()}
      {...props}
    />
  );
}

export function FieldGroup({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      data-slot="field-group"
      className={`${styles['field-group']} ${className ?? ''}`.trim()}
      {...props}
    />
  );
}

export function Field({
  className,
  orientation = 'vertical',
  ...props
}: ComponentProps<'div'> & {
  orientation?: 'horizontal' | 'vertical' | 'responsive';
}) {
  return (
    <div
      role="group"
      data-slot="field"
      data-orientation={orientation}
      className={`${styles.field} ${className ?? ''}`.trim()}
      {...props}
    />
  );
}

export function FieldContent({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      data-slot="field-content"
      className={`${styles['field-content']} ${className ?? ''}`.trim()}
      {...props}
    />
  );
}

export function FieldLabel({
  className,
  ...props
}: React.ComponentProps<typeof Label>) {
  return (
    <Label
      data-slot="field-label"
      className={`${styles['field-label']} ${className ?? ''}`.trim()}
      {...props}
    />
  );
}

export function FieldTitle({ className, ...props }: ComponentProps<'div'>) {
  return (
    <div
      data-slot="field-title"
      className={`${styles['field-title']} ${className ?? ''}`.trim()}
      {...props}
    />
  );
}

export function FieldDescription({ className, ...props }: ComponentProps<'p'>) {
  return (
    <p
      data-slot="field-description"
      className={`${styles['field-description']} ${className ?? ''}`.trim()}
      {...props}
    />
  );
}

export function FieldSeparator({
  children,
  className,
  ...props
}: ComponentProps<'div'> & {
  children?: React.ReactNode;
}) {
  return (
    <div
      data-slot="field-separator"
      data-content={!!children}
      className={`${styles['field-separator']} ${className ?? ''}`.trim()}
      {...props}
    >
      <Separator />
      {children && (
        <span
          className={styles['field-separator-content']}
          data-slot="field-separator-content"
        >
          {children}
        </span>
      )}
    </div>
  );
}

export function FieldError({
  className,
  children,
  errors,
  ...props
}: ComponentProps<'div'> & {
  errors?: Array<{ message?: string } | undefined>;
}) {
  const content = useMemo(() => {
    if (children) {
      return children;
    }

    if (!errors?.length) {
      return null;
    }

    const uniqueErrors = [
      ...new Map(errors.map((error) => [error?.message, error])).values(),
    ];

    if (uniqueErrors?.length == 1) {
      return uniqueErrors[0]?.message;
    }

    return (
      <ul className={styles['field-error-content']}>
        {uniqueErrors.map(
          (error, index) =>
            error?.message && <li key={index}>{error.message}</li>
        )}
      </ul>
    );
  }, [children, errors]);

  if (!content) {
    return null;
  }

  return (
    <div
      role="alert"
      data-slot="field-error"
      className={`${styles['field-error']} ${className ?? ''}`.trim()}
      {...props}
    >
      {content}
    </div>
  );
}
