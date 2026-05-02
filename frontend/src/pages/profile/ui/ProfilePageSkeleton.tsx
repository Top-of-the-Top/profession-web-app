import { Card, CardContent, PageFrame, Skeleton } from '@shared/ui';
import styles from './ProfilePage.module.css';

export function ProfilePageSkeleton() {
  return (
    <PageFrame>
      <div className={styles.body}>
        <Skeleton className={styles.skeletonProfileTitle} />
        <Card className={styles.profilePageCard}>
          <CardContent className={styles.profilePageContent}>
            <div className={styles.profileSection}>
              <div className={styles.profileField}>
                <div className={styles.profileFieldContent}>
                  <Skeleton shape="circle" className={styles.skeletonAvatar} />
                  <div className={styles.profileFieldInfo}>
                    <Skeleton className={styles.skeletonLabel} />
                    <Skeleton className={styles.skeletonValueWide} />
                  </div>
                </div>
                <Skeleton shape="circle" className={styles.skeletonActionIcon} />
              </div>
            </div>

            <div className={styles.profileSection}>
              <Skeleton className={styles.skeletonSectionTitle} />
              {Array.from({ length: 2 }).map((_, idx) => (
                <div key={idx} className={styles.profileField}>
                  <div className={styles.profileFieldContent}>
                    <Skeleton shape="circle" className={styles.skeletonFieldIcon} />
                    <div className={styles.profileFieldInfo}>
                      <Skeleton className={styles.skeletonLabel} />
                      <Skeleton className={styles.skeletonValue} />
                    </div>
                  </div>
                  <Skeleton shape="circle" className={styles.skeletonActionIcon} />
                </div>
              ))}
            </div>

            <div className={styles.profileSection}>
              <Skeleton className={styles.skeletonSectionTitle} />
              {Array.from({ length: 2 }).map((_, idx) => (
                <div key={idx} className={styles.profileField}>
                  <div className={styles.profileFieldContent}>
                    <Skeleton shape="circle" className={styles.skeletonFieldIcon} />
                    <div className={styles.profileFieldInfo}>
                      <Skeleton className={styles.skeletonLabel} />
                      <Skeleton className={styles.skeletonValue} />
                    </div>
                  </div>
                  <Skeleton shape="circle" className={styles.skeletonActionIcon} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </PageFrame>
  );
}
