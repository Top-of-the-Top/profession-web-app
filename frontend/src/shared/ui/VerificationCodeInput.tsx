import { OtpInput, type OtpValue } from '@components/OtpInput';
import { Label } from './Label';
import { cn } from '@shared/lib/utils';

type VerificationCodeInputProps = {
  value: OtpValue;
  onChange: (next: OtpValue) => void;
  disabled?: boolean;
  label?: string;
  hint?: string;
  error?: string;
  className?: string;
  labelClassName?: string;
  otpClassName?: string;
  hintClassName?: string;
  errorClassName?: string;
};

export function VerificationCodeInput({
  value,
  onChange,
  disabled = false,
  label = 'Код подтверждения',
  hint,
  error,
  className,
  labelClassName,
  otpClassName,
  hintClassName,
  errorClassName,
}: VerificationCodeInputProps) {
  return (
    <div className={className}>
      <Label className={labelClassName}>{label}</Label>
      <OtpInput value={value} onChange={onChange} disabled={disabled} className={otpClassName} />
      {hint ? <p className={hintClassName}>{hint}</p> : null}
      {error ? <p className={cn(errorClassName)}>{error}</p> : null}
    </div>
  );
}
