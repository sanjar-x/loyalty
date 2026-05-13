import Image from 'next/image';

import { Check, Minus } from 'lucide-react';

import { Skeleton } from '@/components/ui/skeleton';
import { formatRuDateTime } from '@/lib/format';
import type { InvitedUser } from '@/types';

interface InvitationHistoryProps {
  users: InvitedUser[];
  isLoading: boolean;
}

function isExistingStatus(status: string): boolean {
  const s = status.toLowerCase();
  return (
    s.includes('уже') ||
    s.includes('польз') ||
    s.includes('зарегистр') ||
    s.includes('registered') ||
    s.includes('exists')
  );
}

function getUserDisplayName(user: InvitedUser): string {
  return (
    user.invitee_username ||
    user.invitee_tg_id ||
    String(user.invitee_id)
  );
}

export function InvitationHistory({ users, isLoading }: InvitationHistoryProps) {
  return (
    <section className="mx-4 mt-[18px]" aria-labelledby="invite-history">
      <h2
        id="invite-history"
        className="mb-2.5 text-xs font-normal tracking-wide text-[#111]/45"
      >
        История приглашений
      </h2>

      {(isLoading || users.length > 0) && (
        <ul className="m-0 list-none overflow-hidden rounded-2xl bg-white p-0">
          {isLoading
            ? Array.from({ length: 3 }, (_, i) => (
                <li
                  key={`skeleton-${i}`}
                  className="grid grid-cols-[44px_1fr] gap-3 border-t border-black/[0.06] px-3.5 py-3 first:border-t-0"
                  aria-hidden="true"
                >
                  <Skeleton className="h-11 w-11 rounded-full" />
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <Skeleton className="h-3.5 w-40 rounded-[10px]" />
                      <Skeleton className="mt-2 h-3 w-24 rounded-[10px]" />
                    </div>
                    <Skeleton className="h-3 w-[72px] shrink-0 rounded-[10px]" />
                  </div>
                </li>
              ))
            : users.map((user) => {
                const name = getUserDisplayName(user);
                const date = formatRuDateTime(user.created_at);
                const existing = isExistingStatus(user.status);

                return (
                  <li
                    key={user.invite_id}
                    className="grid grid-cols-[44px_1fr] gap-3 border-t border-black/[0.06] px-3.5 py-3 first:border-t-0"
                  >
                    <Image
                      src="/icons/invite-friends/7-avatar.webp"
                      alt={`Аватар ${name}`}
                      width={44}
                      height={44}
                      className="h-11 w-11 rounded-full"
                    />

                    <div className="flex min-w-0 items-center justify-between gap-3">
                      <div className="min-w-0">
                        <div className="truncate text-[15px] font-semibold text-[#111]">
                          {name}
                        </div>
                        <div className="mt-0.5 truncate text-xs text-[#111]/45">
                          {date}
                        </div>
                      </div>

                      <div className="grid shrink-0 justify-items-end gap-1.5">
                        <span className="text-[#111]/65" aria-hidden="true">
                          {existing ? <Minus size={20} /> : <Check size={18} />}
                        </span>
                        <span className="text-xs text-[#111]/45">
                          {user.status}
                        </span>
                      </div>
                    </div>
                  </li>
                );
              })}
        </ul>
      )}
    </section>
  );
}
