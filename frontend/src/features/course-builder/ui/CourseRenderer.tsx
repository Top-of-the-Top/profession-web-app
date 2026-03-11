import React from 'react';
import type { Block, CourseStructure, Lesson, Module } from '../model/types';

interface CourseRendererProps {
  structure: CourseStructure;
}

const renderBlock = (block: Block) => {
  switch (block.type) {
    case 'text':
      return <p>{block.content}</p>;
    case 'video':
      return (
        <div>
          <a href={block.url} target="_blank" rel="noreferrer">
            Открыть видео
          </a>
          {block.description && <p>{block.description}</p>}
        </div>
      );
    case 'homework':
      return <p>{block.instructions}</p>;
    case 'quiz':
      return <p>{block.question}</p>;
    default:
      return null;
  }
};

export const CourseRenderer: React.FC<CourseRendererProps> = ({ structure }) => {
  return (
    <div>
      <h1>{structure.title}</h1>
      {structure.modules.map((module: Module) => (
        <section key={module.id}>
          <h2>{module.title}</h2>
          {module.lessons.map((lesson: Lesson) => (
            <article key={lesson.id}>
              <h3>{lesson.title}</h3>
              {lesson.blocks.map((block) => (
                <div key={block.id}>{renderBlock(block)}</div>
              ))}
            </article>
          ))}
        </section>
      ))}
    </div>
  );
};

