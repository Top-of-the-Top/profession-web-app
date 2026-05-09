import { useCallback, useEffect, useRef } from 'react';
import type { HomeworkAttemptAttachment } from '@shared/api/courseApi';

const DRAFT_PREFIX = 'hw_draft:';
const TEXT_DEBOUNCE_MS = 800;

export interface DraftAttachmentMeta {
  attachment_id: string;
  file_name: string;
  file_size: number;
  file_extension: string;
}

export interface HomeworkDraftData {
  savedAt: string;
  answers: Record<string, string>;
  attachments: Record<string, DraftAttachmentMeta[]>;
}

function storageKey(homeworkSlug: string): string {
  return `${DRAFT_PREFIX}${homeworkSlug}`;
}

export function readDraft(homeworkSlug: string): HomeworkDraftData | null {
  try {
    const raw = localStorage.getItem(storageKey(homeworkSlug));
    if (!raw) return null;
    return JSON.parse(raw) as HomeworkDraftData;
  } catch {
    return null;
  }
}

export function clearDraft(homeworkSlug: string): void {
  try {
    localStorage.removeItem(storageKey(homeworkSlug));
  } catch {
  }
}

export function toAttachmentMeta(
  attachments: Record<string, HomeworkAttemptAttachment[]>,
): Record<string, DraftAttachmentMeta[]> {
  const result: Record<string, DraftAttachmentMeta[]> = {};
  for (const [id, list] of Object.entries(attachments)) {
    result[id] = list.map(({ attachment_id, file_name, file_size, file_extension }) => ({
      attachment_id,
      file_name,
      file_size,
      file_extension,
    }));
  }
  return result;
}

export function fromAttachmentMeta(
  meta: Record<string, DraftAttachmentMeta[]> | null | undefined,
): Record<string, HomeworkAttemptAttachment[]> {
  if (!meta) return {};
  const result: Record<string, HomeworkAttemptAttachment[]> = {};
  for (const [id, list] of Object.entries(meta)) {
    result[id] = list.map((m) => ({ ...m, file_url: '' }));
  }
  return result;
}

export function useHomeworkDraft(homeworkSlug: string | undefined) {
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const persist = useCallback(
    (
      answers: Record<string, string>,
      attachments: Record<string, HomeworkAttemptAttachment[]>,
    ) => {
      if (!homeworkSlug) return;
      try {
        localStorage.setItem(
          storageKey(homeworkSlug),
          JSON.stringify({
            savedAt: new Date().toISOString(),
            answers,
            attachments: toAttachmentMeta(attachments),
          } satisfies HomeworkDraftData),
        );
      } catch {
      }
    },
    [homeworkSlug],
  );

  const persistDebounced = useCallback(
    (
      answers: Record<string, string>,
      attachments: Record<string, HomeworkAttemptAttachment[]>,
    ) => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
      debounceTimer.current = setTimeout(() => {
        persist(answers, attachments);
        debounceTimer.current = null;
      }, TEXT_DEBOUNCE_MS);
    },
    [persist],
  );

  useEffect(() => {
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current);
    };
  }, []);

  return { persist, persistDebounced };
}
