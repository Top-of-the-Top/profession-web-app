import React from 'react';
import type { CoursePage } from '../../model/types';
import type { HomeworkQuestion } from '../../model/homeworkTypes';
import { FONT_SIZE_STEPS, DEFAULT_FONT_SIZE_INDEX } from '../../lib/constants';
import styles from './CourseRenderer.module.css';

interface CourseRendererProps {
  data: CoursePage;
}

const TextBlockView: React.FC<{
  html: string;
  fontSizeIndex?: number;
}> = ({ html, fontSizeIndex }) => {
  const fontSize = FONT_SIZE_STEPS[fontSizeIndex ?? DEFAULT_FONT_SIZE_INDEX] ?? FONT_SIZE_STEPS[DEFAULT_FONT_SIZE_INDEX];

  return (
    <div
      className={styles.textBlock}
      style={{ fontSize }}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
};

const PhotoBlockView: React.FC<{ url: string }> = ({ url }) => {
  if (!url) return <div className={styles.mediaPlaceholder}>Изображение не загружено</div>;
  return (
    <div className={styles.photoBlock}>
      <img src={url} alt="" loading="lazy" />
    </div>
  );
};

const VideoBlockView: React.FC<{ url: string }> = ({ url }) => {
  if (!url) return <div className={styles.mediaPlaceholder}>Видео не загружено</div>;
  return (
    <div className={styles.videoBlock}>
      <video src={url} controls playsInline />
    </div>
  );
};

const QuestionView: React.FC<{
  question: HomeworkQuestion;
  index: number;
}> = ({ question, index }) => {
  return (
    <div className={styles.questionCard}>
      <div className={styles.questionHeader}>
        <span className={styles.questionNumber}>#{index + 1}</span>
        <span className={styles.questionTitleText}>
          {question.title || 'Без заголовка'}
        </span>
        {question.score > 0 && (
          <span className={styles.questionScore}>
            {question.score} {pluralBall(question.score)}
          </span>
        )}
      </div>

      {'description' in question && question.description && (
        <div className={styles.questionDescription}>{question.description}</div>
      )}

      {question.type === 'single' && (
        <div className={styles.optionsList}>
          {question.options.map((opt) => (
            <div key={opt.id} className={styles.optionRow}>
              <div className={styles.optionRadio} />
              <span className={styles.optionText}>
                {opt.text || 'Вариант без текста'}
              </span>
            </div>
          ))}
        </div>
      )}

      {question.type === 'text' && (
        <div className={styles.answerPlaceholder}>Поле для развёрнутого ответа</div>
      )}

      {question.type === 'file' && (
        <div className={styles.answerPlaceholder}>Загрузка файла</div>
      )}
    </div>
  );
};

function pluralBall(n: number): string {
  const abs = Math.abs(n) % 100;
  const last = abs % 10;
  if (abs > 10 && abs < 20) return 'баллов';
  if (last > 1 && last < 5) return 'балла';
  if (last === 1) return 'балл';
  return 'баллов';
}

export const CourseRenderer: React.FC<CourseRendererProps> = ({ data }) => {
  const { lesson, homework } = data;

  const maxRow = lesson.blocks.reduce(
    (acc, b) => Math.max(acc, b.y + b.h),
    0,
  );

  return (
    <div className={styles.renderer}>
      <h1 className={styles.lessonTitle}>{lesson.title}</h1>

      {lesson.blocks.length > 0 ? (
        <div
          className={styles.blockGrid}
          style={{ gridTemplateRows: `repeat(${maxRow}, minmax(60px, auto))` }}
        >
          {lesson.blocks.map((block) => (
            <div
              key={block.id}
              className={styles.blockCell}
              style={{
                gridColumn: `${block.x + 1} / span ${block.w}`,
                gridRow: `${block.y + 1} / span ${block.h}`,
              }}
            >
              {block.type === 'text' && (
                <TextBlockView
                  html={block.html}
                  fontSizeIndex={block.fontSizeIndex}
                />
              )}
              {block.type === 'photo' && <PhotoBlockView url={block.url} />}
              {block.type === 'video' && <VideoBlockView url={block.url} />}
            </div>
          ))}
        </div>
      ) : (
        <div className={styles.emptyState}>Контент урока пуст</div>
      )}

      {homework && homework.questions.length > 0 && (
        <>
          <div className={styles.divider} />
          <section className={styles.homeworkSection}>
            <h2 className={styles.homeworkTitle}>Домашнее задание</h2>
            <div className={styles.questionList}>
              {homework.questions.map((q, i) => (
                <QuestionView key={q.id} question={q} index={i} />
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
};
