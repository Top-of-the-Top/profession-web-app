import { useEffect, useRef } from 'react';
import type { OtpValue } from '@components/OtpInput';
import { VerificationCodeInput } from './VerificationCodeInput';

type AutoSubmitVerificationCodeProps = {
  value: OtpValue;
  onChange: (next: OtpValue) => void;
  onComplete: (code: string) => Promise<void> | void;
  disabled?: boolean;
  label?: string | null;
  hint?: string;
  error?: string;
  className?: string;
  labelClassName?: string;
  otpClassName?: string;
  hintClassName?: string;
  errorClassName?: string;
};

export function AutoSubmitVerificationCode({
  value,
  onChange,
  onComplete,
  disabled = false,
  label = null,
  hint,
  error,
  className,
  labelClassName,
  otpClassName,
  hintClassName,
  errorClassName,
}: AutoSubmitVerificationCodeProps) {
  const lastSubmittedRef = useRef<string | null>(null);

  useEffect(() => {
    const code = value.join('');
    const complete = value.every((cell) => cell !== '') && code.length === value.length;
    if (!complete) {
      lastSubmittedRef.current = null;
      return;
    }
    if (disabled) return;
    if (lastSubmittedRef.current === code) return;
    lastSubmittedRef.current = code;
    void onComplete(code);
  }, [value, disabled, onComplete]);

  return (
    <VerificationCodeInput
      value={value}
      onChange={onChange}
      disabled={disabled}
      label={label}
      hint={hint}
      error={error}
      className={className}
      labelClassName={labelClassName}
      otpClassName={otpClassName}
      hintClassName={hintClassName}
      errorClassName={errorClassName}
    />
  );
}
