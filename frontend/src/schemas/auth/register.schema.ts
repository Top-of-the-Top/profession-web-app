import { z } from "zod";

export const RegisterTokensSchema = z.object({
	access_token: z.string(),
	access_expires_at: z.string(),  // ISO string
	refresh_token: z.string(),
	refresh_expires_at: z.string(),
});

export type RegisterTokens = z.infer<typeof RegisterTokensSchema>;
