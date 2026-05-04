import { useLayoutEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import { Button, Input, Spinner } from '@shared/ui';
import { useCreateSection } from '@shared/api/mutations/courses';
import { cn } from '@shared/lib/utils';
import styles from '../CourseLessonsPage.module.css';

export function AddSectionRow({ courseSlug }: { courseSlug: string }) {
  const [title, setTitle] = useState('');
  const [expanded, setExpanded] = useState(false);
  const createMutation = useCreateSection(courseSlug);

  useLayoutEffect(() => {
    if (!expanded) return;
    window.requestAnimationFrame(() => {
      document.getElementById('new-section-input')?.focus();
    });
  }, [expanded]);

  const submit = () => {
    const trimmed = title.trim();
    if (!trimmed) return;
    void (async () => {
      try {
        await createMutation.mutateAsync({ title: trimmed });
        setTitle('');
        setExpanded(false);
      } catch {
        return;
      }
    })();
  };

  const cancel = () => {
    setTitle('');
    setExpanded(false);
  };

  return (
    <div className={styles.inlineAddSection}>
      {!expanded ? (
        <div className={styles.addFlowCollapsed}>
          <Button
            type="button"
            variant="outline"
            className={styles.addSectionTriggerBtn}
            onClick={() => setExpanded(true)}
          >
            <Plus size={18} strokeWidth={2} />
            Добавить раздел
          </Button>
        </div>
      ) : (
        <div className={styles.addSectionExpanded}>
          <Input
            id="new-section-input"
            className={cn(
              styles.inlineAddSectionInput,
              styles.addFlowInputAnim
            )}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Название"
            disabled={createMutation.isPending}
            onKeyDown={(e) => {
              if (e.key === 'Enter') submit();
              if (e.key === 'Escape') cancel();
            }}
          />
          <div className={cn(styles.addFlowActions, styles.addFlowActionsAnim)}>
            <Button
              type="button"
              variant="primary"
              className={styles.addSectionSubmitBtn}
              disabled={!title.trim() || createMutation.isPending}
              onClick={submit}
            >
              {createMutation.isPending ? (
                <Spinner />
              ) : (
                <>
                  <Plus size={18} strokeWidth={2} />
                  Добавить раздел
                </>
              )}
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={createMutation.isPending}
              onClick={cancel}
            >
              Отмена
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
