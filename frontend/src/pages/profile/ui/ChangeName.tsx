import { useState, useEffect, type ChangeEvent, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import {
  Button,
  Input,
  Label,
  Avatar,
  AvatarFallback,
  AvatarImage,
  Spinner,
} from '@shared/ui';
import { X } from 'lucide-react';
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

  const handleDeleteAvatar = () => {
    setAvatarFile(null);
    setAvatarPreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
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

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !savePending) {
        handleDialogOpenChange(false);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, savePending, handleDialogOpenChange]);

  if (!open) return null;

  return createPortal(
    <>
      <div
        className={styles.overlay}
        onClick={() => {
          if (!savePending) handleDialogOpenChange(false);
        }}
      />
      <div className={styles.container} role="dialog" aria-modal="true">
        <div className={styles.titleHeader}>
          <h2 className={styles.title}>Личные данные</h2>
          <button
            className={styles.closeButton}
            onClick={() => handleDialogOpenChange(false)}
            type="button"
            aria-label="Закрыть"
            disabled={savePending}
          >
            <X size={18} />
          </button>
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
            disabled={savePending}
          >
            Изменить
          </Button>
          <Button
            variant="secondary"
            className={styles.deleteButton}
            onClick={handleDeleteAvatar}
            type="button"
            disabled={savePending || (!avatarPreview && !avatarFile)}
          >
            Удалить
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
              disabled={savePending}
              {...register('lastName')}
            />
            {errors.lastName?.message ? (
              <p className={styles.errorText}>{errors.lastName.message}</p>
            ) : null}
          </div>
        </form>

        <div className={styles.dialogFooter}>
          <Button
            type="submit"
            form={formId}
            className={styles.saveButton}
            disabled={savePending}
          >
            {savePending ? <Spinner /> : 'Сохранить'}
          </Button>
        </div>
      </div>
    </>
    ,
    document.body
  );
}
