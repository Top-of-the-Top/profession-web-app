'use client';

import { useState, type ChangeEvent } from 'react';
import { Button, Input, Label, Avatar, AvatarFallback, AvatarImage } from '../../../shared/ui';
import { X } from 'lucide-react';
import styles from './ChangeName.module.css';
import { cn } from '../../../shared/lib/utils';

interface ChangeNameProps {
	isVisible: boolean,
  onClose?: () => void;
  onSave?: (data: { firstName: string; lastName: string }) => void;
}

interface FormData {
	avatar?: File | string | null;
  firstName: string;
  lastName: string;
}

export default function ChangeName({ isVisible, onClose, onSave }: ChangeNameProps) {
  const [firstName, setFirstName] = useState<string>('');
  const [lastName, setLastName] = useState<string>('');

  const handleSave = (): void => {
    const formData: FormData = { firstName, lastName };
    onSave?.(formData);
  };

  const handleChange = (): void => {
    console.log('Change clicked');
  };

  const handleFirstNameChange = (e: ChangeEvent<HTMLInputElement>): void => {
    setFirstName(e.target.value);
  };

  const handleLastNameChange = (e: ChangeEvent<HTMLInputElement>): void => {
    setLastName(e.target.value);
  };

  return (
    <div className={cn(styles.container, isVisible ? styles.formVisible : '')}>
      {/* Кнопка закрытия */}
      <div className={styles.titleHeader}>
				{onClose && (
        <button 
          className={styles.closeButton}
          onClick={onClose}
          type="button"
          aria-label="Закрыть"
        >
          <X className="h-4 w-4" />
        </button>
      )}

      <h2 className={styles.title}>
        Личные данные
      </h2>	
			</div>

      <div className={styles.header}>
        <Avatar className={styles.avatar} >

					<AvatarImage src=''>

					</AvatarImage>
          <AvatarFallback className={styles.avatarFallback}>
            U
          </AvatarFallback>
        </Avatar>
        <Button 
          variant="secondary" 
          className={styles.changeButton}
          onClick={handleChange}
          type="button"
        >
          Изменить
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
            onChange={handleFirstNameChange}
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
            onChange={handleLastNameChange}
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