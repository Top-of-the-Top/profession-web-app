import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  Card,
  CardContent,
  Button,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  Avatar,
  AvatarFallback,
  AvatarImage,
  PageFrame,
} from '@shared/ui';
import { Mail, Phone, Calendar, Pencil, Plus, Venus, Mars } from 'lucide-react';
import styles from './ProfilePage.module.css';
import { cn } from '@shared/lib/utils';
import ChangeName from './ChangeName';
import ConfirmContact from './ConfirmContact';
import {
  profileApi,
  type ProfileData,
  type UpdateProfilePayload,
} from '@shared/api/profileApi';
import { useProfile, profileKeys } from '@shared/api/queries/profile';
import { useUpdateProfile } from '@shared/api/mutations/profile';
import { parseApiError } from '@shared/lib/api/parseApiError';
import {
  messageForApiFailure,
  notifyError,
  notifySuccess,
} from '@shared/lib/sileo/notify';
import { validateEmailOrPhone } from '@shared/utils/validation';
import {
  uploadMediaAsset,
  MediaUploadError,
} from '@shared/lib/uploads/uploadMediaAsset';
import { IntentValidationError } from '@shared/lib/uploads/intentLimits';
import { ProfilePageSkeleton } from './ProfilePageSkeleton';

function notifyProfileSaveError(err: unknown) {
  if (err instanceof Error && err.message === 'AUTH_EXPIRED') {
    notifyError({
      title: 'нужен повторный вход',
      description: 'Сессия истекла. Войдите в аккаунт снова.',
    });
    return;
  }
  const parsed = parseApiError(err);
  if (!parsed) {
    const fb = messageForApiFailure('profileUpdate', 0, {});
    notifyError({
      title: fb.title,
      description: err instanceof Error ? err.message : fb.description,
    });
    return;
  }
  const msg = messageForApiFailure('profileUpdate', parsed.status, parsed.body);
  notifyError({ title: msg.title, description: msg.description });
}

interface ProfileFieldProps {
  icon: React.ReactNode;
  label: string;
  value: string | null;
  actionButton: React.ReactNode;
  onClick?: () => void;
}

const ProfileField = ({
  icon,
  label,
  value,
  actionButton,
  onClick,
}: ProfileFieldProps) => (
  <div className={styles.profileField} onClick={onClick}>
    <div className={styles.profileFieldContent}>
      <div className={styles.profileFieldIcon}>{icon}</div>
      <div className={styles.profileFieldInfo}>
        <span className={styles.profileFieldLabel}>{label}</span>
        <span className={styles.profileFieldValue}>{value || '-'}</span>
      </div>
    </div>
    <div className={styles.profileFieldAction}>{actionButton}</div>
  </div>
);

