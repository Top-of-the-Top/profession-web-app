import { useCallback } from 'react';

const DRAFT_PREFIX = 'hw_review_draft:';

export interface ReviewDraftItem {
  points: number;
  comment: string;
}

export interface ReviewDraftData {
  savedAt: string;
  drafts: Record<string, ReviewDraftItem>;
}

function storageKey(attemptId: string): string {
  return `${DRAFT_PREFIX}${attemptId}`;
}

export function readReviewDraft(attemptId: string): ReviewDraftData | null {
  try {
    const raw = localStorage.getItem(storageKey(attemptId));
    if (!raw) return null;
    return JSON.parse(raw) as ReviewDraftData;
  } catch {
    return null;
  }
}

export function clearReviewDraft(attemptId: string): void {
  try {
    localStorage.removeItem(storageKey(attemptId));
  } catch {
    // ignore
  }
}

export function useReviewDraft(attemptId: string | undefined) {
  const persist = useCallback(
    (drafts: Record<string, ReviewDraftItem>) => {
      if (!attemptId) return;
      try {
        localStorage.setItem(
          storageKey(attemptId),
          JSON.stringify({
            savedAt: new Date().toISOString(),
            drafts,
          } satisfies ReviewDraftData),
        );
      } catch {
        // localStorage full or unavailable
      }
    },
    [attemptId],
  );

  return { persist };
}
