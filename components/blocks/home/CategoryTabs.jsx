"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { cn } from "@/lib/format/cn";
import styles from "./CategoryTabs.module.css";

const tabs = ["Для вас", "Новинки", "Одежда", "Обувь", "Аксессуары"];

export default function CategoryTabs() {
  const [activeTab, setActiveTab] = useState("Для вас");
  const router = useRouter();

  const handleTabClick = (tab) => {
    setActiveTab(tab);
    router.push(`/search?query=${encodeURIComponent(tab)}`);
  };

  return (
    <div className={cn(styles.outer, "scrollbar-hide")}>
      <div className={styles.inner}>
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => handleTabClick(tab)}
            type="button"
            className={cn(styles.tab, activeTab === tab && styles.active)}
          >
            {tab}
          </button>
        ))}
      </div>
    </div>
  );
}
