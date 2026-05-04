import { Pencil, Trash2 } from 'lucide-react';
import { Button } from '@shared/ui';
import styles from '../CourseLessonsPage.module.css';

interface SectionStaffToolsProps {
  canManageSection: boolean;
  editingTitle: boolean;
  onEditTitle: () => void;
  onDeleteSection: () => void;
  deletePending: boolean;
}

export function SectionStaffTools({
  canManageSection,
  editingTitle,
  onEditTitle,
  onDeleteSection,
  deletePending,
}: SectionStaffToolsProps) {
  return (
    <div
      className={styles.staffSectionTools}
      role="group"
      onClick={(e) => e.stopPropagation()}
    >
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        className={styles.staffIconEditBtn}
        disabled={!canManageSection || editingTitle}
        title={
          canManageSection
            ? 'Редактировать название'
            : 'У раздела нет slug — обновите страницу или проверьте API'
        }
        onClick={onEditTitle}
      >
        <Pencil size={21} strokeWidth={2} />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        className={styles.staffIconDeleteBtn}
        disabled={!canManageSection || deletePending}
        title={
          canManageSection
            ? 'Удалить раздел'
            : 'У раздела нет slug — обновите страницу или проверьте API'
        }
        onClick={onDeleteSection}
      >
        <Trash2 size={21} strokeWidth={2} />
      </Button>
    </div>
  );
}
