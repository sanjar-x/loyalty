"use client";

import { useRouter } from "next/navigation";
import styles from "./Header.module.css";

export default function Header({
  title,
  subtitle,
  titleColor = "black",
  onClose,
  onMoreClick,
  showClose = false,
  showMore = false,
  hideOnDesktop = false,
}) {
  const router = useRouter();
  const resolvedTitleColor = titleColor === "white" ? "#ffffff" : "#000000";

  const handleClose = () => {
    if (onClose) {
      onClose();
    } else {
      router.back();
    }
  };

  return (
    <div className={`${styles.root} ${hideOnDesktop ? styles.rootHideDesktop : ""}`}>
      <div className={styles.row}>
        {/* Left: close button */}
        <button
          type="button"
          className={styles.iconBtn}
          onClick={handleClose}
          aria-label="Close"
          style={{ visibility: showClose ? "visible" : "hidden" }}
        >
          <img
            src="/icons/global/xiconBlack.svg"
            alt="close"
            width={10}
            height={10}
          />
        </button>

        {/* Center: title */}
        <div className={styles.titleWrap}>
          <h1 className={styles.title} style={{ color: resolvedTitleColor }}>
            {title}
          </h1>
          {subtitle ? (
            <div className={styles.subtitle}>{subtitle}</div>
          ) : null}
        </div>

        {/* Right: three-dots menu */}
        <button
          type="button"
          className={styles.iconBtn}
          onClick={onMoreClick}
          aria-label="More options"
          style={{ visibility: showMore ? "visible" : "hidden" }}
        >
          <img
            src="/icons/global/threeDots.svg"
            alt="more"
            width={4}
            height={16}
          />
        </button>
      </div>
    </div>
  );
}
