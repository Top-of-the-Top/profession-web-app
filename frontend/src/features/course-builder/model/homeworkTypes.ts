import { z } from 'zod';

export const homeworkQuestionTypes = ['single', 'file', 'text'] as const;

export type HomeworkQuestionType = (typeof homeworkQuestionTypes)[number];

export const HomeworkOptionSchema = z.object({
  id: z.string().min(1),
  text: z.string().default(''),
  isCorrect: z.boolean().default(false),
});

export type HomeworkOption = z.infer<typeof HomeworkOptionSchema>;

export const HomeworkQuestionBaseSchema = z.object({
  id: z.string().min(1),
  title: z.string().default(''),
  score: z.number().int().nonnegative().default(0),
});

export const HomeworkQuestionSingleSchema = HomeworkQuestionBaseSchema.extend({
  type: z.literal('single'),
  options: z.array(HomeworkOptionSchema).default([]),
});

export const HomeworkQuestionFileSchema = HomeworkQuestionBaseSchema.extend({
  type: z.literal('file'),
  description: z.string().default(''),
});

export const HomeworkQuestionTextSchema = HomeworkQuestionBaseSchema.extend({
  type: z.literal('text'),
  description: z.string().default(''),
});

export const HomeworkQuestionSchema = z.discriminatedUnion('type', [
  HomeworkQuestionSingleSchema,
  HomeworkQuestionFileSchema,
  HomeworkQuestionTextSchema,
]);

export type HomeworkQuestion = z.infer<typeof HomeworkQuestionSchema>;

export const HomeworkLayoutSchema = z.object({
  lessonId: z.string().min(1),
  title: z.string().default(''),
  deadline: z.string().default(''),
  questions: z.array(HomeworkQuestionSchema),
});

export type HomeworkLayout = z.infer<typeof HomeworkLayoutSchema>;

export type HomeworkLayoutDTO = z.infer<typeof HomeworkLayoutSchema>;

export const parseHomeworkLayout = (data: unknown): HomeworkLayout => {
  return HomeworkLayoutSchema.parse(data);
};

export const serializeHomeworkLayout = (
  layout: HomeworkLayout,
): HomeworkLayoutDTO => {
  return HomeworkLayoutSchema.parse(layout);
};

