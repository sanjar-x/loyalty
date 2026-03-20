"use client";

import styles from "./Header.module.css";

interface HeaderProps {
  title: string;
  bgColor?: string;
  titleColor?: "white" | "black";
}

export default function Header({
  title,
  bgColor = "#ffffff",
  titleColor = "black",
}: HeaderProps) {
  const resolvedTitleColor = titleColor === "white" ? "#ffffff" : "#000000";

  return (
    <>
      <div className={styles.root} style={{ backgroundColor: bgColor }}>
        <h1 className={styles.title} style={{ color: resolvedTitleColor }}>
          {title}
        </h1>
      </div>
    </>
  );
}
