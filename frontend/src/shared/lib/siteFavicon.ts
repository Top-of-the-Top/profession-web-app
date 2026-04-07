export type SiteFaviconVariant = 'default' | 'inverse';

export const SITE_FAVICON_VARIANT: SiteFaviconVariant = 'inverse';

const HREF: Record<SiteFaviconVariant, string> = {
  default: '/profession-minilogo.svg',
  inverse: '/profession-minilogo-white.svg',
};

export function siteFaviconHref(): string {
  return HREF[SITE_FAVICON_VARIANT];
}

export function applySiteFavicon(): void {
  const href = siteFaviconHref();
  let link = document.getElementById('site-favicon') as HTMLLinkElement | null;
  if (!link) {
    link = document.createElement('link');
    link.id = 'site-favicon';
    link.rel = 'icon';
    link.type = 'image/svg+xml';
    document.head.appendChild(link);
  }
  link.href = href;
}
