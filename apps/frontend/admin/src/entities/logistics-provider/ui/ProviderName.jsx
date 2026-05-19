import CdekWordmark from '@/assets/logos/cdek-wordmark.svg';
import DobroPostWordmark from '@/assets/logos/dobropost-wordmark.svg';
import YandexDeliveryWordmark from '@/assets/logos/yandex-delivery-wordmark.svg';
import { cn } from '@/shared/lib/utils';
import { providerLabel } from '../lib/providerSchema';

// Full brand wordmarks — rendered in place of the plain-text provider name
// wherever a provider is identified. Providers without a wordmark fall back
// to their text label.
const PROVIDER_WORDMARKS = {
  cdek: CdekWordmark,
  dobropost: DobroPostWordmark,
  yandex_delivery: YandexDeliveryWordmark,
};

/**
 * Provider identity label — the real brand wordmark when available, plain
 * text otherwise.
 *
 *   logoClassName — sizes the wordmark (set a height; width stays auto).
 *   className     — styles the text fallback (inherits the call-site type).
 */
export function ProviderName({ code, className, logoClassName }) {
  const Wordmark = PROVIDER_WORDMARKS[code];

  if (Wordmark) {
    return (
      <Wordmark
        className={cn('w-auto', logoClassName)}
        role="img"
        aria-label={providerLabel(code)}
      />
    );
  }

  return <span className={className}>{providerLabel(code)}</span>;
}
