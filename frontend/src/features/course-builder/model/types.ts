import { z } from 'zod';

export const blockTypes = ['text', 'video', 'homework', 'quiz'] as const;

export type BlockType = (typeof blockTypes)[number];

export const BaseBlockSchema = z.object({
  id: z.string().min(1),
  type: z.enum(blockTypes),
  title: z.string().min(1).optional(),
});

export type BaseBlock = z.infer<typeof BaseBlockSchema>;

export const TextBlockSchema = BaseBlockSchema.extend({
  type: z.literal('text'),
  content: z.string().default(''),
});

export type TextBlock = z.infer<typeof TextBlockSchema>;

export const VideoBlockSchema = BaseBlockSchema.extend({
  type: z.literal('video'),
  url: z.string().url().or(z.string().min(1)).default(''),
  description: z.string().optional(),
});

export type VideoBlock = z.infer<typeof VideoBlockSchema>;

export const HomeworkBlockSchema = BaseBlockSchema.extend({
  type: z.literal('homework'),
  instructions: z.string().default(''),
  maxScore: z.number().int().positive().optional(),
});

export type HomeworkBlock = z.infer<typeof HomeworkBlockSchema>;

export const QuizBlockSchema = BaseBlockSchema.extend({
  type: z.literal('quiz'),
  question: z.string().default(''),
  options: z.array(z.string()).default([]),
  correctOptionIndex: z.number().int().nonnegative().optional(),
});

export type QuizBlock = z.infer<typeof QuizBlockSchema>;

export const BlockSchema = z.discriminatedUnion('type', [
  TextBlockSchema,
  VideoBlockSchema,
  HomeworkBlockSchema,
  QuizBlockSchema,
]);

export type Block = z.infer<typeof BlockSchema>;

export const LessonSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  blocks: z.array(BlockSchema),
});

export type Lesson = z.infer<typeof LessonSchema>;

export const ModuleSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  lessons: z.array(LessonSchema),
});

export type Module = z.infer<typeof ModuleSchema>;

export const CourseStructureSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  modules: z.array(ModuleSchema),
});

export type CourseStructure = z.infer<typeof CourseStructureSchema>;

export type CourseStructureDTO = z.infer<typeof CourseStructureSchema>;

export const parseCourseStructure = (data: unknown): CourseStructure => {
  return CourseStructureSchema.parse(data);
};

export const serializeCourseStructure = (structure: CourseStructure): CourseStructureDTO => {
  return CourseStructureSchema.parse(structure);
};

