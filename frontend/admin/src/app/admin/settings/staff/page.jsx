'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { staffSeed } from '@/data/staff';
import styles from './page.module.css';

// TODO: StatsIcon is duplicated in promocodes/page.jsx — extract to shared component (e.g. @/components/icons/StatsIcon)
function StatsIcon() {
  return (
    <svg
      className={styles.actionIcon}
      viewBox="0 0 26 26"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M16.25 24.6457H9.74996C3.86746 24.6457 1.35413 22.1323 1.35413 16.2498V9.74984C1.35413 3.86734 3.86746 1.354 9.74996 1.354H16.25C22.1325 1.354 24.6458 3.86734 24.6458 9.74984V16.2498C24.6458 22.1323 22.1325 24.6457 16.25 24.6457ZM9.74996 2.979C4.75579 2.979 2.97913 4.75567 2.97913 9.74984V16.2498C2.97913 21.244 4.75579 23.0207 9.74996 23.0207H16.25C21.2441 23.0207 23.0208 21.244 23.0208 16.2498V9.74984C23.0208 4.75567 21.2441 2.979 16.25 2.979H9.74996Z"
        fill="#292D32"
      />
      <path
        d="M7.94079 16.51C7.76746 16.51 7.59413 16.4558 7.44246 16.3367C7.08496 16.0658 7.01996 15.5567 7.29079 15.1992L9.86912 11.8517C10.1833 11.4508 10.6275 11.1908 11.1366 11.1258C11.635 11.0608 12.1441 11.2017 12.545 11.5158L14.5275 13.0758C14.6033 13.1408 14.6791 13.1408 14.7333 13.13C14.7766 13.13 14.8525 13.1083 14.9175 13.0217L17.42 9.79334C17.6908 9.43584 18.2108 9.37084 18.5575 9.65251C18.915 9.92334 18.98 10.4325 18.6983 10.79L16.1958 14.0183C15.8816 14.4192 15.4375 14.6792 14.9283 14.7333C14.4191 14.7983 13.9208 14.6575 13.52 14.3433L11.5375 12.7833C11.4616 12.7183 11.375 12.7183 11.3316 12.7292C11.2883 12.7292 11.2125 12.7508 11.1475 12.8375L8.56913 16.185C8.42829 16.4017 8.18996 16.51 7.94079 16.51Z"
        fill="#292D32"
      />
    </svg>
  );
}

function MoreIcon() {
  return (
    <svg
      className={styles.actionIcon}
      viewBox="0 0 20 20"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M5 10C5 10.8284 4.32843 11.5 3.5 11.5C2.67157 11.5 2 10.8284 2 10C2 9.17157 2.67157 8.5 3.5 8.5C4.32843 8.5 5 9.17157 5 10Z"
        fill="currentColor"
      />
      <path
        d="M11.5 10C11.5 10.8284 10.8284 11.5 10 11.5C9.17157 11.5 8.5 10.8284 8.5 10C8.5 9.17157 9.17157 8.5 10 8.5C10.8284 8.5 11.5 9.17157 11.5 10Z"
        fill="currentColor"
      />
      <path
        d="M18 10C18 10.8284 17.3284 11.5 16.5 11.5C15.6716 11.5 15 10.8284 15 10C15 9.17157 15.6716 8.5 16.5 8.5C17.3284 8.5 18 9.17157 18 10Z"
        fill="currentColor"
      />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg
      width="28"
      height="28"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M9 9H16C17.1046 9 18 9.89543 18 11V18C18 19.1046 17.1046 20 16 20H9C7.89543 20 7 19.1046 7 18V11C7 9.89543 7.89543 9 9 9Z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <path
        d="M16 9V7C16 5.89543 15.1046 5 14 5H7C5.89543 5 5 5.89543 5 7V14C5 15.1046 5.89543 16 7 16H7"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function StaffPage() {
  const [items] = useState(staffSeed);
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

  useEffect(() => {
    if (!isOpen) return undefined;

    nameRef.current?.focus();

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const onKeyDown = (event) => {
      if (event.key === 'Escape') close();
    };

    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [isOpen, close]);

  const onCreateInvite = () => {
    const bytes = crypto.getRandomValues(new Uint8Array(8));
    const token = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
    // TODO: Domain should come from environment variable (e.g. NEXT_PUBLIC_INVITE_DOMAIN) instead of being hardcoded
    setInviteLink(`https://invite.admin.loyaltymarket.ru/${token}`);
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
                  <StatsIcon />
                </button>
                <button
                  type="button"
                  className={styles.iconButton}
                  aria-label="Меню"
                >
                  <MoreIcon />
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
                    <CopyIcon />
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
