'use client';
import Image from 'next/image';
import styles from './PointsHistory.module.css';

// Backend Loyalty Points module doesn't exist yet (Spec §11). When the module
// is ready, RTKQ `useMyPointsHistoryQuery` will be wired here — history is empty for now.
export default function PointsHistory() {
  const history = [];

  return (
    <div className={styles.root}>
      <h2 className={styles.header}>История баллов:</h2>

      {history.length === 0 ? (
        <div className={styles.empty}>История пока пуста</div>
      ) : (
        <div className={styles.list}>
          {history.map((item, index) => (
            <div key={item.id} className={styles.item}>
              <div className={styles.row}>
                <div className={styles.left}>
                  <div className={styles.avatar}>
                    <Image
                      src={
                        item.points < 0
                          ? '/icons/promo/box-grey.webp'
                          : '/icons/promo/box-colored.webp'
                      }
                      alt="the box"
                      className={styles.avatarImg}
                      width={34}
                      height={34}
                    />
                  </div>

                  <div className={styles.info}>
                    <div className={styles.order}>Заказ {item.order}</div>
                    <div className={styles.date}>{item.date}</div>
                  </div>
                </div>

                <div
                  className={`${styles.points} ${
                    item.points < 0 ? `${styles.pointsNegative}` : ''
                  }`}
                >
                  {item.points > 0 ? `+${item.points}` : item.points}
                </div>
              </div>

              {index < history.length - 1 && <div className={styles.separator} />}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
