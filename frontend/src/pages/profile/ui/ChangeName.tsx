import { useState, useEffect, type ChangeEvent, useRef, useCallback } from 'react';
import {
  Button,
  Input,
  Label,
  Avatar,
  AvatarFallback,
  AvatarImage,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Spinner,
} from '@shared/ui';
import { Camera } from 'lucide-react';
import styles from './ChangeName.module.css';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  changeNameSchema,
  type ChangeNameFormValues,
} from '@shared/utils/formSchemas';

interface ChangeNameProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (data: {
    firstName: string;
    lastName: string;
    avatar?: File | null;
  }) => Promise<void>;
  currentFirstName?: string;
  currentLastName?: string;
  currentAvatar?: string | null;
}

export default function ChangeName({
  open,
  onOpenChange,
  onSave,
  currentFirstName = '',
  currentLastName = '',
  currentAvatar = null,
}: ChangeNameProps) {
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(currentAvatar);
  const [savePending, setSavePending] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const formId = 'change-name-form';
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ChangeNameFormValues>({
    resolver: zodResolver(changeNameSchema),
    defaultValues: { firstName: currentFirstName, lastName: currentLastName },
  });

  const cleanup = useCallback(() => {
    reset({ firstName: currentFirstName, lastName: currentLastName });
    setAvatarFile(null);
    setAvatarPreview(currentAvatar);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [currentAvatar, currentFirstName, currentLastName, reset]);

  useEffect(() => {
    if (!open) return;
    reset({ firstName: currentFirstName, lastName: currentLastName });
    setAvatarFile(null);
    setAvatarPreview(currentAvatar);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [open, currentFirstName, currentLastName, currentAvatar, reset]);

  const handleDialogOpenChange = (next: boolean) => {
    if (!next) cleanup();
    onOpenChange(next);
  };

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

  const onSubmit = handleSubmit(async ({ firstName, lastName }) => {
    setSavePending(true);
    try {
      await onSave({
        firstName,
        lastName,
        avatar: avatarFile,
      });
      handleDialogOpenChange(false);
    } catch {
      return;
    } finally {
      setSavePending(false);
    }
  });

  return (
    <Dialog open={open} onOpenChange={handleDialogOpenChange}>
      <DialogContent className={styles.dialogContent}>
        <DialogHeader>
          <DialogTitle>Личные данные</DialogTitle>
          <DialogDescription className="sr-only">
            Измените имя, фамилию и при необходимости фото профиля
          </DialogDescription>
        </DialogHeader>

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
            disabled={savePending}
          >
            <Camera size={16} style={{ marginRight: '8px' }} />
            {avatarPreview ? 'Изменить фото' : 'Загрузить фото'}
          </Button>
        </div>

        <form id={formId} className={styles.form} onSubmit={onSubmit}>
          <div className={styles.formGroup}>
            <Label htmlFor="firstName" className={styles.label}>
              Имя
            </Label>
            <Input
              id="firstName"
              className={styles.input}
              placeholder="Введите имя"
              disabled={savePending}
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
              disabled={savePending}
              {...register('lastName')}
            />
            {errors.lastName?.message ? (
              <p className={styles.errorText}>{errors.lastName.message}</p>
            ) : null}
          </div>
        </form>

        <DialogFooter className={styles.dialogFooter}>
          <Button
            type="button"
            variant="outline"
            disabled={savePending}
            onClick={() => handleDialogOpenChange(false)}
          >
            Отмена
          </Button>
          <Button
            type="submit"
            form={formId}
            className={styles.saveButton}
            disabled={savePending}
          >
            {savePending ? <Spinner /> : 'Сохранить'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
