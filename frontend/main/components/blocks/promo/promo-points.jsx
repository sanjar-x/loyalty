"use client";
import { useState } from "react";
import styles from "./promo-points.module.css";

export default function PointsHistory() {
  const [history] = useState([
    {
      id: 1,
      order: "42974781810",
      date: "Май 10, 2025 в 21:20",
      points: -200,
    },
    {
      id: 2,
      order: "42974781809",
      date: "Май 9, 2025 в 22:20",
      points: 200,
    },
    {
      id: 3,
      order: "42974781820",
      date: "Май 8, 2025 в 22:20",
      points: 200,
      isInvite: true,
    },
  ]);

  return (
    <div className={styles.root}>
      {/* Заголовок */}
      <h2 className={styles.header}>История баллов:</h2>

      {/* Список записей */}
      <div className={styles.list}>
        {history.map((item, index) => (
          <div key={item.id} className={styles.item}>
            {/* Контейнер записи */}
            <div className={styles.row}>
              {/* Левая часть: аватар и информация */}
              <div className={styles.left}>
                {/* Аватар */}
                <div className={styles.avatar}>
                  <img
                    src={
                      item.points < 0
                        ? "/icons/promo/box-grey.svg"
                        : "/icons/promo/box-colored.svg"
                    }
                    alt="the box"
                    className={styles.avatarImg}
                  />
                </div>

                {/* Информация о заказе */}
                <div className={styles.info}>
                  <div className={styles.order}>Заказ {item.order}</div>
                  <div className={styles.date}>{item.date}</div>
                </div>
              </div>

              {/* Сумма баллов (справа) */}
              <div
                className={`${styles.points} ${item.points < 0 ? `${styles.pointsNegative}` : ""}`}
              >
                {item.points > 0 ? `+${item.points}` : item.points}
              </div>
            </div>

            {/* Линия-разделитель (кроме последнего элемента) */}
            {index < history.length - 1 && <div className={styles.separator} />}
          </div>
        ))}
      </div>
    </div>
  );
}
