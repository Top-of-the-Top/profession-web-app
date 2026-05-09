import { z } from "zod";

function pickUserFacingText(v: unknown): string | null {
  if (typeof v === "string" && v.trim()) return v.trim();
  if (Array.isArray(v) && v.length > 0 && v.every((x) => typeof x === "string")) {
    return v.join(" ");
  }
  return null;
}

const DEFAULT_CODE_SENT =
  "Код подтверждения отправлен на почту или телефон.";

export const RegisterCodeSentSchema = z
  .object({
    status: z.unknown(),
    detail: z.unknown().optional(),
    message: z.unknown().optional(),
  })
  .passthrough()
  .transform((data) => {
    const raw = data.status;
    const statusNorm =
      typeof raw === "string"
        ? raw.trim().toLowerCase()
        : String(raw ?? "").trim().toLowerCase();

    if (statusNorm !== "code_sent") {
      throw new z.ZodError([
        {
          code: z.ZodIssueCode.custom,
          path: ["status"],
          message: `Ожидался status "code_sent", получено: ${String(raw)}`,
        },
      ]);
    }

    const detail =
      pickUserFacingText(data.detail) ??
      pickUserFacingText(data.message) ??
      DEFAULT_CODE_SENT;

    return {
      status: "code_sent" as const,
      detail,
    };
  });

export type RegisterCodeSent = z.infer<typeof RegisterCodeSentSchema>;
