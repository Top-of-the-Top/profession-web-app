import { z } from "zod";

export const RecoverPhoneTokenSchema = z.object({
  token: z.string(),
});

export type RecoverPhoneToken = z.infer<typeof RecoverPhoneTokenSchema>;
