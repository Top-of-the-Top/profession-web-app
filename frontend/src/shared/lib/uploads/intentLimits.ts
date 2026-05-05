import type { MediaIntent } from '@shared/api/uploadsApi';

const MB = 1024 * 1024;

export interface IntentLimits {
  maxSize: number;
  mimeAllowlist: readonly string[];
}

export const INTENT_LIMITS: Record<MediaIntent, IntentLimits> = {
  homework_attachment: {
    maxSize: 10 * MB,
    mimeAllowlist: [
      'application/pdf',
      'application/zip',
      'image/png',
      'image/jpeg',
      'text/plain',
    ],
  },
  homework_material: {
    maxSize: 10 * MB,
    mimeAllowlist: [
      'application/pdf',
      'application/zip',
      'image/png',
      'image/jpeg',
      'text/plain',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'audio/mpeg',
      'video/mp4',
    ],
  },
  lesson_image: {
    maxSize: 10 * MB,
    mimeAllowlist: [
      'image/png',
      'image/jpeg',
      'image/webp',
      'image/gif',
      'image/svg+xml',
    ],
  },
  lesson_file: {
    maxSize: 100 * MB,
    mimeAllowlist: [
      'application/pdf',
      'application/zip',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'text/plain',
    ],
  },
  course_cover: {
    maxSize: 10 * MB,
    mimeAllowlist: ['image/png', 'image/jpeg', 'image/webp'],
  },
  user_avatar: {
    maxSize: 10 * MB,
    mimeAllowlist: ['image/png', 'image/jpeg'],
  },
  webinar_whiteboard: {
    maxSize: 50 * MB,
    mimeAllowlist: ['application/pdf'],
  },
  lesson_video: {
    maxSize: 20 * 1024 * MB,
    mimeAllowlist: ['video/mp4', 'video/webm', 'video/quicktime'],
  },
};

export type IntentValidationCode =
  | 'MIME_NOT_ALLOWED'
  | 'SIZE_TOO_LARGE'
  | 'EMPTY_FILE';

export class IntentValidationError extends Error {
  readonly code: IntentValidationCode;

  constructor(message: string, code: IntentValidationCode) {
    super(message);
    this.name = 'IntentValidationError';
    this.code = code;
  }
}

export function validateForIntent(intent: MediaIntent, file: File): void {
  if (file.size <= 0) {
    throw new IntentValidationError('Файл пустой.', 'EMPTY_FILE');
  }
  const limits = INTENT_LIMITS[intent];
  const mime = file.type || 'application/octet-stream';
  if (!limits.mimeAllowlist.includes(mime)) {
    throw new IntentValidationError(
      `Тип файла не поддерживается для этого сценария (${mime}).`,
      'MIME_NOT_ALLOWED',
    );
  }
  if (file.size > limits.maxSize) {
    const limitMb = Math.round(limits.maxSize / MB);
    throw new IntentValidationError(
      `Размер файла превышает ${limitMb} МБ.`,
      'SIZE_TOO_LARGE',
    );
  }
}
