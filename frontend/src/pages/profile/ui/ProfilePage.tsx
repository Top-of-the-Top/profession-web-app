import { useEffect, useState } from 'react';
import {
  Card,
  CardContent,
  Button,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
} from '../../../shared/ui';
import {
  User,
  Mail,
  Phone,
  Calendar,
  Pencil,
  Plus,
  Venus,
  Mars,
} from 'lucide-react';
import styles from './ProfilePage.module.css';
import { cn } from '../../../shared/lib/utils';
import ChangeName from './ChangeName';
import ConfirmContact from './ConfirmContact';
import { profileApi, type ProfileData, type UpdateProfilePayload } from '../../../shared/api/profileApi';

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
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [isChangeNameMenuOpen, setChangeMenuOpen] = useState(false);
  const [isEmailMenuOpen, setEmailMenuOpen] = useState(false);
  const [isPhoneMenuOpen, setPhoneMenuOpen] = useState(false);
  const [gender, setGender] = useState<string | null>(null);

  // --- Загрузка профиля ---
  useEffect(() => {
    profileApi
      .getProfile()
      .then((data) => {
        setProfile(data);
        setGender(data.gender === 'Мужской' ? 'Мужской' : 'Женский');
      })
      .catch((err) => {
        console.error(err);
        setError('Не удалось загрузить профиль');
      })
      .finally(() => setLoading(false));
  }, []);

  // --- Изменение пола ---
  const updateGender = async (value: string) => {
    setGender(value);
    try {
      await profileApi.updateProfile({ gender: value });
      setProfile((prev) => (prev ? { ...prev, gender: value } : prev));
    } catch (err) {
      console.error('Ошибка обновления пола', err);
    }
  };

  // --- Меню модалок ---
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

  if (loading) return <div>Загрузка профиля...</div>;
  if (error) return <div>{error}</div>;
  if (!profile) return <div>Профиль недоступен</div>;

  // --- Обработчики сохранения ---
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
    
    // Если есть новый файл аватара, добавляем его
    if (data.avatar instanceof File) {
      updateData.avatar = data.avatar;
    }
    // Если avatar === null (удален), отправляем null
    else if (data.avatar === null) {
      updateData.avatar = null;
    }
    
    await profileApi.updateProfile(updateData);
    
    setProfile((prev) => prev ? { 
      ...prev, 
      first_name: data.firstName, 
      last_name: data.lastName,
      // Если аватар обновлен, нужно обновить и его
      ...(data.avatar && { avatar: URL.createObjectURL(data.avatar) })
    } : prev);
    
    setChangeMenuOpen(false);
  } catch (err) {
    console.error('Ошибка обновления имени', err);
  }
};

  const handleContactSave = async (
    { contact }: { contact: string },
    type: 'email' | 'phone'
  ) => {
    try {
      if (type === 'email') {
        await profileApi.updateProfile({ email: contact });
        setProfile((prev) => (prev ? { ...prev, email: contact } : prev));
        setEmailMenuOpen(false);
      } else {
        await profileApi.updateProfile({ phone_number: contact });
        setProfile((prev) =>
          prev ? { ...prev, phone_number: contact } : prev
        );
        setPhoneMenuOpen(false);
      }
    } catch (err) {
      console.error(`Ошибка обновления ${type}`, err);
    }
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
        currentAvatar={profile.avatar}
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
            {/* Имя и Фамилия */}
            <div className={styles.profileSection}>
              <ProfileField
                icon={<User size={20} />}
                label="Имя и Фамилия"
                value={`${profile.first_name ?? ''} ${profile.last_name ?? ''}`}
                onClick={toggleNameMenu}
                actionButton={
                  <Button variant="ghost" size="icon" onClick={toggleNameMenu}>
                    <Pencil size={16} />
                  </Button>
                }
              />
            </div>

            {/* Контакты */}
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

            {/* Дополнительно */}
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

              {/* Пол */}
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
