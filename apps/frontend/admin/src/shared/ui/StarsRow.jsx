import { cn } from '@/shared/lib/utils';

export function Star({ filled, className }) {
  if (filled) {
    return (
      <svg
        width="16"
        height="16"
        viewBox="0 0 17 16"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={cn('block h-4 w-4', className)}
        aria-hidden="true"
      >
        <path
          d="M8.08398 0L10.4322 5.26798L16.168 5.87336L11.8835 9.73452L13.0802 15.3766L8.08398 12.495L3.08781 15.3766L4.28451 9.73452L3.8147e-06 5.87336L5.73578 5.26798L8.08398 0Z"
          fill="#2D2D2D"
        />
      </svg>
    );
  }

  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 17 16"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn('block h-4 w-4', className)}
      aria-hidden="true"
    >
      <path
        d="M9.97559 5.47168L10.0928 5.73535L10.3799 5.76562L15 6.25195L11.5488 9.36328L11.335 9.55664L11.3945 9.83789L12.3574 14.3818L8.33398 12.0615L8.08398 11.918L7.83398 12.0615L3.80957 14.3818L4.77344 9.83789L4.83301 9.55664L4.61914 9.36328L1.16699 6.25195L5.78809 5.76562L6.0752 5.73535L6.19238 5.47168L8.08398 1.22754L9.97559 5.47168Z"
        stroke="#2D2D2D"
      />
    </svg>
  );
}

export function StarsRow({ rating, className }) {
  const safe = Math.max(0, Math.min(5, Number(rating) || 0));
  return (
    <div
      className={cn('flex items-center gap-0.5', className)}
      aria-label={`Оценка ${safe} из 5`}
    >
      {Array.from({ length: 5 }, (_, idx) => (
        <Star key={idx} filled={idx < safe} />
      ))}
    </div>
  );
}
