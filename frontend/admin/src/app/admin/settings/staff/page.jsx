'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import StatsIcon from '@/assets/icons/stats.svg';
import MoreIcon from '@/assets/icons/more-dots.svg';
import CopyIcon from '@/assets/icons/copy.svg';
import { useBodyScrollLock } from '@/shared/hooks/useBodyScrollLock';
import { useEscapeKey } from '@/shared/hooks/useEscapeKey';
import { randomHexToken } from '@/shared/lib/genId';
import { getStaff } from '@/entities/staff';
import styles from './page.module.css';

const INVITE_TOKEN_BYTES = 8;
const INVITE_DOMAIN =
  process.env.NEXT_PUBLIC_INVITE_DOMAIN ?? 'invite.admin.loyaltymarket.ru';

export default function StaffPage() {
  const [items] = useState(() => getStaff());
  const [isOpen, setIsOpen] = useState(false);
  const [openSelect, setOpenSelect] = useState(null);
  const [inviteLink, setInviteLink] = useState('');

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('');

  const nameRef = useRef(null);

  const roleOptions = useMemo(() => {
    return ['Администратор', 'Контент-менеджер'];
  }, []);

  const canSubmit = useMemo(() => {
    if (inviteLink) return false;
    return Boolean(name.trim()) && Boolean(email.trim()) && Boolean(role);
  }, [email, inviteLink, name, role]);

  const close = useCallback(() => {
    setIsOpen(false);
    setOpenSelect(null);
    setInviteLink('');
    setName('');
    setEmail('');
    setRole('');
  }, []);

  useBodyScrollLock(isOpen);
  useEscapeKey(close, isOpen);

  useEffect(() => {
    if (isOpen) nameRef.current?.focus();
  }, [isOpen]);

  const onCreateInvite = () => {
    setInviteLink(
      `https://${INVITE_DOMAIN}/${randomHexToken(INVITE_TOKEN_BYTES)}`,
    );
  };

  const copyInvite = async () => {
    if (!inviteLink) return;
    try {
      await navigator.clipboard.writeText(inviteLink);
    } catch {
      // ignore
    }
  };

  return (
    <section>
      <header className={styles.header}>
        <h2 className={styles.headerTitle}>Сотрудники</h2>
        <button
          type="button"
          className={styles.primaryButton}
          onClick={() => setIsOpen(true)}
        >
          Добавить сотрудника
        </button>
      </header>

      <div className={styles.panel}>
        {!items.length ? (
          <div className={styles.empty}>
            <p className={styles.emptyTitle}>Сотрудники не найдены</p>
            <p className={styles.emptyText}>Добавьте первого сотрудника.</p>
          </div>
        ) : (
          items.map((row) => (
            <div key={row.id} className={styles.listRow}>
              <div className={styles.personCell}>
                <div className={styles.avatar} aria-hidden="true" />
                <div className={styles.personInfo}>
                  <div className={styles.personName}>{row.name}</div>
                  <div className={styles.personEmail}>{row.email}</div>
                </div>
              </div>
              <div className={styles.roleCell}>{row.role}</div>
              <div className={styles.actions}>
                <button
                  type="button"
                  className={styles.iconButton}
                  aria-label="Статистика"
                >
                  <StatsIcon className={styles.actionIcon} />
                </button>
                <button
                  type="button"
                  className={styles.iconButton}
                  aria-label="Меню"
                >
                  <MoreIcon className={styles.actionIcon} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {isOpen ? (
        <div
          className={styles.modalOverlay}
          role="presentation"
          onClick={close}
        >
          <div
            className={styles.modalCard}
            role="dialog"
            aria-modal="true"
            aria-labelledby="add-staff-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className={styles.modalHeader}>
              <h3 id="add-staff-title" className={styles.modalTitle}>
                Добавление сотрудника
              </h3>
              <button
                type="button"
                className={styles.modalClose}
                onClick={close}
                aria-label="Закрыть"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 20 20"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  aria-hidden="true"
                >
                  <path
                    d="M5 5L15 15"
                    stroke="#111111"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                  <path
                    d="M15 5L5 15"
                    stroke="#111111"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                </svg>
              </button>
            </div>

            <form
              className={styles.modalBody}
              onMouseDown={() => setOpenSelect(null)}
              onSubmit={(e) => {
                e.preventDefault();
                if (!canSubmit) return;
                onCreateInvite();
              }}
            >
              {inviteLink ? (
                <div
                  className={styles.linkField}
                  onMouseDown={(e) => e.stopPropagation()}
                >
                  <div className={styles.linkLabel}>Ссылка-приглашение</div>
                  <div className={styles.linkValue}>{inviteLink}</div>
                  <button
                    type="button"
                    className={styles.copyButton}
                    onClick={copyInvite}
                    aria-label="Скопировать"
                  >
                    <CopyIcon width={28} height={28} />
                  </button>
                </div>
              ) : (
                <>
                  <div
                    className={`${styles.field} ${
                      name ? styles.fieldFilled : ''
                    }`}
                    onMouseDown={(e) => e.stopPropagation()}
                  >
                    <span className={styles.label}>Имя</span>
                    <input
                      ref={nameRef}
                      className={styles.input}
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      autoComplete="off"
                    />
                  </div>

                  <div
                    className={`${styles.field} ${
                      email ? styles.fieldFilled : ''
                    }`}
                    onMouseDown={(e) => e.stopPropagation()}
                  >
                    <span className={styles.label}>Эл. почта</span>
                    <input
                      className={styles.input}
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      autoComplete="off"
                    />
                  </div>

                  <div
                    className={`${styles.field} ${
                      role ? styles.fieldFilled : ''
                    } ${openSelect === 'role' ? styles.fieldActive : ''}`}
                    onMouseDown={(e) => e.stopPropagation()}
                  >
                    <span className={styles.label}>Роль</span>
                    <button
                      type="button"
                      className={styles.selectButton}
                      onClick={() =>
                        setOpenSelect((prev) =>
                          prev === 'role' ? null : 'role',
                        )
                      }
                      aria-expanded={openSelect === 'role'}
                    >
                      <span className={styles.selectValue}>{role}</span>
                    </button>
                    <svg
                      className={`${styles.chevron} ${
                        openSelect === 'role' ? styles.chevronOpen : ''
                      }`}
                      width="24"
                      height="24"
                      viewBox="0 0 24 24"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                      aria-hidden="true"
                    >
                      <path
                        d="M6 9L12 15L18 9"
                        stroke="currentColor"
                        strokeWidth="2.2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>

                    {openSelect === 'role' ? (
                      <div
                        className={styles.dropdown}
                        role="listbox"
                        onMouseDown={(e) => e.stopPropagation()}
                      >
                        {roleOptions.map((opt) => (
                          <button
                            key={opt}
                            type="button"
                            className={styles.dropdownItem}
                            onClick={() => {
                              setRole(opt);
                              setOpenSelect(null);
                            }}
                            role="option"
                            aria-selected={role === opt}
                          >
                            {opt}
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>

                  <div className={styles.footer}>
                    <button
                      type="submit"
                      className={styles.submit}
                      disabled={!canSubmit}
                    >
                      Создать ссылку-приглашение
                    </button>
                  </div>
                </>
              )}
            </form>
          </div>
        </div>
      ) : null}
    </section>
  );
}
