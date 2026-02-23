import { useState, type ChangeEvent, useRef } from 'react';
import { Button, Input, Label, Avatar, AvatarFallback, AvatarImage } from '../../../shared/ui';
import { X, Camera } from 'lucide-react';
import styles from './ChangeName.module.css';
import { cn } from '../../../shared/lib/utils';

interface ChangeNameProps {
  isVisible: boolean;
  onClose?: () => void;
  onSave?: (data: { 
    firstName: string; 
    lastName: string;
    avatar?: File | null;
  }) => void;
  currentFirstName?: string;
  currentLastName?: string;
  currentAvatar?: string | null;
}

export default function ChangeName({ 
  isVisible, 
  onClose, 
  onSave,
  currentFirstName = '',
  currentLastName = '',
  currentAvatar = null
}: ChangeNameProps) {
  const [firstName, setFirstName] = useState<string>(currentFirstName);
  const [lastName, setLastName] = useState<string>(currentLastName);
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(currentAvatar);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setAvatarFile(file);
      
      const reader = new FileReader();
      reader.onloadend = () => {
        setAvatarPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleChangeClick = () => {
    fileInputRef.current?.click();
  };

  const handleSave = (): void => {
    onSave?.({
      firstName,
      lastName,
      avatar: avatarFile
    });
  };

  const handleClose = () => {
    setFirstName(currentFirstName);
    setLastName(currentLastName);
    setAvatarFile(null);
    setAvatarPreview(currentAvatar);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    onClose?.();
  };

  return (
    <div className={cn(styles.container, isVisible ? styles.formVisible : '')}>
      <div className={styles.titleHeader}>
        {onClose && (
          <button 
            className={styles.closeButton}
            onClick={handleClose}
            type="button"
            aria-label="Закрыть"
          >
            <X className="h-4 w-4" />
          </button>
        )}
        <h2 className={styles.title}>Личные данные</h2>	
      </div>

      <div className={styles.header}>
        <div className={styles.avatarContainer}>
          <Avatar className={styles.avatar}>
            <AvatarImage src={avatarPreview || ''} />
            <AvatarFallback className={styles.avatarFallback}>
              {firstName?.[0] || lastName?.[0] || 'U'}
            </AvatarFallback>
          </Avatar>
        </div>
        
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        
        <Button 
          variant="secondary" 
          className={styles.changeButton}
          onClick={handleChangeClick}
          type="button"
        >
          <Camera size={16} style={{ marginRight: '8px' }} />
          {avatarPreview ? 'Изменить фото' : 'Загрузить фото'}
        </Button>
      </div>

      <div className={styles.form}>
        <div className={styles.formGroup}>
          <Label htmlFor="firstName" className={styles.label}>
            Имя
          </Label>
          <Input
            id="firstName"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            className={styles.input}
            placeholder="Введите имя"
          />
        </div>

        <div className={styles.formGroup}>
          <Label htmlFor="lastName" className={styles.label}>
            Фамилия
          </Label>
          <Input
            id="lastName"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            className={styles.input}
            placeholder="Введите фамилию"
          />
        </div>
      </div>

      <Button 
        className={styles.saveButton}
        onClick={handleSave}
        type="button"
      >
        Сохранить
      </Button>
    </div>
  );
}