import styles from "./Input.module.css";
import type { ComponentProps } from "react";

export function Input({ className, ...props }: ComponentProps<"input">) {
  return (
    <input className={`${styles.input} ${className ?? ""}`.trim()} {...props} />
  );
}

