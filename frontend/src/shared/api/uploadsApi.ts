import { apiClient } from './interceptor';

export type MediaIntent =
  | 'homework_attachment'
  | 'homework_material'
  | 'user_avatar'
  | 'course_cover'
  | 'lesson_image'
  | 'lesson_file'
  | 'lesson_video'
  | 'webinar_whiteboard';

export type StorageBackend = 's3' | 'kinescope' | 'external';

export interface InitiateUploadPayload {
  intent: MediaIntent;
  filename: string;
  mime_type: string;
  size: number;
}

export interface PresignedUpload {
  method: 'POST' | 'PUT';
  url: string;
  storage_key: string;
  expires_at: string;
  fields: Record<string, string>;
  headers: Record<string, string>;
}

export interface InitiateUploadResponse {
  asset_id: string;
  dedup: boolean;
  storage_backend: StorageBackend;
  upload: PresignedUpload | null;
}

export type AssetStatus = 'pending' | 'ready' | 'deleted';

export interface UploadStatusResponse {
  asset_id: string;
  status: AssetStatus;
  storage_backend: StorageBackend;
  storage_key: string;
  visibility: string;
  mime_type: string;
  size_bytes: number;
  original_filename: string;
  created_at: string;
  committed_at: string | null;
}

export const uploadsApi = {
  initiate(payload: InitiateUploadPayload): Promise<InitiateUploadResponse> {
    return apiClient.request<InitiateUploadResponse>('/api/uploads/initiate/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  status(assetId: string): Promise<UploadStatusResponse> {
    return apiClient.request<UploadStatusResponse>(
      `/api/uploads/${assetId}/status/`,
      { method: 'GET' },
    );
  },
};
