import {
  uploadsApi,
  type MediaIntent,
  type PresignedUpload,
  type UploadStatusResponse,
} from '@shared/api/uploadsApi';
import { parseApiError } from '@shared/lib/api/parseApiError';
import { resolveApiFailureMessage } from '@shared/lib/api/backendApiMessages';
import { validateForIntent } from './intentLimits';

export interface UploadMediaAssetOptions {
  pollIntervalMs?: number;
  pollMaxIntervalMs?: number;
  timeoutMs?: number;
  onProgress?: (event: UploadProgressEvent) => void;
}

export type UploadPhase =
  | 'initiating'
  | 'uploading'
  | 'polling'
  | 'ready';

export interface UploadProgressEvent {
  phase: UploadPhase;
  assetId?: string;
  uploadedBytes?: number;
  totalBytes?: number;
  progressPercent?: number;
}

export class MediaUploadError extends Error {
  readonly phase: UploadPhase;
  readonly cause?: unknown;

  constructor(message: string, phase: UploadPhase, cause?: unknown) {
    super(message);
    this.name = 'MediaUploadError';
    this.phase = phase;
    this.cause = cause;
  }
}

const DEFAULT_TIMEOUT_MS = 5 * 60 * 1000;
const DEFAULT_POLL_INTERVAL_MS = 600;
const DEFAULT_POLL_MAX_INTERVAL_MS = 4000;

function toMediaUploadError(err: unknown, phase: UploadPhase): MediaUploadError {
  const parsed = parseApiError(err);
  if (parsed) {
    const message = resolveApiFailureMessage('mediaUpload', parsed.status, parsed.body);
    return new MediaUploadError(message.description, phase, err);
  }
  if (err instanceof MediaUploadError) return err;
  if (err instanceof Error) return new MediaUploadError(err.message, phase, err);
  return new MediaUploadError('Ошибка загрузки файла.', phase, err);
}

async function uploadToS3(file: File, upload: PresignedUpload): Promise<void> {
  const method = upload.method || 'POST';
  const headers = upload.headers ?? {};
  let response: Response;

  if (method === 'POST') {
    const form = new FormData();
    for (const [key, value] of Object.entries(upload.fields ?? {})) {
      form.append(key, value);
    }
    form.append('file', file);
    response = await fetch(upload.url, {
      method,
      headers,
      body: form,
    });
  } else {
    response = await fetch(upload.url, {
      method,
      headers: {
        ...headers,
        'Content-Type': file.type || 'application/octet-stream',
      },
      body: file,
    });
  }

  if (!response.ok) {
    throw new MediaUploadError(
      `S3 ответил кодом ${response.status}. Попробуйте ещё раз.`,
      'uploading',
    );
  }
}

async function uploadToKinescope(
  file: File,
  upload: PresignedUpload,
  onProgress?: (event: UploadProgressEvent) => void,
  assetId?: string,
): Promise<void> {
  const tusModule = await import('tus-js-client');
  const tus = tusModule.default ?? tusModule;

  await new Promise<void>((resolve, reject) => {
    const uploader = new tus.Upload(file, {
      endpoint: upload.url,
      headers: upload.headers ?? {},
      metadata: {
        filename: file.name,
        filetype: file.type || 'application/octet-stream',
      },
      uploadSize: file.size,
      onError: (error: Error) => {
        reject(new MediaUploadError(error.message, 'uploading', error));
      },
      onProgress: (uploadedBytes: number, totalBytes: number) => {
        const percent =
          totalBytes > 0
            ? Math.max(0, Math.min(100, Math.round((uploadedBytes / totalBytes) * 100)))
            : 0;
        onProgress?.({
          phase: 'uploading',
          assetId,
          uploadedBytes,
          totalBytes,
          progressPercent: percent,
        });
      },
      onSuccess: () => {
        resolve();
      },
    });
    uploader.start();
  });
}

async function pollUntilReady(
  assetId: string,
  options: Required<
    Pick<UploadMediaAssetOptions, 'pollIntervalMs' | 'pollMaxIntervalMs' | 'timeoutMs'>
  >,
): Promise<UploadStatusResponse> {
  const deadline = Date.now() + options.timeoutMs;
  let interval = options.pollIntervalMs;

  while (Date.now() < deadline) {
    let status: UploadStatusResponse;
    try {
      status = await uploadsApi.status(assetId);
    } catch (err) {
      throw toMediaUploadError(err, 'polling');
    }
    if (status.status === 'ready') return status;
    if (status.status === 'deleted') {
      throw new MediaUploadError('Файл удалён до завершения обработки.', 'polling');
    }
    await new Promise((resolve) => setTimeout(resolve, interval));
    interval = Math.min(options.pollMaxIntervalMs, Math.round(interval * 1.5));
  }

  throw new MediaUploadError(
    'Превышено время ожидания обработки файла. Попробуйте позже.',
    'polling',
  );
}

export async function uploadMediaAsset(
  intent: MediaIntent,
  file: File,
  options: UploadMediaAssetOptions = {},
): Promise<{ assetId: string; status: UploadStatusResponse }> {
  validateForIntent(intent, file);

  const onProgress = options.onProgress;
  onProgress?.({ phase: 'initiating' });

  let initiated: Awaited<ReturnType<typeof uploadsApi.initiate>>;
  try {
    initiated = await uploadsApi.initiate({
      intent,
      filename: file.name,
      mime_type: file.type || 'application/octet-stream',
      size: file.size,
    });
  } catch (err) {
    throw toMediaUploadError(err, 'initiating');
  }

  if (!initiated.upload) {
    throw new MediaUploadError(
      'Сервер не вернул инструкции для загрузки.',
      'initiating',
    );
  }

  onProgress?.({ phase: 'uploading', assetId: initiated.asset_id });

  if (initiated.storage_backend === 's3') {
    await uploadToS3(file, initiated.upload);
  } else if (initiated.storage_backend === 'kinescope') {
    await uploadToKinescope(file, initiated.upload, onProgress, initiated.asset_id);
  } else {
    throw new MediaUploadError(
      `Хранилище ${initiated.storage_backend} пока не поддерживается фронтом.`,
      'uploading',
    );
  }

  onProgress?.({ phase: 'polling', assetId: initiated.asset_id });

  const status = await pollUntilReady(initiated.asset_id, {
    pollIntervalMs: options.pollIntervalMs ?? DEFAULT_POLL_INTERVAL_MS,
    pollMaxIntervalMs: options.pollMaxIntervalMs ?? DEFAULT_POLL_MAX_INTERVAL_MS,
    timeoutMs: options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
  });

  onProgress?.({ phase: 'ready', assetId: initiated.asset_id });

  return { assetId: initiated.asset_id, status };
}

export function assetUri(assetId: string): string {
  return `asset://${assetId}`;
}
