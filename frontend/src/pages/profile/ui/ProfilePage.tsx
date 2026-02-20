import { Card, CardContent, Button } from '../../../shared/ui'
import { 
  User, 
  Mail, 
  Phone, 
  Calendar, 
  Venus, 
  Pencil, 
  Plus 
} from 'lucide-react'
import styles from './ProfilePage.module.css'

interface ProfileFieldProps {
  icon: React.ReactNode
  label: string
  value: string | null
  actionButton: React.ReactNode
}

const ProfileField = ({ icon, label, value, actionButton }: ProfileFieldProps) => {
  return (
    <div className={styles.profileField}>
      <div className={styles.profileFieldContent}>
        <div className={styles.profileFieldIcon}>
          {icon}
        </div>
        <div className={styles.profileFieldInfo}>
          <span className={styles.profileFieldLabel}>{label}</span>
          <span className={styles.profileFieldValue}>{value || '-'}</span>
        </div>
      </div>
      <div className={styles.profileFieldAction}>
        {actionButton}
      </div>
    </div>
  )
}

export default function ProfilePage() {
  return (
    <div className={styles.profilePage}>

      <div className={styles.wrapper}>
				<h1 className={styles.profilePageTitle}>Личный кабинет</h1>
				<Card className={styles.profilePageCard}>
        <CardContent className={styles.profilePageContent}>
          {/* User Info Section */}
          <div className={styles.profileSection}>
            <ProfileField
              icon={<User className={styles.icon} size={20} />}
              label="Имя и Фамилия"
              value="Василий Пупкин"
              actionButton={
                <Button variant="ghost" size="icon" className={styles.profileFieldButton}>
                  <Pencil size={16} />
                </Button>
              }
            />
          </div>

          {/* Contacts Section */}
          <div className={styles.profileSection}>
            <h2 className={styles.profileSectionTitle}>Контакты</h2>
            
            <ProfileField
              icon={<Mail className={styles.icon} size={20} />}
              label="Почта"
              value="profession.ru@yandex.ru"
              actionButton={
                <Button variant="ghost" size="icon" className={styles.profileFieldButton}>
                  <Pencil size={16} />
                </Button>
              }
            />

            <ProfileField
              icon={<Phone className={styles.icon} size={20} />}
              label="Телефон"
              value={null}
              actionButton={
                <Button variant="ghost" size="icon" className={styles.profileFieldButton}>
                  <Plus size={16} />
                </Button>
              }
            />
          </div>

          {/* Additional Data Section */}
          <div className={styles.profileSection}>
            <h2 className={styles.profileSectionTitle}>Дополнительные данные</h2>
            
            <ProfileField
              icon={<Calendar className={styles.icon} size={20} />}
              label="Дата рождения"
              value={null}
              actionButton={
                <Button variant="ghost" size="icon" className={styles.profileFieldButton}>
                  <Plus size={16} />
                </Button>
              }
            />

            <ProfileField
              icon={<Venus className={styles.icon} size={20} />}
              label="Пол"
              value="Женский"
              actionButton={
                <Button variant="ghost" size="icon" className={styles.profileFieldButton}>
                  <Pencil size={16} />
                </Button>
              }
            />
          </div>
        </CardContent>
      </Card>
			</div>
    </div>
  )
}