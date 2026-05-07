import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { PageFrame, Spinner } from '@shared/ui';
import { useLessonBySlug } from '@shared/api/queries/courses';
import { useSaveLessonContent } from '@shared/api/mutations/courses';
import { CourseBuilder, useLessonBuilderStore } from '../../../features/course-builder';
import type { SubmitPayload } from '../../../features/course-builder';
import { parseLessonLayoutFromContentString, normalizeLessonLayoutForEditor } from '../../../features/course-builder/model/types';
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
  const [savedRevision, setSavedRevision] = useState(0);
  const [initialLessonSignature, setInitialLessonSignature] = useState<string | undefined>(undefined);

  useEffect(() => {
    setInitialized(false);
  }, [courseSlug, lessonSlug]);

  useEffect(() => {
    if (!lessonDetail || initialized) return;
    try {
      const layout = normalizeLessonLayoutForEditor(
        parseLessonLayoutFromContentString(lessonDetail.document),
      );
      useLessonBuilderStore.getState().initialize(layout);
    } catch {
      useLessonBuilderStore.getState().initialize({
        id: crypto.randomUUID(),
        title: lessonDetail.title,
        blocks: [],
      });
    }
    const { layout, pendingUploads } = useLessonBuilderStore.getState();
    setInitialLessonSignature(
      JSON.stringify({ lesson: layout, pendingUploadIds: Object.keys(pendingUploads).sort() }),
    );
    setInitialized(true);
  }, [lessonDetail, initialized]);

  const handleSave = (payload: SubmitPayload) => {
    const title = useLessonBuilderStore.getState().layout.title;
    saveMutation.mutate(
      {
        title,
        document: payload.document,
      },
      {
        onSuccess: () => {
          setSavedRevision((prev) => prev + 1);
        },
      },
    );
  };

  if (isError) {
    return (
      <PageFrame className={styles.errorWrapper}>
        <p>Не удалось загрузить урок</p>
      </PageFrame>
    );
  }

  if (isLoading) {
    return (
      <PageFrame className={styles.loaderWrapper}>
        <Spinner size="lg" />
      </PageFrame>
    );
  }

  if (!lessonDetail) {
    return (
      <PageFrame className={styles.errorWrapper}>
        <p>Не удалось загрузить урок</p>
      </PageFrame>
    );
  }

  if (!initialized) return null;

  return (
    <PageFrame className={styles.builderRoot}>
      <CourseBuilder
        courseSlug={courseSlug!}
        lessonSlug={lessonSlug!}
        lessonHomeworks={lessonDetail.homeworks}
        onSave={handleSave}
        saving={saveMutation.isPending}
        savedRevision={savedRevision}
        initialLessonSignature={initialLessonSignature}
      />
    </PageFrame>
  );
}
