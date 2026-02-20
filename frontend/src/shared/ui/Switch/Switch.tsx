import styles from "./Switch.module.css";
import type { ComponentProps } from "react";
import * as SwitchPrimitives from "@radix-ui/react-switch";

export function Switch({
  className,
  ...props
}: ComponentProps<typeof SwitchPrimitives.Root>) {
  return (
    <SwitchPrimitives.Root
      className={`${styles.switch} ${className ?? ""}`.trim()}
      {...props}>
      <SwitchPrimitives.Thumb className={styles["switch-thumb"]} />
    </SwitchPrimitives.Root>
  );
}
