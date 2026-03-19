import { cn } from "@/lib/format/cn";
import styles from "./Layout.module.css";

export default function Container({ children, className = "" }) {
  return <div className={cn(styles.root, className)}>{children}</div>;
}
