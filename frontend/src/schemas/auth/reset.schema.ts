import { z } from "zod";

export const ResetSchema = z.object({
  status: z.string()
});

export type ResetSchema = z.infer<typeof ResetSchema>;
