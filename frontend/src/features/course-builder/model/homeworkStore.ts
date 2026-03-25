import { create } from 'zustand';
import { nanoid } from 'nanoid';
import type {
  HomeworkLayout,
  HomeworkQuestion,
  HomeworkQuestionType,
  HomeworkOption,
} from './homeworkTypes';
import { serializeHomeworkLayout } from './homeworkTypes';

interface HomeworkState {
  layout: HomeworkLayout;
}

interface HomeworkActions {
  initialize: (lessonId: string, layout?: HomeworkLayout) => void;
  addQuestion: (type: HomeworkQuestionType, index?: number) => void; // Изменено: добавлен параметр index
  updateQuestion: (id: string, patch: Partial<HomeworkQuestion>) => void;
  removeQuestion: (id: string) => void;
  reorderQuestions: (fromIndex: number, toIndex: number) => void;
  addOption: (questionId: string) => void;
  updateOption: (
    questionId: string,
    optionId: string,
    patch: Partial<HomeworkOption>,
  ) => void;
  removeOption: (questionId: string, optionId: string) => void;
  reorderOptions: (
    questionId: string,
    fromIndex: number,
    toIndex: number,
  ) => void;
  toJSON: () => HomeworkLayout;
}

export type HomeworkStore = HomeworkState & HomeworkActions;

const createEmptyLayout = (lessonId: string): HomeworkLayout => ({
  lessonId,
  questions: [],
});

const moveItem = <T,>(list: T[], from: number, to: number): T[] => {
  if (
    from === to ||
    from < 0 ||
    to < 0 ||
    from >= list.length ||
    to > list.length
  ) {
    return list;
  }
  const next = [...list];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
};

const insertItem = <T,>(list: T[], item: T, index?: number): T[] => {
  const next = [...list];
  if (index !== undefined && index >= 0 && index <= list.length) {
    next.splice(index, 0, item);
  } else {
    next.push(item);
  }
  return next;
};

export const useHomeworkStore = create<HomeworkStore>((set, get) => ({
  layout: createEmptyLayout(''),

  initialize: (lessonId, layout) => {
    const current = get().layout;
    if (!layout && current.lessonId === lessonId && current.questions.length > 0) {
      return;
    }
    set(() => ({
      layout: layout ?? createEmptyLayout(lessonId),
    }));
  },

  addQuestion: (type, index) =>
    set((state) => {
      const base: HomeworkQuestion = {
        id: nanoid(),
        type,
        title: '',
        score: 0,
        ...(type === 'single' ? { options: [] } : { description: '' }),
      } as HomeworkQuestion;

      return {
        layout: {
          ...state.layout,
          questions: insertItem(state.layout.questions, base, index),
        },
      };
    }),

  updateQuestion: (id, patch) =>
    set((state) => ({
      layout: {
        ...state.layout,
        questions: state.layout.questions.map((q) =>
          q.id === id
            ? ({ ...q, ...(patch as HomeworkQuestion) } as HomeworkQuestion)
            : q,
        ),
      },
    })),

  removeQuestion: (id) =>
    set((state) => ({
      layout: {
        ...state.layout,
        questions: state.layout.questions.filter((q) => q.id !== id),
      },
    })),

  reorderQuestions: (fromIndex, toIndex) =>
    set((state) => ({
      layout: {
        ...state.layout,
        questions: moveItem(state.layout.questions, fromIndex, toIndex),
      },
    })),

  addOption: (questionId) =>
    set((state) => ({
      layout: {
        ...state.layout,
        questions: state.layout.questions.map((q) => {
          if (q.id !== questionId || q.type !== 'single') return q;
          const nextOptions = [
            ...(q.options ?? []),
            { id: nanoid(), text: '' } as HomeworkOption,
          ];
          return { ...q, options: nextOptions };
        }),
      },
    })),

  updateOption: (questionId, optionId, patch) =>
    set((state) => ({
      layout: {
        ...state.layout,
        questions: state.layout.questions.map((q) => {
          if (q.id !== questionId || q.type !== 'single') return q;
          const nextOptions = (q.options ?? []).map((opt) =>
            opt.id === optionId
              ? ({ ...opt, ...(patch as HomeworkOption) } as HomeworkOption)
              : opt,
          );
          return { ...q, options: nextOptions };
        }),
      },
    })),

  removeOption: (questionId, optionId) =>
    set((state) => ({
      layout: {
        ...state.layout,
        questions: state.layout.questions.map((q) => {
          if (q.id !== questionId || q.type !== 'single') return q;
          const nextOptions = (q.options ?? []).filter(
            (opt) => opt.id !== optionId,
          );
          return { ...q, options: nextOptions };
        }),
      },
    })),

  reorderOptions: (questionId, fromIndex, toIndex) =>
    set((state) => ({
      layout: {
        ...state.layout,
        questions: state.layout.questions.map((q) => {
          if (q.id !== questionId || q.type !== 'single') return q;
          return {
            ...q,
            options: moveItem(q.options ?? [], fromIndex, toIndex),
          };
        }),
      },
    })),

  toJSON: () => {
    const { layout } = get();
    return serializeHomeworkLayout(layout);
  },
}));