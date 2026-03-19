'use client'
import React from 'react'
import { Star } from 'lucide-react'
import styles from './ReviewCard.module.css'

/**
 * Компонент карточки отзыва
 */
export default function ReviewCard({ review }) {
  const renderStars = (rating) => {
    return Array.from({ length: 5 }, (_, index) => (
      <Star
        key={index}
        className={`${styles.star} ${index < rating ? styles.starOn : styles.starOff}`}
      />
    ))
  }

  return (
    <div className={styles.root}>
      {/* Заголовок отзыва */}
      <div className={styles.header}>
        <img
          src={review.avatar}
          alt={review.userName || 'Пользователь'}
          className={styles.avatar}
        />
        <div className={styles.meta}>
          <div className={styles.stars}>
            {renderStars(review.rating)}
          </div>
          {review.title && (
            <p className={styles.title}>
              {review.title}
            </p>
          )}
          {review.date && (
            <p className={styles.date}>
              {review.date}
            </p>
          )}
        </div>
      </div>

      {/* Контент отзыва */}
      <div className={styles.content}>
        {/* Достоинства */}
        <div>
          <p className={styles.label}>
            Достоинства:{' '}
            <span className={styles.value}>{review.pros}</span>
          </p>
        </div>

        {/* Недостатки */}
        <div>
          <p className={styles.label}>
            Недостатки:{' '}
            <span className={`${styles.value} ${styles.cons}`}>{review.cons}</span>
          </p>
        </div>
      </div>
    </div>
  )
}

