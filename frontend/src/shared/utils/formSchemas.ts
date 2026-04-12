import { z } from 'zod';
import { validateEmailOrPhone } from './validation';

export const emailOrPhoneSchema = z
  .string()
  .trim()
  .min(1, 'Введите почту или номер телефона')
  .refine(
    (value) => validateEmailOrPhone(value).isValid,
    'Введите корректный email или номер телефона',
  );

export const passwordSchema = z
  .string()
  .min(8, 'Пароль должен быть не короче 8 символов');

export const oneTimeCodeSchema = z
  .string()
  .trim()
  .regex(/^\d{6}$/, 'Введите 6 цифр кода');

export const loginFormSchema = z.object({
  emailOrPhone: emailOrPhoneSchema,
  password: z.string().min(1, 'Введите пароль'),
});

export type LoginFormValues = z.infer<typeof loginFormSchema>;

export const registerCredentialsSchema = z
  .object({
    emailOrPhone: emailOrPhoneSchema,
    password: passwordSchema,
    repeatPassword: z.string().min(1, 'Повторите пароль'),
  })
  .refine((data) => data.password === data.repeatPassword, {
    path: ['repeatPassword'],
    message: 'Введите одинаковый пароль в оба поля',
  });

export type RegisterCredentialsFormValues = z.infer<
  typeof registerCredentialsSchema
>;

export const recoverSetPasswordSchema = z
  .object({
    password: passwordSchema,
    confirmPassword: z.string().min(1, 'Подтвердите пароль'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    path: ['confirmPassword'],
    message: 'Введите одинаковый пароль в оба поля',
  });

export type RecoverSetPasswordFormValues = z.infer<
  typeof recoverSetPasswordSchema
>;

export const resetRequestSchema = z.object({
  emailOrPhone: emailOrPhoneSchema,
});

export type ResetRequestFormValues = z.infer<typeof resetRequestSchema>;

export const resetPhoneCodeSchema = z.object({
  code: oneTimeCodeSchema,
});

export type ResetPhoneCodeFormValues = z.infer<typeof resetPhoneCodeSchema>;

export const changeNameSchema = z.object({
  firstName: z.string().trim().min(1, 'Введите имя'),
  lastName: z.string().trim().min(1, 'Введите фамилию'),
});

export type ChangeNameFormValues = z.infer<typeof changeNameSchema>;

export const confirmEmailContactSchema = z.object({
  contact: z.string().trim().email('Введите корректный адрес почты'),
});

export const confirmPhoneContactSchema = z.object({
  contact: z
    .string()
    .trim()
    .refine((value) => {
      const digits = value.replace(/\D/g, '');
      return digits.length === 10 || digits.length === 11;
    }, 'Введите корректный номер телефона'),
});

export const confirmContactCodeSchema = z.object({
  code: oneTimeCodeSchema,
});

export type ConfirmContactInputFormValues = z.infer<
  typeof confirmEmailContactSchema
>;
export type ConfirmContactCodeFormValues = z.infer<
  typeof confirmContactCodeSchema
>;
