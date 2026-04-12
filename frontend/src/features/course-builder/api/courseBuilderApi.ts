import { apiClient } from '@shared/api/interceptor';
import type { LessonLayoutDTO } from '../model/types';

export interface SaveLessonLayoutParams {
  courseId: number;
  layout: LessonLayoutDTO;
}

export const STRUCTURE_MEDIA_PLACEHOLDER_PREFIX = 'local://' as const;

const ASSET_PART_PREFIX = 'asset_' as const;

export type StructureAssetKind = 'image' | 'video';

export interface StructureSaveAssetMeta {
  id: string;
  field: string;
  kind: StructureAssetKind;
}

export interface StructureSaveEnvelope {
  assets?: StructureSaveAssetMeta[];
  document: unknown;
}

const ASSET_ID_RE = /^[a-zA-Z0-9_-]+$/;

export function structureAssetPartName(assetId: string): string {
  if (!ASSET_ID_RE.test(assetId)) {
    throw new Error(`structureAssetPartName: invalid asset id "${assetId}"`);
  }
  return `${ASSET_PART_PREFIX}${assetId}`;
}

export function makeStructureMediaPlaceholder(assetId: string): string {
  if (!ASSET_ID_RE.test(assetId)) {
    throw new Error(`makeStructureMediaPlaceholder: invalid asset id "${assetId}"`);
  }
  return `${STRUCTURE_MEDIA_PLACEHOLDER_PREFIX}${assetId}`;
}

function guessAssetKind(file: File): StructureAssetKind {
  if (file.type.startsWith('video/')) return 'video';
  return 'image';
}

export function buildStructureSaveFormData(
  document: unknown,
  filesByAssetId: Record<string, File>,
): FormData {
  const assetIds = Object.keys(filesByAssetId);
  const assets: StructureSaveAssetMeta[] = assetIds.map((id) => ({
    id,
    field: structureAssetPartName(id),
    kind: guessAssetKind(filesByAssetId[id]),
  }));

  const envelope: StructureSaveEnvelope = {
    document,
    ...(assets.length > 0 ? { assets } : {}),
  };

  const formData = new FormData();
  formData.set('envelope', JSON.stringify(envelope));
  for (const id of assetIds) {
    const file = filesByAssetId[id];
    formData.set(structureAssetPartName(id), file, file.name || id);
  }

  return formData;
}

export interface SaveCourseStructureWithMediaParams {
  courseId: number;
  document: unknown;
  filesByAssetId: Record<string, File>;
}

export const courseBuilderApi = {
  async load(courseId: number): Promise<LessonLayoutDTO> {
    return apiClient.request<LessonLayoutDTO>(
      `/api/app/courses/${courseId}/structure/`,
      { method: 'GET' },
    );
  },

  async save({ courseId, layout }: SaveLessonLayoutParams): Promise<void> {
    await apiClient.request(`/api/app/courses/${courseId}/structure/`, {
      method: 'PUT',
      body: JSON.stringify(layout),
    });
  },

  async saveWithMedia({
    courseId,
    document,
    filesByAssetId,
  }: SaveCourseStructureWithMediaParams): Promise<void> {
    const body = buildStructureSaveFormData(document, filesByAssetId);
    await apiClient.request(`/api/app/courses/${courseId}/structure/`, {
      method: 'PUT',
      body,
    });
  },
};
