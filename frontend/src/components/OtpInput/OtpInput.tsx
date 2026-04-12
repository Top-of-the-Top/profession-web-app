import { useLayoutEffect, useRef } from 'react';
import { cn } from '@shared/lib/utils';
import styles from './OtpInput.module.css';

export const OTP_LENGTH = 6;

export type OtpValue = [string, string, string, string, string, string];

export const EMPTY_OTP: OtpValue = ['', '', '', '', '', ''];

export type OtpInputProps = {
  value: OtpValue;
  onChange: (next: OtpValue) => void;
  disabled?: boolean;
  className?: string;
  groupAriaLabel?: string;
};

export function OtpInput({
  value,
  onChange,
  disabled = false,
  className,
  groupAriaLabel = 'Код из 6 цифр',
}: OtpInputProps) {
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  useLayoutEffect(() => {
    if (!value.every((c) => c === '')) return;
    const id = requestAnimationFrame(() => inputRefs.current[0]?.focus());
    return () => cancelAnimationFrame(id);
  }, [value.join('')]);

  const focusAt = (index: number) => {
    requestAnimationFrame(() =>
      inputRefs.current[Math.min(Math.max(index, 0), OTP_LENGTH - 1)]?.focus(),
    );
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const raw = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, OTP_LENGTH);
    if (!raw) return;
    const next: OtpValue = [...EMPTY_OTP];
    raw.split('').forEach((ch, i) => {
      if (i < OTP_LENGTH) next[i] = ch;
    });
    onChange(next);
    focusAt(Math.min(raw.length, OTP_LENGTH - 1));
  };

  const handleChange = (index: number, inputValue: string) => {
    const digitsOnly = inputValue.replace(/\D/g, '');
    if (digitsOnly.length > 1) {
      const next: OtpValue = [...EMPTY_OTP];
      let writeAt = index;
      for (const ch of digitsOnly) {
        if (writeAt < OTP_LENGTH) next[writeAt++] = ch;
      }
      onChange(next);
      focusAt(Math.min(writeAt, OTP_LENGTH - 1));
      return;
    }
    const digit = digitsOnly.slice(-1);
    onChange(
      value.map((c, i) => (i === index ? digit : c)) as OtpValue,
    );
    if (digit && index < OTP_LENGTH - 1) {
      focusAt(index + 1);
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !value[index] && index > 0) {
      e.preventDefault();
      inputRefs.current[index - 1]?.focus();
    }
  };

  return (
    <div
      className={cn(styles.row, className)}
      onPaste={handlePaste}
      role="group"
      aria-label={groupAriaLabel}
    >
      {value.map((digit, i) => (
        <input
          key={i}
          ref={(el) => {
            inputRefs.current[i] = el;
          }}
          type="text"
          inputMode="numeric"
          autoComplete={i === 0 ? 'one-time-code' : 'off'}
          maxLength={1}
          className={styles.cell}
          value={digit}
          aria-label={`Цифра ${i + 1}`}
          disabled={disabled}
          onChange={(e) => handleChange(i, e.target.value)}
          onKeyDown={(e) => handleKeyDown(i, e)}
        />
      ))}
    </div>
  );
}
