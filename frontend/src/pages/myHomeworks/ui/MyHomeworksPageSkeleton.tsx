import { Skeleton } from '@shared/ui';
import styles from './MyHomeworksPage.module.css';

const SKELETON_ROWS = 8;

type StudentTab = 'todo' | 'pending' | 'reviewed';

export function MyHomeworksTeacherTableSkeleton() {
  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th>Ученик</th>
          <th className={styles.colHomework}>Домашнее задание</th>
          <th>Выполнено</th>
          <th>Сдано</th>
          <th>Статус</th>
        </tr>
      </thead>
      <tbody>
        {Array.from({ length: SKELETON_ROWS }).map((_, r) => (
          <tr key={r} className={styles.skeletonDataRow}>
            <td>
              <div className={styles.skeletonPrimaryCell}>
                <Skeleton className={styles.skeletonLineLg} />
                <Skeleton className={styles.skeletonLineSm} />
              </div>
            </td>
            <td className={styles.colHomework}>
              <Skeleton className={styles.skeletonLineMd} />
            </td>
            <td>
              <Skeleton className={styles.skeletonLineXs} />
            </td>
            <td>
              <Skeleton className={styles.skeletonLineXs} />
            </td>
            <td>
              <Skeleton className={styles.skeletonStatusOrb} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function MyHomeworksStudentTableSkeleton({ tab }: { tab: StudentTab }) {
  return (
    <table className={styles.table}>
      <thead>
        <tr>
          <th>Домашнее задание</th>
          <th>Баллы</th>
          <th>{tab === 'pending' ? 'Сдано' : 'Дедлайн'}</th>
          <th />
        </tr>
      </thead>
      <tbody>
        {Array.from({ length: SKELETON_ROWS }).map((_, r) => (
          <tr key={r} className={styles.skeletonDataRow}>
            <td>
              <div className={styles.skeletonPrimaryCell}>
                <Skeleton className={styles.skeletonLineLg} />
                <Skeleton className={styles.skeletonLineSm} />
              </div>
            </td>
            <td>
              <Skeleton className={styles.skeletonLineXs} />
            </td>
            <td>
              <Skeleton className={styles.skeletonLineMd} />
            </td>
            <td className={styles.arrowCell}>
              <Skeleton className={styles.skeletonArrowStub} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
