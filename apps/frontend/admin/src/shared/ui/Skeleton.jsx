/**
 * Audit 1.1 / 4.2 — generic skeleton primitive used by the page-level
 * skeletons (product detail, product edit). Pure presentation; pulse
 * animation is the same one already used for ProductRowSkeleton, just
 * lifted to a Tailwind utility so we don't repeat the CSS-module wiring
 * for every new placeholder.
 *
 * Use `<Skeleton.Bar w={…} h={…} />` for one-liners, `<Skeleton.Block />`
 * for taller placeholders, and `<Skeleton.Circle size={…} />` for
 * avatar / status-dot placeholders. All three carry `aria-hidden` so SR
 * users don't hear repeated «pulse pulse pulse»; the page-level loading
 * announcement is the responsibility of the parent.
 */
export function Skeleton({ className = '', style, role }) {
  const ariaProps =
    role === 'status' ? { role: 'status', 'aria-label': 'Загрузка' } : {};
  return (
    <div
      {...ariaProps}
      aria-hidden={role === 'status' ? undefined : 'true'}
      className={`bg-app-card animate-pulse rounded-md ${className}`}
      style={style}
    />
  );
}

function Bar({ w, h = 16, className = '' }) {
  return <Skeleton className={className} style={{ width: w, height: h }} />;
}

function Block({ h = 96, className = '' }) {
  return <Skeleton className={className} style={{ height: h }} />;
}

function Circle({ size = 40, className = '' }) {
  return (
    <Skeleton
      className={`rounded-full ${className}`}
      style={{ width: size, height: size }}
    />
  );
}

Skeleton.Bar = Bar;
Skeleton.Block = Block;
Skeleton.Circle = Circle;
