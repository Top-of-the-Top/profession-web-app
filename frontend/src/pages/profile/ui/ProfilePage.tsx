import {
  Card,
  CardContent,
  Button,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
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
import { useState } from 'react';
import { cn } from '../../../shared/lib/utils';
import ChangeName from './ChangeName';
import ConfirmContact from './ConfirmContact';

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
}: ProfileFieldProps) => {
  return (
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
};

export default function ProfilePage() {
  const [isChangeNameMenuOpen, setChangeMenuOpen] = useState(false);
  const [isEmailMenuOpen, setIsEmailMenuOpen] = useState(false);
  const [isPhoneMenuOpen, setIsPhoneMenuOpen] = useState(false);
  const [gender, setGender] = useState<string | null>(null);

  const toggleNameMenu = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    setChangeMenuOpen((prev) => !prev);
  };

  const toggleEmailMenu = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    setIsEmailMenuOpen((prev) => !prev);
  };

  const togglePhoneMenu = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    setIsPhoneMenuOpen((prev) => !prev);
  };

  const closeAllMenus = () => {
    setChangeMenuOpen(false);
    setIsEmailMenuOpen(false);
    setIsPhoneMenuOpen(false);
  };

  const anyMenuOpen =
    isChangeNameMenuOpen || isEmailMenuOpen || isPhoneMenuOpen;

  return (
    <div className={styles.profilePage}>
      {anyMenuOpen && (
        <div className={styles.overlay} onClick={closeAllMenus} />
      )}

      <ChangeName isVisible={isChangeNameMenuOpen} onClose={toggleNameMenu} />
      <ConfirmContact
        type="email"
        isVisible={isEmailMenuOpen}
        onClose={toggleEmailMenu}
      />
      <ConfirmContact
        type="phone"
        isVisible={isPhoneMenuOpen}
        onClose={togglePhoneMenu}
      />

      <div className={styles.wrapper}>
        <h1 className={styles.profilePageTitle}>Личный кабинет</h1>

        <Card className={styles.profilePageCard}>
          <CardContent className={styles.profilePageContent}>
            <div className={styles.profileSection}>
              <ProfileField
                icon={<User size={20} />}
                label="Имя и Фамилия"
                value="Василий Пупкин"
                onClick={toggleNameMenu}
                actionButton={
                  <Button
                    variant="ghost"
                    size="icon"
                    className={styles.profileFieldButton}
                    onClick={toggleNameMenu}
                  >
                    <Pencil size={16} />
                  </Button>
                }
              />
            </div>

            <div className={styles.profileSection}>
              <h2 className={styles.profileSectionTitle}>Контакты</h2>

              <ProfileField
                icon={<Mail size={20} />}
                label="Почта"
                value="profession.ru@yandex.ru"
                onClick={toggleEmailMenu}
                actionButton={
                  <Button
                    variant="ghost"
                    size="icon"
                    className={styles.profileFieldButton}
                    onClick={toggleEmailMenu}
                  >
                    <Pencil size={16} />
                  </Button>
                }
              />

              <ProfileField
                icon={<Phone size={20} />}
                label="Телефон"
                value={null}
                onClick={togglePhoneMenu}
                actionButton={
                  <Button
                    variant="ghost"
                    size="icon"
                    className={styles.profileFieldButton}
                    onClick={togglePhoneMenu}
                  >
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
                value={null}
                actionButton={
                  <Button
                    variant="ghost"
                    size="icon"
                    className={styles.profileFieldButton}
                  >
                    <Plus size={16} />
                  </Button>
                }
              />

              <Select value={gender ?? ''} onValueChange={setGender}>
                <SelectTrigger
                  className={cn(styles.profileField, styles.genderTrigger)}
                >
                  <div className={styles.profileFieldContent}>
                    <div className={styles.profileFieldIcon}>
                      {gender === 'male' ? (
                        <Mars size={20} />
                      ) : (
                        <Venus size={20} />
                      )}
                    </div>

                    <div className={styles.profileFieldInfo}>
                      <span className={styles.profileFieldLabel}>Пол</span>
                      <span className={styles.profileFieldValue}>
                        {gender === 'male'
                          ? 'Мужской'
                          : gender === 'female'
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
                  <SelectItem value="male">Мужской</SelectItem>
                  <SelectItem value="female">Женский</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
