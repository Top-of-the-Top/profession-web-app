import { useEffect, useState } from 'react';
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
} from '../../../shared/ui';
import { Mail, Phone, Calendar, Pencil, Plus, Venus, Mars } from 'lucide-react';
import styles from './ProfilePage.module.css';
import { cn } from '../../../shared/lib/utils';
import ChangeName from './ChangeName';
import ConfirmContact from './ConfirmContact';
import {
  profileApi,
  type ProfileData,
  type UpdateProfilePayload,
} from '../../../shared/api/profileApi';
import { useUserStore } from '../../../entities/user/model/userStore';
import { parseApiError } from '../../../shared/lib/api/parseApiError';
import { messageForApiFailure, notifyError } from '../../../shared/lib/sileo/notify';

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
  const user = useUserStore((state) => state.user);
  const isLoading = useUserStore((state) => state.isLoading);
  const setUser = useUserStore((state) => state.setUser);
  const [profile, setProfile] = useState<ProfileData | null>(user);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);

  const [isChangeNameMenuOpen, setChangeMenuOpen] = useState(false);
  const [isEmailMenuOpen, setEmailMenuOpen] = useState(false);
  const [isPhoneMenuOpen, setPhoneMenuOpen] = useState(false);
  const [gender, setGender] = useState<string | null>(null);

  useEffect(() => {
    setProfile(user);
    setGender(user?.gender || null);
    setAvatarUrl(user?.avatar || null);
  }, [user]);

  // --- Изменение пола ---
  const updateGender = async (value: string) => {
    const previous = gender;
    setGender(value);
    try {
      await profileApi.updateProfile({ gender: value });
      setProfile((prev) => {
        const next = prev ? { ...prev, gender: value } : prev;
        if (next) {
          setUser(next);
        }
        return next;
      });
    } catch (err) {
      notifyProfileSaveError(err);
      setGender(previous);
    }
  };

  const toggleNameMenu = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    setChangeMenuOpen((prev) => !prev);
  };
  const toggleEmailMenu = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    setEmailMenuOpen((prev) => !prev);
  };
  const togglePhoneMenu = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    setPhoneMenuOpen((prev) => !prev);
  };
  const closeAllMenus = () => {
    setChangeMenuOpen(false);
    setEmailMenuOpen(false);
    setPhoneMenuOpen(false);
  };
  const anyMenuOpen =
    isChangeNameMenuOpen || isEmailMenuOpen || isPhoneMenuOpen;

  if (isLoading && !profile) return <div>Загрузка профиля...</div>;
  if (!profile) return <div>Профиль недоступен</div>;

  const handleNameSave = async (data: {
    firstName: string;
    lastName: string;
    avatar?: File | null;
  }) => {
    try {
      const updateData: UpdateProfilePayload = {
        first_name: data.firstName,
        last_name: data.lastName,
      };

      if (data.avatar instanceof File) {
        updateData.avatar = data.avatar;
        const tempUrl = URL.createObjectURL(data.avatar);
        setAvatarUrl(tempUrl);
      }

      await profileApi.updateProfile(updateData);

      setProfile((prev) => {
        const next = prev
          ? {
              ...prev,
              first_name: data.firstName,
              last_name: data.lastName,
            }
          : prev;
        if (next) {
          setUser(next);
        }
        return next;
      });

      setChangeMenuOpen(false);
    } catch (err) {
      notifyProfileSaveError(err);
      setAvatarUrl(profile.avatar);
    }
  };

  const handleContactSave = async (
    { contact }: { contact: string },
    type: 'email' | 'phone'
  ) => {
    try {
      if (type === 'email') {
        await profileApi.updateProfile({ email: contact });
        setProfile((prev) => {
          const next = prev ? { ...prev, email: contact } : prev;
          if (next) {
            setUser(next);
          }
          return next;
        });
        setEmailMenuOpen(false);
      } else {
        await profileApi.updateProfile({ phone_number: contact });
        setProfile((prev) => {
          const next = prev ? { ...prev, phone_number: contact } : prev;
          if (next) {
            setUser(next);
          }
          return next;
        });
        setPhoneMenuOpen(false);
      }
    } catch (err) {
      notifyProfileSaveError(err);
    }
  };

  const getInitials = () => {
    const first = profile.first_name?.[0] || '';
    const last = profile.last_name?.[0] || '';
    return (first + last).toUpperCase() || 'U';
  };

  return (
    <div className={styles.profilePage}>
      {anyMenuOpen && (
        <div className={styles.overlay} onClick={closeAllMenus} />
      )}

      <ChangeName
        isVisible={isChangeNameMenuOpen}
        onClose={toggleNameMenu}
        onSave={handleNameSave}
        currentFirstName={profile.first_name || ''}
        currentLastName={profile.last_name || ''}
        currentAvatar={avatarUrl}
      />
      <ConfirmContact
        type="email"
        isVisible={isEmailMenuOpen}
        onClose={toggleEmailMenu}
        onSave={(data) => handleContactSave(data, 'email')}
      />
      <ConfirmContact
        type="phone"
        isVisible={isPhoneMenuOpen}
        onClose={togglePhoneMenu}
        onSave={(data) => handleContactSave(data, 'phone')}
      />

      <div className={styles.wrapper}>
        <h1 className={styles.profilePageTitle}>Личный кабинет</h1>
        <Card className={styles.profilePageCard}>
          <CardContent className={styles.profilePageContent}>
            <div className={styles.profileSection}>
              <div className={styles.profileField} onClick={toggleNameMenu}>
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
                  <Button variant="ghost" size="icon" onClick={toggleNameMenu}>
                    <Pencil size={16} />
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
                  <Button variant="ghost" size="icon" onClick={toggleEmailMenu}>
                    <Pencil size={16} />
                  </Button>
                }
              />
              <ProfileField
                icon={<Phone size={20} />}
                label="Телефон"
                value={profile.phone_number}
                onClick={togglePhoneMenu}
                actionButton={
                  <Button variant="ghost" size="icon" onClick={togglePhoneMenu}>
                    <Plus size={16} />
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
                  <Button variant="ghost" size="icon">
                    <Plus size={16} />
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
                      <Pencil size={16} />
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
    </div>
  );
}
