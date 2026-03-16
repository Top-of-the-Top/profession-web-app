import React from 'react';
import type { Block, LessonLayout } from '../model/types';

interface CourseRendererProps {
  layout: LessonLayout;
}

const renderBlock = (block: Block) => {
  switch (block.type) {
    case 'text':
      return (
        <div dangerouslySetInnerHTML={{ __html: block.html }} />
      );
    case 'photo':
      return block.url ? (
        <img src={block.url} alt="" style={{ maxWidth: '100%' }} />
      ) : null;
    case 'video':
      return block.url ? (
        <video src={block.url} controls style={{ maxWidth: '100%' }} />
      ) : null;
    default:
      return null;
  }
};

export const CourseRenderer: React.FC<CourseRendererProps> = ({ layout }) => {
  return (
    <div>
      <h1>{layout.title}</h1>
      {layout.blocks.map((block) => (
        <div key={block.id}>{renderBlock(block)}</div>
      ))}
    </div>
  );
};

