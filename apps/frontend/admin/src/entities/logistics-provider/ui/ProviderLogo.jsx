import CdekLogo from '@/assets/logos/cdek.svg';
import DobroPostLogo from '@/assets/logos/dobropost.svg';
import YandexDeliveryLogo from '@/assets/logos/yandex-delivery.svg';
import { cn } from '@/shared/lib/utils';
import { PROVIDER_MONOGRAM, providerLabel } from '../lib/providerSchema';

// Brand marks for the provider card / picker avatar. The monogram tile
// stays as the fallback for any unrecognised provider code.
const PROVIDER_LOGOS = {
  cdek: CdekLogo,
  dobropost: DobroPostLogo,
  yandex_delivery: YandexDeliveryLogo,
};

/**
 * Square provider mark — the real brand logo when available, a monogram
 * tile otherwise. `className` controls the footprint (size + corner
 * radius); a logo keeps its own aspect ratio centred inside that box,
 * the monogram fills it as a solid tile.
 */
export function ProviderLogo({ code, className }) {
  const Logo = PROVIDER_LOGOS[code];

  if (Logo) {
    return (
      <Logo
        className={cn('shrink-0', className)}
        role="img"
        aria-label={providerLabel(code)}
      />
    );
  }

  return (
    <span
      aria-hidden="true"
      className={cn(
        'bg-app-sidebar flex shrink-0 items-center justify-center text-xs font-bold text-white',
        className,
      )}
    >
      {PROVIDER_MONOGRAM[code] ?? '??'}
    </span>
  );
}
