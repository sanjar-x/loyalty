import type { TabIconProps } from "./icon-home";

export function IconFavorites({ filled = false }: TabIconProps) {
  if (filled) {
    return (
      <svg
        width="20"
        height="18"
        viewBox="0 0 20 18"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <path
          d="M9.56783 3.93379C7.6403 -0.59056 0.893921 -0.108675 0.893921 5.67396C0.893921 11.4566 9.56783 16.2756 9.56783 16.2756C9.56783 16.2756 18.2417 11.4566 18.2417 5.67396C18.2417 -0.108675 11.4954 -0.59056 9.56783 3.93379Z"
          fill="#2D2D2D"
          stroke="#2D2D2D"
          strokeWidth="1.78774"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  }

  return (
    <svg
      width="20"
      height="18"
      viewBox="0 0 20 18"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M9.56783 3.93379C7.6403 -0.59056 0.893921 -0.108675 0.893921 5.67396C0.893921 11.4566 9.56783 16.2756 9.56783 16.2756C9.56783 16.2756 18.2417 11.4566 18.2417 5.67396C18.2417 -0.108675 11.4954 -0.59056 9.56783 3.93379Z"
        stroke="#B6B6B6"
        strokeWidth="1.78774"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
