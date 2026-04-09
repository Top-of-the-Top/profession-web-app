import { useState, useEffect, type ChangeEvent, useRef } from 'react';
import { Button, Input, Label, Avatar, AvatarFallback, AvatarImage } from '@shared/ui';
import { X, Camera } from 'lucide-react';
import styles from './ChangeName.module.css';
import { cn } from '@shared/lib/utils';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  changeNameSchema,
  type ChangeNameFormValues,
} from '@shared/utils/formSchemas';

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
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(currentAvatar);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ChangeNameFormValues>({
    resolver: zodResolver(changeNameSchema),
    defaultValues: { firstName: currentFirstName, lastName: currentLastName },
  });

  useEffect(() => {
    if (isVisible) {
      reset({ firstName: currentFirstName, lastName: currentLastName });
      if (!avatarFile) {
        setAvatarPreview(currentAvatar);
      }
    }
  }, [isVisible, currentFirstName, currentLastName, currentAvatar, reset, avatarFile]);

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

  const handleSave = ({ firstName, lastName }: ChangeNameFormValues): void => {
    onSave?.({
      firstName,
      lastName,
      avatar: avatarFile
    });
  };

  const handleClose = () => {
    reset({ firstName: currentFirstName, lastName: currentLastName });
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
            <AvatarImage
              src={avatarPreview || ''}
              className={styles.avatarImage}
            />
            <AvatarFallback className={styles.avatarFallback}>
              {currentFirstName?.[0] || currentLastName?.[0] || 'U'}
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

      <form className={styles.form} onSubmit={handleSubmit(handleSave)}>
        <div className={styles.formGroup}>
          <Label htmlFor="firstName" className={styles.label}>
            Имя
          </Label>
          <Input
            id="firstName"
            className={styles.input}
            placeholder="Введите имя"
            {...register('firstName')}
          />
          {errors.firstName?.message ? (
            <p className={styles.errorText}>{errors.firstName.message}</p>
          ) : null}
        </div>

        <div className={styles.formGroup}>
          <Label htmlFor="lastName" className={styles.label}>
            Фамилия
          </Label>
          <Input
            id="lastName"
            className={styles.input}
            placeholder="Введите фамилию"
            {...register('lastName')}
          />
          {errors.lastName?.message ? (
            <p className={styles.errorText}>{errors.lastName.message}</p>
          ) : null}
        </div>
        <Button 
          className={styles.saveButton}
          type="submit"
        >
          Сохранить
        </Button>
      </form>

    </div>
  );
}