import React from "react";

import { cn } from "@/lib/format/cn";
import styles from "./Layout.module.css";

interface ContainerProps {
  children: React.ReactNode;
  className?: string;
}

export default function Container({ children, className = "" }: ContainerProps) {
  return <div className={cn(styles.root, className)}>{children}</div>;
}
