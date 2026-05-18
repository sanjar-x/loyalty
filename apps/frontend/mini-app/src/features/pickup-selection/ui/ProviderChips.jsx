import { cn } from '@/shared/lib/ui-utils';

import { PVZ_PROVIDERS } from '@/entities/pickup-point/lib/pvzProviders';

import styles from './page.module.css';

/**
 * PVZ provider filter chips (All / CDEK / Yandex). Audit #1:
 * presentation extracted from the `app/checkout/pickup/page.jsx` god component.
 *
 * `ProviderIcon` is local — used only inside this component.
 */

function ProviderIcon({ providerCode }) {
  if (providerCode === 'cdek') {
    return (
      <svg
        width="22"
        height="22"
        viewBox="0 0 22 22"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          fillRule="evenodd"
          clipRule="evenodd"
          d="M10.9998 0C17.0748 0 21.9999 4.9248 21.9999 10.9998C21.9999 17.0748 17.0748 21.9996 10.9998 21.9996C4.92461 21.9996 0 17.0748 0 10.9998C0 4.9248 4.92461 0 10.9998 0ZM4.83866 5.23205C4.91287 5.23205 4.98356 5.24751 5.04732 5.27531L5.04818 5.2745C5.36689 5.40123 5.74373 5.53277 6.06687 5.61181C7.38586 5.9391 8.73303 6.14343 10.1899 6.19447C12.3953 6.27812 14.8101 6.2187 17.6114 6.19946L17.6142 6.19924H17.6276V6.19905C17.9162 6.19905 18.1498 6.43285 18.1498 6.72127C18.1498 6.96528 17.9824 7.17022 17.7559 7.22755C13.127 8.89181 9.26192 11.1715 6.26782 15.2743C6.04574 15.5802 5.81695 15.8973 5.61114 16.2159C5.60508 16.2259 5.59921 16.2356 5.59254 16.2452L5.59211 16.2458C5.49782 16.3818 5.34075 16.4709 5.16256 16.4709C4.8742 16.4709 4.64038 16.2371 4.64038 15.9487C4.64038 15.92 4.64287 15.892 4.64706 15.8646L4.64855 15.8563C5.01661 13.703 5.49219 11.5942 6.37785 9.62646C5.75337 8.64961 5.01365 7.52637 4.36933 5.98785L4.3708 5.98618C4.33609 5.91631 4.31644 5.83765 4.31644 5.75423C4.31644 5.46586 4.55024 5.23205 4.83866 5.23205ZM6.78646 18.3597C6.77287 18.3866 6.75717 18.4126 6.73943 18.4367V18.4369C6.64447 18.566 6.49118 18.6502 6.31822 18.6502C6.03006 18.6502 5.79624 18.4164 5.79624 18.1281C5.79624 18.0299 5.8232 17.9385 5.87027 17.8601H5.87008L5.87193 17.8574L6.29796 17.16C9.33305 12.4564 13.1909 10.0437 18.1813 8.24433C18.215 8.22784 18.2506 8.21463 18.2879 8.20566H18.2886C18.3279 8.19622 18.3687 8.19121 18.4107 8.19121C18.6991 8.19121 18.9329 8.42501 18.9329 8.71343C18.9329 8.93173 18.7987 9.11893 18.6084 9.19673V9.19692L18.6048 9.19816C18.5931 9.20279 18.5812 9.20718 18.569 9.21094C13.4485 11.0418 9.80966 13.3741 6.78646 18.3597Z"
          fill="#2D2D2D"
        />
      </svg>
    );
  }
  // yandex_delivery
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M9.39303 0.0503741C7.03646 0.423252 5.04356 1.42068 3.30032 3.09983C1.75064 4.5926 0.83489 6.17798 0.217332 8.43709C-0.0956258 9.58236 -0.0649481 12.5231 0.272963 13.7541C1.85824 19.53 7.59415 23.0175 13.3994 21.735C15.3693 21.2998 17.0525 20.3831 18.5916 18.907C23.0601 14.6219 23.1459 7.62078 18.7838 3.22664C17.4304 1.86331 15.5856 0.794872 13.7428 0.307306C12.8406 0.0686694 10.2464 -0.0845525 9.39303 0.0503741ZM14.7158 11.067V17.5847H13.5711H12.4264V11.8539V6.1231L11.4248 6.19937C9.45839 6.34893 8.59163 7.11401 8.61567 8.67881C8.62323 9.16592 8.70816 9.62204 8.85033 9.94003C9.1056 10.5104 9.98426 11.3746 11.0242 12.078C11.4178 12.3442 11.7367 12.5987 11.733 12.6435C11.7293 12.6883 10.9954 13.8056 10.1018 15.1262L8.47728 17.5275L7.30397 17.5601C6.58523 17.5801 6.13067 17.5489 6.13067 17.4797C6.13067 17.4175 6.76952 16.4244 7.55043 15.2727L8.97007 13.179L8.0708 12.3478C7.39738 11.7254 7.07664 11.3243 6.79413 10.7511C6.43985 10.0323 6.41684 9.91213 6.41684 8.78253C6.41684 7.72347 6.45267 7.50312 6.71675 6.94078C7.1072 6.10892 7.7148 5.51421 8.59404 5.10326C9.59484 4.63536 10.0244 4.57602 12.5123 4.56195L14.7158 4.54938V11.067Z"
        fill="#2D2D2D"
      />
    </svg>
  );
}

export default function ProviderChips({ activeProvider, onSelectProvider }) {
  return (
    <div className={styles.c5}>
      <div className={cn(styles.c6, styles.tw2, styles.noScrollbar)}>
        <button
          type="button"
          aria-pressed={activeProvider === 'all'}
          onClick={() => onSelectProvider('all')}
          className={cn(
            styles.providerChip,
            activeProvider === 'all' ? styles.providerChipActive : styles.providerChipInactive
          )}
        >
          <span className={cn(styles.c7, styles.tw3)}>
            <span className={cn(styles.c8, styles.tw4)}>
              <span className={cn(styles.c9, styles.tw5)} />
              <span className={cn(styles.c10, styles.tw6)} />
              <span className={cn(styles.c11, styles.tw7)} />
              <span className={cn(styles.c12, styles.tw8)} />
            </span>
          </span>
          <span className={cn(styles.c13, styles.nowrap)}>Все</span>
        </button>
        {PVZ_PROVIDERS.map((p) => {
          const isOn = activeProvider === p.code;
          return (
            <button
              key={p.code}
              type="button"
              aria-pressed={isOn}
              onClick={() => onSelectProvider(p.code)}
              className={cn(
                styles.providerChip,
                isOn ? styles.providerChipActive : styles.providerChipInactive
              )}
            >
              <span className={cn(styles.c14, styles.tw9)}>
                <ProviderIcon providerCode={p.code} />
              </span>
              <span className={cn(styles.c15, styles.nowrap)}>{p.short}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
