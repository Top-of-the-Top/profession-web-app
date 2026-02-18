import styles from "./styles.module.css";
import type { ComponentProps } from "react";

type AlertProps = ComponentProps<"div"> & {
  variant?: "default" | "destructive";
};

export function Alert({ variant = "default", className, ...props }: AlertProps) {
  return (
    <div
      data-slot="alert"
      role="alert"
      data-variant={variant}
      className={`${styles.alert} ${className ?? ""}`.trim()}
      {...props}
    />
  );
}

export function AlertTitle({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-title"
      className={`${styles["alert-title"]} ${className ?? ""}`.trim()}
      {...props}
    />
  );
}

export function AlertDescription({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-description"
      className={`${styles["alert-description"]} ${className ?? ""}`.trim()}
      {...props}
    />
  );
}


