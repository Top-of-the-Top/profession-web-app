import { z } from "zod";

export const ResetSchema = z.object({
  status: z.string(),
  detail: z.string().optional(),
});

export type ResetSchema = z.infer<typeof ResetSchema>;