export default function ProfilePage() {
  const queryClient = useQueryClient();
  const { data: user, isLoading } = useProfile();
  const updateProfile = useUpdateProfile();
  const [profile, setProfile] = useState<ProfileData | null>(user ?? null);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);

  const [isChangeNameMenuOpen, setChangeMenuOpen] = useState(false);
  const [isEmailMenuOpen, setEmailMenuOpen] = useState(false);
  const [isPhoneMenuOpen, setPhoneMenuOpen] = useState(false);
  const [gender, setGender] = useState<string | null>(null);

  useEffect(() => {
    setProfile(user ?? null);
    setGender(user?.gender || null);
    setAvatarUrl(user?.avatar || null);
  }, [user]);

  // --- Изменение пола ---
  const updateGender = async (value: string) => {
    const previous = gender;
    setGender(value);
    try {
      await updateProfile.mutateAsync({ gender: value });
      setProfile((prev) => {
        return prev ? { ...prev, gender: value } : prev;
      });
    } catch (err) {
      notifyProfileSaveError(err);
      setGender(previous);
    }
  };

  const openNameMenu = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    setChangeMenuOpen(true);
  };
  const toggleEmailMenu = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    setEmailMenuOpen((prev) => !prev);
  };
  const togglePhoneMenu = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    setPhoneMenuOpen((prev) => !prev);
  };

  if (isLoading && !profile) return <ProfilePageSkeleton />;
  if (!profile) return <div>Профиль недоступен</div>;

  const handleNameSave = async (data: {
    firstName: string;
    lastName: string;
    avatar?: File | null;
  }) => {
    const prevAvatar = profile.avatar;
    let blobUrl: string | null = null;

    try {
      const updateData: UpdateProfilePayload = {
        first_name: data.firstName,
        last_name: data.lastName,
      };

      if (data.avatar instanceof File) {
        blobUrl = URL.createObjectURL(data.avatar);
        try {
          const { assetId } = await uploadMediaAsset('user_avatar', data.avatar);
          updateData.avatar_asset_id = assetId;
        } catch (err) {
          if (
            err instanceof IntentValidationError ||
            err instanceof MediaUploadError
          ) {
            notifyError({
              title: 'не удалось загрузить аватар',
              description: err.message,
            });
          } else {
            notifyProfileSaveError(err);
          }
          if (blobUrl) URL.revokeObjectURL(blobUrl);
          throw err;
        }
      }

      const optimistic: ProfileData = {
        ...profile,
        first_name: data.firstName,
        last_name: data.lastName,
        ...(blobUrl ? { avatar: blobUrl } : {}),
      };

      setProfile(optimistic);
      setAvatarUrl(blobUrl ?? prevAvatar);

      await updateProfile.mutateAsync(updateData);

      const fresh = await queryClient.fetchQuery({
        queryKey: profileKeys.me(),
        queryFn: () => profileApi.getProfile(),
      });

      if (blobUrl && fresh.avatar === prevAvatar) {
        const merged = { ...fresh, avatar: blobUrl };
        setProfile(merged);
        setAvatarUrl(blobUrl);
      } else {
        setProfile(fresh);
        setAvatarUrl(fresh.avatar);
        if (blobUrl) URL.revokeObjectURL(blobUrl);
      }
    } catch (err) {
      if (
        !(err instanceof IntentValidationError) &&
        !(err instanceof MediaUploadError)
      ) {
        notifyProfileSaveError(err);
      }
      setAvatarUrl(prevAvatar);
      if (blobUrl) URL.revokeObjectURL(blobUrl);
      const reverted = await queryClient
        .fetchQuery({
          queryKey: profileKeys.me(),
          queryFn: () => profileApi.getProfile(),
        })
        .catch(() => null);
      if (reverted) {
        setProfile(reverted);
      }
      throw err;
    }
  };

  const handleContactRequest = async (
    rawContact: string,
    type: 'email' | 'phone'
  ) => {
    try {
      if (type === 'email') {
        await updateProfile.mutateAsync({ email: rawContact.trim() });
      } else {
        const v = validateEmailOrPhone(rawContact);
        if (!v.isValid) {
          notifyError({
            title: 'проверьте номер',
            description: 'Введите корректный номер телефона.',
          });
          throw new Error('invalid_phone');
        }
        await updateProfile.mutateAsync({ phone_number: v.normalized });
      }
      notifySuccess({
        title: 'код отправлен',
        description:
          type === 'email'
            ? 'Проверьте почту и введите код ниже.'
            : 'Проверьте SMS и введите код ниже.',
      });
    } catch (err) {
      if (err instanceof Error && err.message === 'invalid_phone') {
        throw err;
      }
      notifyProfileSaveError(err);
      throw err;
    }
  };

  const handleContactVerify = async (code: string, type: 'email' | 'phone') => {
    try {
      if (type === 'email') {
        await profileApi.verifyEmailChange(code);
      } else {
        await profileApi.verifyPhoneChange(code);
      }
      const fresh = await queryClient.fetchQuery({
        queryKey: profileKeys.me(),
        queryFn: () => profileApi.getProfile(),
      });
      setProfile(fresh);
      notifySuccess({
        title: 'готово',
        description:
          type === 'email'
            ? 'Почта подтверждена и обновлена.'
            : 'Телефон подтверждён и обновлён.',
      });
      setEmailMenuOpen(false);
      setPhoneMenuOpen(false);
    } catch (err) {
      if (err instanceof Error && err.message === 'AUTH_EXPIRED') {
        notifyError({
          title: 'нужен повторный вход',
          description: 'Сессия истекла. Войдите в аккаунт снова.',
        });
        return;
      }
      const parsed = parseApiError(err);
      const scene =
        type === 'email' ? 'profileVerifyEmail' : 'profileVerifyPhone';
      if (parsed) {
        const m = messageForApiFailure(scene, parsed.status, parsed.body);
        notifyError({ title: m.title, description: m.description });
        return;
      }
      notifyError({ title: 'ошибка', description: 'Повторите попытку.' });
    }
  };

  const getInitials = () => {
    const first = profile.first_name?.[0] || '';
    const last = profile.last_name?.[0] || '';
    return (first + last).toUpperCase() || 'U';
  };

  return (
    <>
      <ChangeName
        open={isChangeNameMenuOpen}
        onOpenChange={setChangeMenuOpen}
        onSave={handleNameSave}
        currentFirstName={profile.first_name || ''}
        currentLastName={profile.last_name || ''}
        currentAvatar={avatarUrl}
      />
      <ConfirmContact
        type="email"
        isVisible={isEmailMenuOpen}
        onClose={toggleEmailMenu}
        initialContact={profile.email}
        onRequestChange={(c) => handleContactRequest(c, 'email')}
        onVerify={(code) => handleContactVerify(code, 'email')}
      />
      <ConfirmContact
        type="phone"
        isVisible={isPhoneMenuOpen}
        onClose={togglePhoneMenu}
        initialContact={profile.phone_number}
        onRequestChange={(c) => handleContactRequest(c, 'phone')}
        onVerify={(code) => handleContactVerify(code, 'phone')}
      />

      <PageFrame>
        <div className={styles.body}>
        <h1 className={styles.profilePageTitle}>Личный кабинет</h1>
        <Card className={styles.profilePageCard}>
          <CardContent className={styles.profilePageContent}>
            <div className={styles.profileSection}>
              <div className={styles.profileField} onClick={openNameMenu}>
                <div className={styles.profileFieldContent}>
                  <div className={styles.profileFieldIcon}>
                    <Avatar className={styles.fieldAvatar}>
                      <AvatarImage src={avatarUrl || ''} />
                      <AvatarFallback className={styles.fieldAvatarFallback}>
                        {getInitials()}
                      </AvatarFallback>
                    </Avatar>
                  </div>
                  <div className={styles.profileFieldInfo}>
                    <span className={styles.profileFieldLabel}>
                      Имя и Фамилия
                    </span>
                    <span className={styles.profileFieldValue}>
                      {`${profile.first_name ?? ''} ${profile.last_name ?? ''}`}
                    </span>
                  </div>
                </div>
                <div className={styles.profileFieldAction}>
                  <Button
                    variant="ghost"
                    size="icon"
                    className={styles.pencilEditButton}
                    onClick={openNameMenu}
                  >
                    <Pencil className={styles.pencilIcon} size={16} />
                  </Button>
                </div>
              </div>
            </div>

            <div className={styles.profileSection}>
              <h2 className={styles.profileSectionTitle}>Контакты</h2>
              <ProfileField
                icon={<Mail size={20} />}
                label="Почта"
                value={profile.email}
                onClick={toggleEmailMenu}
                actionButton={
                  <Button
                    variant="ghost"
                    size="icon"
                    className={styles.pencilEditButton}
                    onClick={toggleEmailMenu}
                  >
                    <Pencil className={styles.pencilIcon} size={16} />
                  </Button>
                }
              />
              <ProfileField
                icon={<Phone size={20} />}
                label="Телефон"
                value={profile.phone_number}
                onClick={togglePhoneMenu}
                actionButton={
                  <Button
                    variant="ghost"
                    size="icon"
                    className={styles.pencilEditButton}
                    onClick={togglePhoneMenu}
                  >
                    <Plus className={styles.plusIcon} size={16} />
                  </Button>
                }
              />
            </div>

            <div className={styles.profileSection}>
              <h2 className={styles.profileSectionTitle}>
                Дополнительные данные
              </h2>
              <ProfileField
                icon={<Calendar size={20} />}
                label="Дата рождения"
                value={profile.birthday}
                actionButton={
                  <Button
                    variant="ghost"
                    size="icon"
                    className={styles.pencilEditButton}
                  >
                    <Plus className={styles.plusIcon} size={16} />
                  </Button>
                }
              />

              <Select value={gender ?? ''} onValueChange={updateGender}>
                <SelectTrigger
                  className={cn(styles.profileField, styles.genderTrigger)}
                >
                  <div className={styles.profileFieldContent}>
                    <div className={styles.profileFieldIcon}>
                      {gender === 'Мужской' ? (
                        <Mars size={20} />
                      ) : (
                        <Venus size={20} />
                      )}
                    </div>
                    <div className={styles.profileFieldInfo}>
                      <span className={styles.profileFieldLabel}>Пол</span>
                      <span className={styles.profileFieldValue}>
                        {gender === 'Мужской'
                          ? 'Мужской'
                          : gender === 'Женский'
                            ? 'Женский'
                            : 'Не указан'}
                      </span>
                    </div>
                    <div className={styles.profileFieldAction}>
                      <Pencil className={styles.pencilIcon} size={16} />
                    </div>
                  </div>
                </SelectTrigger>
                <SelectContent
                  className={styles.genderSelectContent}
                  position="popper"
                  sideOffset={4}
                >
                  <SelectItem value="Мужской">Мужской</SelectItem>
                  <SelectItem value="Женский">Женский</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>
        </div>
      </PageFrame>
    </>
  );
}
