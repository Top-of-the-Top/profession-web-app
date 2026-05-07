import { sanitizeEditorHtml } from '@shared/lib/html/sanitizeEditorHtml';

interface SafeHtmlProps {
  html: string;
  className?: string;
  style?: React.CSSProperties;
}

export function SafeHtml({ html, className, style }: SafeHtmlProps) {
  return (
    <div
      className={className}
      style={style}
      dangerouslySetInnerHTML={{ __html: sanitizeEditorHtml(html) }}
    />
  );
}
