import { z } from 'zod';

export const HOMEWORK_FILE_TASK_TEXT_PREFIX = 'FILE::';

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

export interface HomeworkErrors {
  title: boolean;
  deadline: boolean;
  noQuestions: boolean;
  questions: Record<string, QuestionErrors>;
}

export interface QuestionErrors {
  title: boolean;
  score: boolean;
  noCorrect: boolean;
  tooFewOptions: boolean;
  duplicateOptionIds: Set<string>;
}

export function validateHomeworkLayout(layout: HomeworkLayout): HomeworkErrors {
  const questions: Record<string, QuestionErrors> = {};

  for (const q of layout.questions) {
    const qErr: QuestionErrors = {
      title: !q.title.trim(),
      score: !q.score || q.score <= 0,
      noCorrect: false,
      tooFewOptions: false,
      duplicateOptionIds: new Set(),
    };

    if (q.type === 'single') {
      qErr.tooFewOptions = q.options.length < 2;
      qErr.noCorrect = !q.options.some((o) => o.isCorrect);

      const seen = new Map<string, string>();
      for (const opt of q.options) {
        const key = opt.text.trim().toLowerCase();
        if (!key) continue;
        const firstId = seen.get(key);
        if (firstId === undefined) {
          seen.set(key, opt.id);
        } else {
          qErr.duplicateOptionIds.add(opt.id);
          qErr.duplicateOptionIds.add(firstId);
        }
      }
    }

    questions[q.id] = qErr;
  }

  const deadlineDate = new Date(layout.deadline);

  return {
    title: !layout.title.trim(),
    deadline: !layout.deadline.trim() || Number.isNaN(deadlineDate.getTime()),
    noQuestions: layout.questions.length === 0,
    questions,
  };
}

export function isHomeworkValid(errors: HomeworkErrors): boolean {
  if (errors.title || errors.deadline || errors.noQuestions) return false;
  return Object.values(errors.questions).every(
    (q) =>
      !q.title &&
      !q.score &&
      !q.noCorrect &&
      !q.tooFewOptions &&
      q.duplicateOptionIds.size === 0,
  );
}

