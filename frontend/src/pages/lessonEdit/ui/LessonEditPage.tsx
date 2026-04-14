import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Spinner, PageTransition } from '@shared/ui';
import { useLessonBySlug } from '@shared/api/queries/courses';
import { useSaveLessonContent } from '@shared/api/mutations/courses';
import { CourseBuilder, useLessonBuilderStore } from '../../../features/course-builder';
import type { SubmitPayload } from '../../../features/course-builder';
import { parseLessonLayoutFromContentString } from '../../../features/course-builder/model/types';
import styles from './LessonEditPage.module.css';

export default function LessonEditPage() {
  const { slug: courseSlug, lessonSlug } = useParams<{
    slug: string;
    lessonSlug: string;
  }>();

  const {
    data: lessonDetail,
    isLoading,
    isError,
  } = useLessonBySlug(courseSlug, lessonSlug);

  const saveMutation = useSaveLessonContent(courseSlug ?? '', lessonSlug ?? '');
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    setInitialized(false);
  }, [courseSlug, lessonSlug]);

  useEffect(() => {
    if (!lessonDetail || initialized) return;
    try {
      const layout = parseLessonLayoutFromContentString(lessonDetail.document);
      useLessonBuilderStore.getState().initialize(layout);
    } catch {
      useLessonBuilderStore.getState().initialize({
        id: crypto.randomUUID(),
        title: lessonDetail.title,
        blocks: [],
      });
    }
    setInitialized(true);
  }, [lessonDetail, initialized]);

  const handleSave = (payload: SubmitPayload) => {
    const title = useLessonBuilderStore.getState().layout.title;
    saveMutation.mutate({
      title,
      document: payload.document,
      files: payload.files,
    });
  };

  if (isError) {
    return (
      <PageTransition>
        <div className={styles.errorWrapper}>
          <p>Не удалось загрузить урок</p>
        </div>
      </PageTransition>
    );
  }

  if (isLoading) {
    return (
      <PageTransition>
        <div className={styles.loaderWrapper}>
          <Spinner size="lg" />
        </div>
      </PageTransition>
    );
  }

  if (!lessonDetail) {
    return (
      <PageTransition>
        <div className={styles.errorWrapper}>
          <p>Не удалось загрузить урок</p>
        </div>
      </PageTransition>
    );
  }

  if (!initialized) return null;

  return (
    <PageTransition>
      <CourseBuilder
        courseSlug={courseSlug!}
        lessonSlug={lessonSlug!}
        onSave={handleSave}
        saving={saveMutation.isPending}
      />
    </PageTransition>
  );
}
