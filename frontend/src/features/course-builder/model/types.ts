import { z } from 'zod';

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

export const parseLessonLayout = (data: unknown): LessonLayout => {
  return LessonLayoutSchema.parse(data);
};

export const serializeLessonLayout = (layout: LessonLayout): LessonLayoutDTO => {
  return LessonLayoutSchema.parse(layout);
};

