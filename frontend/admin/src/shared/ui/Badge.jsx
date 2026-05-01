import { cn } from '@/shared/lib/utils';

const variants = {
  default: 'bg-app-card text-app-text-dark',
  china: 'bg-app-badge-china text-app-badge-china-text',
  dark: 'bg-app-text-dark text-white',
  muted: 'bg-[#f4f4f5] text-[#81858d]',
};

export function Badge({ children, variant = 'default', className }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-3 py-1 text-sm leading-5 font-medium',
        variants[variant],
        className,
      )}
    >
      {children}
    </span>
  );
}
