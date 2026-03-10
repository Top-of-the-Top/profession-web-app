import { create } from 'zustand';
import { nanoid } from 'nanoid';
import type {
  Block,
  BlockType,
  CourseStructure,
  Lesson,
  Module,
} from './types';
import { serializeCourseStructure } from './types';

interface CourseBuilderState {
  structure: CourseStructure;
  selectedModuleId?: string;
  selectedLessonId?: string;
  isSaving: boolean;
  lastSavedAt?: string;
}

interface CourseBuilderActions {
  initialize: (structure: CourseStructure) => void;
  selectLesson: (moduleId: string, lessonId: string) => void;
  addModule: () => void;
  addLesson: (moduleId: string) => void;
  addBlock: (lessonId: string, type: BlockType) => void;
  updateBlock: (lessonId: string, blockId: string, patch: Partial<Block>) => void;
  reorderBlocks: (lessonId: string, fromIndex: number, toIndex: number) => void;
  moveBlockToLesson: (
    fromLessonId: string,
    toLessonId: string,
    blockId: string,
    toIndex: number,
  ) => void;
  reorderModules: (fromIndex: number, toIndex: number) => void;
  reorderLessons: (moduleId: string, fromIndex: number, toIndex: number) => void;
  toJSON: () => CourseStructure;
  startSaving: () => void;
  finishSaving: () => void;
}

export type CourseBuilderStore = CourseBuilderState & CourseBuilderActions;

const createEmptyStructure = (): CourseStructure => ({
  id: nanoid(),
  title: 'Новый курс',
  modules: [],
});

const moveItem = <T,>(array: T[], fromIndex: number, toIndex: number): T[] => {
  const next = array.slice();
  const [item] = next.splice(fromIndex, 1);
  next.splice(toIndex, 0, item);
  return next;
};

export const useCourseBuilderStore = create<CourseBuilderStore>((set, get) => ({
  structure: createEmptyStructure(),
  selectedModuleId: undefined,
  selectedLessonId: undefined,
  isSaving: false,
  lastSavedAt: undefined,

  initialize: (structure) =>
    set(() => ({
      structure,
      selectedModuleId: structure.modules[0]?.id,
      selectedLessonId: structure.modules[0]?.lessons[0]?.id,
    })),

  selectLesson: (moduleId, lessonId) =>
    set(() => ({
      selectedModuleId: moduleId,
      selectedLessonId: lessonId,
    })),

  addModule: () =>
    set((state) => {
      const newModule: Module = {
        id: nanoid(),
        title: `Модуль ${state.structure.modules.length + 1}`,
        lessons: [],
      };

      const modules = [...state.structure.modules, newModule];

      return {
        structure: { ...state.structure, modules },
        selectedModuleId: newModule.id,
        selectedLessonId: undefined,
      };
    }),

  addLesson: (moduleId) =>
    set((state) => {
      const modules = state.structure.modules.map((module) => {
        if (module.id !== moduleId) return module;

        const newLesson: Lesson = {
          id: nanoid(),
          title: `Урок ${module.lessons.length + 1}`,
          blocks: [],
        };

        return {
          ...module,
          lessons: [...module.lessons, newLesson],
        };
      });

      const module = modules.find((m) => m.id === moduleId);
      const newLesson = module?.lessons[module.lessons.length - 1];

      return {
        structure: { ...state.structure, modules },
        selectedModuleId: moduleId,
        selectedLessonId: newLesson?.id,
      };
    }),

  addBlock: (lessonId, type) =>
    set((state) => {
      const modules = state.structure.modules.map((module) => ({
        ...module,
        lessons: module.lessons.map((lesson) => {
          if (lesson.id !== lessonId) return lesson;

          let newBlock: Block;
          if (type === 'text') {
            newBlock = { id: nanoid(), type: 'text', content: '' };
          } else if (type === 'video') {
            newBlock = { id: nanoid(), type: 'video', url: '', description: '' };
          } else if (type === 'homework') {
            newBlock = { id: nanoid(), type: 'homework', instructions: '', maxScore: 0 };
          } else {
            newBlock = { id: nanoid(), type: 'quiz', question: '', options: [] };
          }

          return {
            ...lesson,
            blocks: [...lesson.blocks, newBlock],
          };
        }),
      }));

      return {
        structure: { ...state.structure, modules },
      };
    }),

  updateBlock: (lessonId, blockId, patch) =>
    set((state) => {
      const modules = state.structure.modules.map((module) => ({
        ...module,
        lessons: module.lessons.map((lesson) => {
          if (lesson.id !== lessonId) return lesson;

          return {
            ...lesson,
            blocks: lesson.blocks.map((block) => {
              if (block.id !== blockId) return block;
              return { ...(block as Block), ...(patch as Block) };
            }),
          };
        }),
      }));

      return {
        structure: { ...state.structure, modules },
      };
    }),

  reorderBlocks: (lessonId, fromIndex, toIndex) =>
    set((state) => {
      const modules = state.structure.modules.map((module) => ({
        ...module,
        lessons: module.lessons.map((lesson) => {
          if (lesson.id !== lessonId) return lesson;

          return {
            ...lesson,
            blocks: moveItem(lesson.blocks, fromIndex, toIndex),
          };
        }),
      }));

      return {
        structure: { ...state.structure, modules },
      };
    }),

  moveBlockToLesson: (fromLessonId, toLessonId, blockId, toIndex) =>
    set((state) => {
      let movedBlock: Block | undefined;

      const modules = state.structure.modules.map((module) => ({
        ...module,
        lessons: module.lessons.map((lesson) => {
          if (lesson.id === fromLessonId) {
            const remainingBlocks = lesson.blocks.filter((block) => {
              if (block.id === blockId) {
                movedBlock = block;
                return false;
              }
              return true;
            });
            return { ...lesson, blocks: remainingBlocks };
          }

          if (lesson.id === toLessonId && movedBlock) {
            const nextBlocks = lesson.blocks.slice();
            nextBlocks.splice(toIndex, 0, movedBlock);
            return { ...lesson, blocks: nextBlocks };
          }

          return lesson;
        }),
      }));

      return {
        structure: { ...state.structure, modules },
      };
    }),

  reorderModules: (fromIndex, toIndex) =>
    set((state) => ({
      structure: {
        ...state.structure,
        modules: moveItem(state.structure.modules, fromIndex, toIndex),
      },
    })),

  reorderLessons: (moduleId, fromIndex, toIndex) =>
    set((state) => {
      const modules = state.structure.modules.map((module) => {
        if (module.id !== moduleId) return module;

        return {
          ...module,
          lessons: moveItem(module.lessons, fromIndex, toIndex),
        };
      });

      return {
        structure: { ...state.structure, modules },
      };
    }),

  toJSON: () => {
    const { structure } = get();
    return serializeCourseStructure(structure);
  },

  startSaving: () =>
    set(() => ({
      isSaving: true,
    })),

  finishSaving: () =>
    set(() => ({
      isSaving: false,
      lastSavedAt: new Date().toISOString(),
    })),
}));

