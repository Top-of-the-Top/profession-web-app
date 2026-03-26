import type { LessonDetail } from '../../../shared/api/courseApi';

/**
 * Включить мок-режим: true — используем MOCK_LESSON ниже, false — реальный API.
 * Выключи когда бэкенд проснётся.
 */
export const USE_MOCK = true;

/**
 * Вставь сюда JSON из «Сохранить черновик» в CourseBuilder.
 * Формат: { version: 1, lesson: { id, title, blocks: [...] }, homework: ... }
 *
 * Код сам вытащит поле `lesson` и подставит в content.
 */
const BUILDER_JSON ={"version":1,"lesson":{"id":"Ei4VQY3BNzob1o0h0AIbc","title":"Урок 1. Излучение Xоккинга","blocks":[{"id":"o46juurxpDqyNYKWZEf4K","type":"text","x":4,"y":0,"w":11,"h":4,"html":"<div><div style=\"font-family: &quot;Golos Text&quot;, sans-serif;\"><span style=\"font-family: &quot;Golos Text&quot;, sans-serif; white-space-collapse: preserve;\">В одном небольшом городке жила-была девочка по имени Маша. Больше всего на свете она любила рисовать, но была у неё одна беда кисточка у неё была самая обычная, да и краски часто заканчивались.</span></div><div style=\"font-family: &quot;Golos Text&quot;, sans-serif;\"><span style=\"font-family: &quot;Golos Text&quot;, sans-serif; white-space-collapse: preserve;\">Однажды, гуляя в парке, Маша нашла странную кисточку, всю переливающуюся радужными красками. Кисточка оказалась волшебной стоило Маше нарисовать что-нибудь, как рисунок оживал.</span></div><div style=\"font-family: &quot;Golos Text&quot;, sans-serif;\"><span style=\"font-family: &quot;Golos Text&quot;, sans-serif; white-space-collapse: preserve;\">Первым делом девочка нарисовала для своей бабушки красивый букет цветов, который тут же наполнил всю квартиру чудесным ароматом. Потом она создала для друга, который боялся собак, смешного щенка, который стал его лучшим другом</span></div></div>","fontSizeIndex":1},{"id":"d2HVpyfaj-isLFg99dH4i","type":"video","x":0,"y":4,"w":15,"h":5,"url":""},{"id":"csIPKk7jESarbpDpENybr","type":"photo","x":0,"y":0,"w":4,"h":4,"url":""}]},"homework":{"lessonId":"12","questions":[{"id":"GpRuTq2NrTflK3IWyAQQM","title":"Вопрос 1","score":0,"type":"single","options":[{"id":"cM3FiFGk3gNe18Gvl2VZ5","text":"1","isCorrect":false},{"id":"v_ktqPhzIcUJ4wphwr3jR","text":"2","isCorrect":false}]},{"id":"TUsCIHuZCX59iOZkxYOhK","title":"Вопрос 2","score":0,"type":"single","options":[{"id":"0jAj-kSgBpXHk6z1tKHSV","text":"1","isCorrect":false},{"id":"gqpROfXkOnPbFblyJLA3n","text":"2","isCorrect":false}]}]}}

export const MOCK_LESSON: LessonDetail = {
  lesson_id: 1,
  course_id: 1,
  title: BUILDER_JSON.lesson.title,
  slug: 'mock-lesson',
  // Чтобы таймер в мок-режиме сразу показывал осмысленный обратный отсчет.
  // На старте примерно "00:12:36:54" (будет чуть отличаться из-за задержек).
  date: new Date(Date.now() + (12 * 3600 + 36 * 60 + 54) * 1000).toISOString(),
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  last_modified_by: null,
  content: BUILDER_JSON.lesson as unknown as Record<string, unknown>,
  has_homework: true,
  homework_slug: 'mock-homework',
  homework_deadline: new Date(Date.now() + 1000 * 60 * 60 * 27).toISOString(),
  board_url: 'https://miro.com/',
  webinar_url: 'https://meet.google.com/',
};

export const MOCK_COURSE_TITLE = 'Тестовый курс';
