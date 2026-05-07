import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { AutoSubmitVerificationCode, Button, Input, Label } from '@shared/ui';
import { X, AlertCircle } from 'lucide-react';
import styles from './ConfirmContact.module.css';
import { cn } from '@shared/lib/utils';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { EMPTY_OTP, type OtpValue } from '@components/OtpInput';
import {
  confirmEmailContactSchema,
  confirmPhoneContactSchema,
  type ConfirmContactInputFormValues,
  oneTimeCodeSchema,
} from '@shared/utils/formSchemas';

type FormStep = 'input' | 'code';

interface ConfirmContactProps {
  type: 'email' | 'phone';
  isVisible: boolean;
  onClose?: () => void;
  initialContact?: string | null;
  /** PATCH профиля с новым контактом; после успеха показывается шаг ввода кода. */
  onRequestChange: (contact: string) => Promise<void>;
  /** Подтверждение кода из письма или SMS. */
  onVerify: (code: string) => Promise<void>;
}

export default function ConfirmContact({
  type,
  isVisible,
  onClose,
  initialContact = null,
  onRequestChange,
  onVerify,
}: ConfirmContactProps) {
  const [step, setStep] = useState<FormStep>('input');
  const [isLoading, setIsLoading] = useState(false);
  const [otp, setOtp] = useState<OtpValue>(() => [...EMPTY_OTP]);
  const [codeError, setCodeError] = useState<string | null>(null);
  const inputSchema =
    type === 'email' ? confirmEmailContactSchema : confirmPhoneContactSchema;
  const {
    register: registerInput,
    handleSubmit: handleInputSubmit,
    reset: resetInput,
    setError: setInputError,
    clearErrors: clearInputErrors,
    watch: watchInput,
    formState: { errors: inputErrors },
  } = useForm<ConfirmContactInputFormValues>({
    resolver: zodResolver(inputSchema),
    defaultValues: { contact: '' },
  });
  const contactField = registerInput('contact');
  const contact = watchInput('contact');

  useEffect(() => {
    if (!isVisible) return;
    setStep('input');
    resetInput({ contact: initialContact ?? '' });
    setOtp([...EMPTY_OTP]);
    setCodeError(null);
    setIsLoading(false);
  }, [isVisible, initialContact, resetInput]);

  const title =
    type === 'email' ? 'Подтверждение почты' : 'Подтверждение номера';

  const descriptions = {
    input: `Введите ${type === 'email' ? 'новый адрес почты' : 'новый номер телефона'}`,
    code: `Код отправлен в ${type === 'email' ? 'письмо' : 'SMS'}`,
  };

  const handleContinue = async ({
    contact,
  }: ConfirmContactInputFormValues): Promise<void> => {
    setIsLoading(true);
    try {
      await onRequestChange(type === 'email' ? contact.trim() : contact);
      setStep('code');
    } catch {
      setInputError('contact', { message: 'Не удалось отправить код подтверждения' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmCode = async (code: string): Promise<void> => {
    const parsed = oneTimeCodeSchema.safeParse(code);
    if (!parsed.success) {
      setCodeError(parsed.error.issues[0]?.message ?? 'Введите 6 цифр кода');
      return;
    }
    setIsLoading(true);
    setCodeError(null);
    try {
      await onVerify(parsed.data);
    } catch {
      return;
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = (): void => {
    setStep('input');
    resetInput({ contact: '' });
    setOtp([...EMPTY_OTP]);
    setCodeError(null);
    setIsLoading(false);
    onClose?.();
  };

  const handleBack = (): void => {
    setStep('input');
    setOtp([...EMPTY_OTP]);
    setCodeError(null);
  };

  if (!isVisible) return null;

  return createPortal(
    <>
      <div className={styles.overlay} onClick={handleClose} />
    <div className={styles.container}>
      <div className={styles.titleHeader}>
        <h2 className={styles.title}>{title}</h2>
        <button
          className={styles.closeButton}
          onClick={handleClose}
          type="button"
          aria-label="Закрыть"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <p className={styles.description}>{descriptions[step]}</p>

      {step === 'input' && (
        <form className={styles.form} onSubmit={handleInputSubmit(handleContinue)}>
          <div className={styles.formGroup}>
            <Label htmlFor="contact" className={styles.label}>
              {type === 'email' ? 'Адрес почты' : 'Номер телефона'}
            </Label>
            <Input
              id="contact"
              value={contact}
              type={type === 'email' ? 'email' : 'tel'}
              inputMode={type === 'email' ? 'email' : 'numeric'}
              pattern={type === 'email' ? undefined : '[0-9]*'}
              maxLength={type === 'email' ? undefined : 12}
              name={contactField.name}
              ref={contactField.ref}
              onBlur={contactField.onBlur}
              onFocus={(event) => {
                event.currentTarget.select();
              }}
              onChange={(e) => {
                if (type === 'phone') {
                  e.target.value = e.target.value.replace(/\D/g, '').slice(0, 11);
                }
                contactField.onChange(e);
                clearInputErrors('contact');
              }}
              className={cn(styles.input, inputErrors.contact && styles.inputError)}
              placeholder={
                type === 'email' ? 'example@mail.ru' : '+7 (xxx) xxx-xx-xx'
              }
              disabled={isLoading}
            />
            {inputErrors.contact?.message && (
              <div className={styles.errorText}>
                <AlertCircle className="h-4 w-4" />
                {inputErrors.contact.message}
              </div>
            )}
          </div>

          <Button
            className={styles.saveButton}
            type="submit"
            disabled={isLoading}
          >
            {isLoading ? 'Отправка...' : 'Продолжить'}
          </Button>
        </form>
      )}

      {step === 'code' && (
        <div className={styles.form}>
          <div className={styles.formGroup}>
            <AutoSubmitVerificationCode
              value={otp}
              onChange={(next) => {
                setOtp(next);
                if (codeError) setCodeError(null);
              }}
              onComplete={handleConfirmCode}
              disabled={isLoading}
              label={null}
              labelClassName={styles.label}
              error={codeError ?? undefined}
              errorClassName={styles.errorText}
            />
          </div>

          <div className={styles.buttonGroup}>
            <Button
              variant="outline"
              className={styles.backButton}
              onClick={handleBack}
              type="button"
              disabled={isLoading}
            >
              Назад
            </Button>
          </div>
        </div>
      )}
    </div>
    </>,
    document.body
  );
}
