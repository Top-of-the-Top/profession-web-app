import { lazy, Suspense } from 'react';
import { ProfilePageSkeleton } from './ProfilePageSkeleton';

const ProfilePage = lazy(() => import('./ProfilePage'));

export default function ProfileRoutePage() {
  return (
    <Suspense fallback={<ProfilePageSkeleton />}>
      <ProfilePage />
    </Suspense>
  );
}
