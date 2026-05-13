import { Skeleton } from '@/components/ui/skeleton';

interface ReferralStatsCardProps {
  visited: number;
  started: number;
  promocodes: number;
  isLoading: boolean;
}

const STAT_ROWS = [
  { key: 'visited', label: 'Перешло по ссылке' },
  { key: 'started', label: 'Запустило приложение' },
  { key: 'promocodes', label: 'Получено промокодов' },
] as const;

export function ReferralStatsCard({ visited, started, promocodes, isLoading }: ReferralStatsCardProps) {
  const values = { visited, started, promocodes };

  return (
    <section
      className="mx-4 mt-3 rounded-2xl border border-black/[0.06] bg-white px-[22px] py-[29px]"
      aria-label="Статистика"
      aria-busy={isLoading || undefined}
    >
      {STAT_ROWS.map((row, idx) => (
        <div key={row.key}>
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm text-black">{row.label}</span>
            {isLoading ? (
              <Skeleton className="h-3.5 w-10 rounded-[10px]" />
            ) : (
              <strong className="text-[15px] font-normal text-black">
                {values[row.key]}
              </strong>
            )}
          </div>
          {idx < STAT_ROWS.length - 1 && (
            <div className="my-[7px] h-px bg-transparent" />
          )}
        </div>
      ))}
    </section>
  );
}
