import { z } from 'zod';
import type { HomeworkLayout } from './homeworkTypes';
import { HomeworkLayoutSchema } from './homeworkTypes';

export const COURSE_PAGE_VERSION = 1 as const;

export const blockTypes = ['text', 'photo', 'video'] as const;

export type BlockType = (typeof blockTypes)[number];

const PositionSchema = z.object({
  x: z.number().int().nonnegative(),
  y: z.number().int().nonnegative(),
  w: z.number().int().positive(),
  h: z.number().int().positive(),
});

export const BaseBlockSchema = z.object({
  id: z.string().min(1),
  type: z.enum(blockTypes),
}).merge(PositionSchema);

export type BaseBlock = z.infer<typeof BaseBlockSchema>;

export const TextBlockSchema = BaseBlockSchema.extend({
  type: z.literal('text'),
  html: z.string().default(''),
  fontSizeIndex: z.number().int().nonnegative().optional(),
});

export type TextBlock = z.infer<typeof TextBlockSchema>;

export const PhotoBlockSchema = BaseBlockSchema.extend({
  type: z.literal('photo'),
  url: z.string().optional().default(''),
});

export type PhotoBlock = z.infer<typeof PhotoBlockSchema>;

export const VideoBlockSchema = BaseBlockSchema.extend({
  type: z.literal('video'),
  url: z.string().optional().default(''),
});

export type VideoBlock = z.infer<typeof VideoBlockSchema>;

export const BlockSchema = z.discriminatedUnion('type', [
  TextBlockSchema,
  PhotoBlockSchema,
  VideoBlockSchema,
]);

export type Block = z.infer<typeof BlockSchema>;

export const LessonLayoutSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  blocks: z.array(BlockSchema),
});

export type LessonLayout = z.infer<typeof LessonLayoutSchema>;

export type LessonLayoutDTO = z.infer<typeof LessonLayoutSchema>;

export const CoursePageSchema = z.object({
  version: z.literal(COURSE_PAGE_VERSION),
  lesson: LessonLayoutSchema,
  homework: HomeworkLayoutSchema.nullable(),
});

export type CoursePage = z.infer<typeof CoursePageSchema>;
export type CoursePageDTO = z.infer<typeof CoursePageSchema>;

export const parseLessonLayout = (data: unknown): LessonLayout => {
  return LessonLayoutSchema.parse(data);
};

export const parseLessonLayoutFromContentString = (raw: string): LessonLayout => {
  const trimmed = raw.trim();
  if (!trimmed) {
    throw new Error('EMPTY_LESSON_CONTENT');
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(trimmed);
  } catch {
    throw new Error('INVALID_LESSON_CONTENT_JSON');
  }
  if (parsed && typeof parsed === 'object' && 'lesson' in parsed) {
    return CoursePageSchema.parse(parsed).lesson;
  }
  return LessonLayoutSchema.parse(parsed);
};

export const serializeLessonLayout = (layout: LessonLayout): LessonLayoutDTO => {
  return LessonLayoutSchema.parse(layout);
};

export const serializeCoursePage = (
  lesson: LessonLayout,
  homework: HomeworkLayout | null,
): CoursePageDTO => {
  return CoursePageSchema.parse({
    version: COURSE_PAGE_VERSION,
    lesson,
    homework,
  });
};

export const parseCoursePage = (data: unknown): CoursePage => {
  return CoursePageSchema.parse(data);
};

