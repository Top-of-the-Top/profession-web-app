const ALLOWED_TAGS = new Set([
  'p',
  'br',
  'strong',
  'b',
  'em',
  'i',
  'u',
  's',
  'h1',
  'h2',
  'h3',
  'blockquote',
  'ul',
  'ol',
  'li',
]);

const DROP_WITH_CONTENT_TAGS = new Set([
  'script',
  'style',
  'iframe',
  'object',
  'embed',
  'link',
  'meta',
  'svg',
  'math',
]);

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function normalizeToHtml(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return '<p></p>';
  if (/<[a-z][\s\S]*>/i.test(trimmed)) return trimmed;
  return `<p>${escapeHtml(trimmed).replace(/\r?\n/g, '<br>')}</p>`;
}

export function sanitizeEditorHtml(value: string): string {
  const normalized = normalizeToHtml(value);
  const parser = new DOMParser();
  const doc = parser.parseFromString(`<div>${normalized}</div>`, 'text/html');
  const container = doc.body.firstElementChild as HTMLDivElement | null;
  if (!container) return '<p></p>';

  const elements = Array.from(container.querySelectorAll('*'));
  for (const element of elements) {
    const tagName = element.tagName.toLowerCase();

    if (DROP_WITH_CONTENT_TAGS.has(tagName)) {
      element.remove();
      continue;
    }

    if (!ALLOWED_TAGS.has(tagName)) {
      element.replaceWith(...Array.from(element.childNodes));
      continue;
    }

    for (const attrName of element.getAttributeNames()) {
      element.removeAttribute(attrName);
    }
  }

  const result = container.innerHTML.trim();
  return result ? result : '<p></p>';
}
