"use client";

import React, { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useCart } from "@/components/blocks/cart/useCart";
import styles from "./page.module.css";
import cn from "clsx";
import SplitPaymentSheet from "@/components/blocks/product/SplitPaymentSheet";

const CHECKOUT_SELECTED_KEY = "loyaltymarket_checkout_selected_ids_v1";
const CHECKOUT_PROMO_KEY = "loyaltymarket_checkout_promo_v1";
const CHECKOUT_RECIPIENT_KEY = "loyaltymarket_checkout_recipient_v1";
const CHECKOUT_CUSTOMS_KEY = "loyaltymarket_checkout_customs_v1";
const CHECKOUT_CARD_KEY = "loyaltymarket_checkout_card_v1";

const CHECKOUT_MODAL_ANIMATION_MS = 240;
const CHECKOUT_MODAL_UNMOUNT_DELAY_MS = CHECKOUT_MODAL_ANIMATION_MS + 30;

function useAnimatedPresence(open: boolean) {
  const [mounted, setMounted] = useState(open);
  const [active, setActive] = useState(false);

  useEffect(() => {
    let frame1 = 0;
    let frame2 = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;

    if (open) {
      frame1 = requestAnimationFrame(() => {
        setMounted(true);
        setActive(false);
        frame2 = requestAnimationFrame(() => setActive(true));
      });
    } else {
      frame1 = requestAnimationFrame(() => setActive(false));
      timer = setTimeout(
        () => setMounted(false),
        CHECKOUT_MODAL_UNMOUNT_DELAY_MS,
      );
    }

    return () => {
      if (frame1) cancelAnimationFrame(frame1);
      if (frame2) cancelAnimationFrame(frame2);
      if (timer) clearTimeout(timer);
    };
  }, [open]);

  return { mounted, active };
}

interface CheckoutRecipient {
  fullName: string;
  phoneDigits: string;
  email: string;
}

interface CheckoutCustomsData {
  passportSeries: string;
  passportNumber: string;
  issueDate: string;
  birthDate: string;
  inn: string;
}

interface CheckoutCardSaved {
  last4: string;
  exp: string;
  holder: string;
}

interface CheckoutCardDraft {
  numberDigits: string;
  exp: string;
  cvc: string;
  holder: string;
}

interface CheckoutCardErrors {
  numberDigits?: string;
  exp?: string;
  cvc?: string;
  holder?: string;
}

interface CheckoutRecipientErrors {
  fullName?: string;
  phoneDigits?: string;
  email?: string;
}

interface CheckoutPromo {
  code: string;
  discountRub: number;
}

function readRecipient() {
  try {
    const raw = localStorage.getItem(CHECKOUT_RECIPIENT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    const x = parsed;
    if (
      typeof x.fullName !== "string" ||
      typeof x.phoneDigits !== "string" ||
      typeof x.email !== "string"
    ) {
      return null;
    }
    return {
      fullName: x.fullName,
      phoneDigits: x.phoneDigits,
      email: x.email,
    };
  } catch {
    return null;
  }
}

function writeRecipient(value: CheckoutRecipient) {
  try {
    localStorage.setItem(CHECKOUT_RECIPIENT_KEY, JSON.stringify(value));
  } catch {}
}

function readCustomsData() {
  try {
    const raw = localStorage.getItem(CHECKOUT_CUSTOMS_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    const x = parsed;
    if (
      typeof x.passportSeries !== "string" ||
      typeof x.passportNumber !== "string" ||
      typeof x.issueDate !== "string" ||
      typeof x.birthDate !== "string" ||
      typeof x.inn !== "string"
    ) {
      return null;
    }
    return {
      passportSeries: x.passportSeries,
      passportNumber: x.passportNumber,
      issueDate: x.issueDate,
      birthDate: x.birthDate,
      inn: x.inn,
    };
  } catch {
    return null;
  }
}

function writeCustomsData(value: CheckoutCustomsData) {
  try {
    localStorage.setItem(CHECKOUT_CUSTOMS_KEY, JSON.stringify(value));
  } catch {}
}

function readCard() {
  try {
    const raw = localStorage.getItem(CHECKOUT_CARD_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    const x = parsed;
    if (
      typeof x.last4 !== "string" ||
      typeof x.exp !== "string" ||
      typeof x.holder !== "string"
    ) {
      return null;
    }
    return {
      last4: x.last4,
      exp: x.exp,
      holder: x.holder,
    };
  } catch {
    return null;
  }
}

function writeCard(value: CheckoutCardSaved) {
  try {
    localStorage.setItem(CHECKOUT_CARD_KEY, JSON.stringify(value));
  } catch {
    // ignore
  }
}

function normalizeCardNumberDigits(input: string) {
  return (input || "").replace(/\D/g, "").slice(0, 19);
}

function formatCardNumber(digits: string) {
  const d = (digits || "").replace(/\D/g, "");
  return d.replace(/(.{4})/g, "$1 ").trim();
}

function normalizeExpiry(value: string) {
  const digits = (value || "").replace(/\D/g, "").slice(0, 4);
  const mm = digits.slice(0, 2);
  const yy = digits.slice(2, 4);
  return yy ? `${mm}/${yy}` : mm;
}

function isValidLuhn(numberDigits: string) {
  const digits = (numberDigits || "").replace(/\D/g, "");
  if (digits.length < 12) return false;
  let sum = 0;
  let shouldDouble = false;
  for (let i = digits.length - 1; i >= 0; i--) {
    let digit = Number(digits[i]);
    if (Number.isNaN(digit)) return false;
    if (shouldDouble) {
      digit *= 2;
      if (digit > 9) digit -= 9;
    }
    sum += digit;
    shouldDouble = !shouldDouble;
  }
  return sum % 10 === 0;
}

function normalizePhoneDigits(input: string) {
  const raw = input || "";
  let digits = raw.replace(/\D/g, "");
  if (!digits) return "";

  // If the user types into our formatted input (which shows "+7 ..."),
  // the extracted digits will start with a leading "7" from the prefix.
  // Strip it so we keep only the 10 digits after +7.
  const hasPlus7Prefix = /^\s*\+7/.test(raw);
  if (hasPlus7Prefix && digits.startsWith("7")) {
    digits = digits.slice(1);
  }

  // Also accept pasted formats: 8XXXXXXXXXX, 7XXXXXXXXXX, +7XXXXXXXXXX.
  if (
    digits.length >= 11 &&
    (digits.startsWith("7") || digits.startsWith("8"))
  ) {
    digits = digits.slice(1);
  }

  return digits.slice(0, 10);
}

function formatPhone(digits10: string) {
  const d = (digits10 || "").replace(/\D/g, "").slice(0, 10);
  if (!d) return "";
  const a = d.slice(0, 3);
  const b = d.slice(3, 6);
  const c = d.slice(6, 8);
  const e = d.slice(8, 10);
  let out = "+7";
  if (a) out += ` ${a}`;
  if (b) out += ` ${b}`;
  if (c) out += `-${c}`;
  if (e) out += `-${e}`;
  return out;
}

function validateCardDraft(draft: CheckoutCardDraft): CheckoutCardErrors {
  const errors: CheckoutCardErrors = {};

  const numberDigits = normalizeCardNumberDigits(draft.numberDigits);
  if (!numberDigits) {
    errors.numberDigits = "required";
  } else if (numberDigits.length < 16 || numberDigits.length > 19) {
    errors.numberDigits = "invalid";
  } else if (!isValidLuhn(numberDigits)) {
    errors.numberDigits = "invalid";
  }

  const exp = normalizeExpiry(draft.exp);
  if (!exp) {
    errors.exp = "required";
  } else if (!/^\d{2}\/\d{2}$/.test(exp)) {
    errors.exp = "invalid";
  } else {
    const [mmStr, yyStr] = exp.split("/");
    const mm = Number(mmStr);
    const yy = Number(yyStr);
    if (mm < 1 || mm > 12 || Number.isNaN(yy)) {
      errors.exp = "invalid";
    }
  }

  const cvc = (draft.cvc || "").replace(/\D/g, "").slice(0, 4);
  if (!cvc) {
    errors.cvc = "required";
  } else if (cvc.length < 3) {
    errors.cvc = "invalid";
  }

  const holder = (draft.holder || "").trim();
  if (!holder) {
    errors.holder = "required";
  } else {
    const ok = /^[A-Za-zА-Яа-яЁё\s-]+$/.test(holder);
    if (!ok || holder.replace(/\s+/g, " ").length < 3) {
      errors.holder = "invalid";
    }
  }

  return errors;
}

function validateRecipient(draft: CheckoutRecipient): CheckoutRecipientErrors {
  const errors: CheckoutRecipientErrors = {};

  const fullName = draft.fullName.trim();
  if (!fullName) {
    errors.fullName = "required";
  } else {
    if (/[A-Za-z]/.test(fullName)) {
      errors.fullName = "invalid";
    } else {
      const parts = fullName.split(/\s+/).filter(Boolean);
      if (parts.length < 2) {
        errors.fullName = "invalid";
      } else {
        const ok = parts.every((p: string) => /^[А-Яа-яЁё-]+$/.test(p));
        if (!ok) errors.fullName = "invalid";
      }
    }
  }

  const phoneDigits = draft.phoneDigits.trim();
  if (!phoneDigits) {
    errors.phoneDigits = "required";
  } else if (phoneDigits.length !== 10 || !phoneDigits.startsWith("9")) {
    errors.phoneDigits = "invalid";
  }

  const email = draft.email.trim();
  if (!email) {
    errors.email = "required";
  } else {
    const ok = /^[^\s@]+@[^\s@]+\.(ru|com)$/i.test(email);
    if (!ok) errors.email = "invalid";
  }

  return errors;
}

function formatRub(value: number) {
  try {
    return `${new Intl.NumberFormat("ru-RU").format(value)} ₽`;
  } catch {
    return `${value} ₽`;
  }
}

function pluralizeItemsRu(count: number) {
  const n = Math.abs(count);
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return "товар";
  if (mod10 >= 2 && mod10 <= 4 && !(mod100 >= 12 && mod100 <= 14))
    return "товара";
  return "товаров";
}

function readSelectedIds(): Set<string | number> {
  try {
    const raw = localStorage.getItem(CHECKOUT_SELECTED_KEY);
    if (!raw) return new Set<string | number>();
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return new Set<string | number>();
    const ids = parsed.filter((x: unknown) => typeof x === "number") as number[];
    return new Set<string | number>(ids);
  } catch {
    return new Set<string | number>();
  }
}

function readPromo(): CheckoutPromo | null {
  try {
    const raw = localStorage.getItem(CHECKOUT_PROMO_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    const x = parsed;
    if (typeof x.code !== "string" || typeof x.discountRub !== "number")
      return null;
    return { code: x.code, discountRub: x.discountRub };
  } catch {
    return null;
  }
}

export default function CheckoutPage() {
  return (
    <Suspense fallback={<div className={styles.c1} />}>
      <CheckoutPageInner />
    </Suspense>
  );
}

function CheckoutPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const searchParamsKey = searchParams.toString();
  const { items } = useCart();

  const pickup = useMemo(() => {
    const params = new URLSearchParams(searchParamsKey);
    const pickupPvzId = params.get("pickupPvzId")?.trim() || null;
    const pickupAddress = params.get("pickupAddress")?.trim() || null;
    const pickupProvider = params.get("pickupProvider")?.trim() || null;
    return { pickupPvzId, pickupAddress, pickupProvider };
  }, [searchParamsKey]);

  const openPickupSelection = useMemo(() => {
    if (pickup.pickupPvzId) {
      return `/checkout/pickup?step=map&pvzId=${encodeURIComponent(
        pickup.pickupPvzId,
      )}`;
    }
    return "/checkout/pickup?step=search";
  }, [pickup.pickupPvzId]);

  const [recipient, setRecipient] = useState<CheckoutRecipient | null>(null);
  const [isRecipientModalOpen, setIsRecipientModalOpen] = useState(false);
  const [recipientDraft, setRecipientDraft] = useState({
    fullName: "",
    phoneDigits: "",
    email: "",
  });
  const [recipientSubmitAttempted, setRecipientSubmitAttempted] =
    useState(false);

  const openRecipientModal = () => {
    setRecipientDraft(
      recipient ?? { fullName: "", phoneDigits: "", email: "" },
    );
    setRecipientSubmitAttempted(false);
    setIsRecipientModalOpen(true);
  };

  const recipientErrors = useMemo(() => {
    if (!recipientSubmitAttempted) return {};
    return validateRecipient(recipientDraft);
  }, [recipientDraft, recipientSubmitAttempted]);

  const [customs, setCustoms] = useState<CheckoutCustomsData | null>(null);
  const [isCustomsModalOpen, setIsCustomsModalOpen] = useState(false);
  const [customsDraft, setCustomsDraft] = useState({
    passportSeries: "",
    passportNumber: "",
    issueDate: "",
    birthDate: "",
    inn: "",
  });

  const openCustomsModal = () => {
    setCustomsDraft(
      customs ?? {
        passportSeries: "",
        passportNumber: "",
        issueDate: "",
        birthDate: "",
        inn: "",
      },
    );
    setIsCustomsModalOpen(true);
  };

  const [card, setCard] = useState<CheckoutCardSaved | null>(null);
  const [isCardModalOpen, setIsCardModalOpen] = useState(false);
  const [cardDraft, setCardDraft] = useState({
    numberDigits: "",
    exp: "",
    cvc: "",
    holder: "",
  });
  const [cardSubmitAttempted, setCardSubmitAttempted] = useState(false);

  const closeCardModal = () => {
    setIsCardModalOpen(false);
    if (!card) {
      setPaymentMethod("sbp");
      setUseSplit(false);
    }
  };

  const openCardModal = () => {
    setCardDraft({
      numberDigits: "",
      exp: card?.exp ?? "",
      cvc: "",
      holder: card?.holder ?? "",
    });
    setCardSubmitAttempted(false);
    setIsCardModalOpen(true);
  };

  const [deliveryMode] = useState("pickup");
  const [usePoints, setUsePoints] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState("sbp");
  const [useSplit, setUseSplit] = useState(false);
  const [isSplitSheetOpen, setIsSplitSheetOpen] = useState(false);

  const recipientSheet = useAnimatedPresence(isRecipientModalOpen);
  const customsSheet = useAnimatedPresence(isCustomsModalOpen);
  const cardSheet = useAnimatedPresence(isCardModalOpen);

  const [selectedIds, setSelectedIds] = useState<Set<string | number>>(() => new Set());
  const [promo, setPromo] = useState<CheckoutPromo | null>(null);

  // Hydrate client-only state after mount to avoid SSR/CSR text mismatches.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    setRecipient(readRecipient());
    setCustoms(readCustomsData());
    setCard(readCard());
    setSelectedIds(readSelectedIds());
    setPromo(readPromo());
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  const cardErrors = useMemo(() => {
    if (!cardSubmitAttempted) return {};
    return validateCardDraft(cardDraft);
  }, [cardDraft, cardSubmitAttempted]);

  const selectedItems = useMemo(() => {
    if (selectedIds.size === 0) return [];
    return items.filter((x) => selectedIds.has(x.id));
  }, [items, selectedIds]);

  const { selectedQuantity, selectedSubtotalRub } = useMemo(() => {
    let qty = 0;
    let sum = 0;
    for (const x of selectedItems) {
      qty += x.quantity;
      const line = Number(x?.lineTotalRub);
      if (Number.isFinite(line)) sum += line;
      else sum += (x.priceRub ?? x.price) * x.quantity;
    }
    return { selectedQuantity: qty, selectedSubtotalRub: sum };
  }, [selectedItems]);

  const groupedByDelivery = useMemo(() => {
    const map = new Map<string, typeof selectedItems>();
    for (const x of selectedItems) {
      const key = x.deliveryText || "";
      const bucket = map.get(key);
      if (bucket) bucket.push(x);
      else map.set(key, [x]);
    }
    return Array.from(map.entries());
  }, [selectedItems]);

  const deliveryPriceText = deliveryMode === "pickup" ? "от 99₽" : "—";
  const deliveryBulletText =
    deliveryMode === "pickup" ? "Доставка в пункт выдачи" : "Доставка курьером";

  const discountRub = selectedQuantity > 0 ? (promo?.discountRub ?? 0) : 0;
  const pointsRub = selectedQuantity > 0 && usePoints ? 200 : 0;
  const totalRub = Math.max(0, selectedSubtotalRub - discountRub - pointsRub);

  const payButtonTitle = useSplit
    ? "Оформить сплит"
    : paymentMethod === "sbp"
      ? "Оплатить через СБП"
      : "Оплатить картой";

  const payButtonSuffix =
    paymentMethod === "card" && card?.last4 ? `…${card.last4}` : "";

  const splitPayment = useMemo(
    () => ({ count: 4, amount: "880", text: "без переплаты" }),
    [],
  );

  return (
    <div className={styles.c2}>
      <div className={styles.c3}>
        <h1 className={styles.c4}>Оформление заказа</h1>

        <div className={cn(styles.c5, styles.tw1)}>
          <button
            type="button"
            onClick={() => router.push(openPickupSelection)}
            className={cn(styles.c6, styles.tw2)}
          >
            <div className={styles.c7}>Пункт выдачи</div>
            {pickup.pickupAddress ? (
              <div className={cn(styles.c8)}>
                {pickup.pickupProvider
                  ? `${pickup.pickupProvider} — ${pickup.pickupAddress}`
                  : pickup.pickupAddress}
              </div>
            ) : null}
            <div className={styles.c9}>{deliveryPriceText}</div>
          </button>
          <div className={styles.c10}>
            <div className={styles.c11}>Курьером</div>
            <div className={styles.c12}>Нет курьерской доставки</div>
          </div>
        </div>

        <div className={styles.c13}>
          <div className={styles.c14}>
            <button
              type="button"
              onClick={() => router.push(openPickupSelection)}
              className={cn(styles.c15)}
            >
              <div className={cn(styles.c16, styles.tw3)}>
                <img
                  src="/icons/global/location.svg"
                  alt="location"
                  className={cn(styles.c17, styles.tw4)}
                />
                <div>
                  <div className={styles.c18}>Пункт выдачи</div>
                  <div className={styles.c19}>
                    {pickup.pickupAddress ?? "Не выбран"}
                  </div>
                </div>
              </div>
              <img
                src="/icons/global/small-arrow.svg"
                alt=""
                className={cn(styles.c20, styles.tw5)}
              />
            </button>

            <button
              type="button"
              onClick={openRecipientModal}
              className={cn(styles.c21)}
            >
              <div className={cn(styles.c22, styles.tw6)}>
                <img
                  src="/icons/global/user.svg"
                  alt="location"
                  className={cn(styles.c23, styles.tw7)}
                />
                <div>
                  <div className={styles.c24}>Получатель</div>
                  <div className={styles.c25}>
                    {recipient?.fullName?.trim()
                      ? recipient.fullName
                      : "Не указан"}
                  </div>
                </div>
              </div>
              <img
                src="/icons/global/small-arrow.svg"
                alt=""
                className={cn(styles.c26, styles.tw8)}
              />
            </button>

            <button
              type="button"
              onClick={openCustomsModal}
              className={styles.c27}
            >
              <div className={cn(styles.c28, styles.tw9)}>
                <img
                  src="/icons/global/personalCard.svg"
                  alt="location"
                  className={cn(styles.c29, styles.tw10)}
                />
                <div>
                  <div className={styles.c30}>Данные для таможни</div>
                  <div className={styles.c31}>Паспорт и ИНН</div>
                </div>
              </div>
              <img
                src="/icons/global/small-arrow.svg"
                alt=""
                className={cn(styles.c32, styles.tw11)}
              />
            </button>
          </div>

          {selectedQuantity === 0 ? (
            <div className={styles.c33}>
              <div className={styles.c34}>Выберите товары</div>
              <button
                type="button"
                onClick={() => router.push("/trash")}
                className={cn(styles.c35, styles.tw12)}
              >
                Вернуться в корзину
              </button>
            </div>
          ) : (
            <div className={cn(styles.c36, styles.spaceY2)}>
              {groupedByDelivery.map(([deliveryText, groupItems]) => {
                const first = groupItems[0];
                return (
                  <div
                    key={deliveryText}
                    className={cn(styles.c37, styles.spaceY14)}
                  >
                    <div className={styles.c38}>
                      <div className={cn(styles.c39, styles.tw13)}>
                        <span className={cn(styles.c40, styles.tw14)} />
                        <div>
                          <span className={styles.c41}>{deliveryText}</span>
                          <div className={styles.c42}>
                            В пункт выдачи {deliveryPriceText}
                          </div>
                          {first?.shippingText?.trim() ? (
                            <div className={styles.c43}>
                              {first.shippingText}
                            </div>
                          ) : null}
                        </div>
                      </div>
                    </div>

                    {groupItems.map((x) => (
                      <div key={x.id} className={cn(styles.c44, styles.tw15)}>
                        <div className={cn(styles.c45, styles.tw16)}>
                          <img
                            src={x.image}
                            alt={x.name}
                            className={styles.c46}
                          />
                        </div>
                        <div className={cn(styles.c47, styles.tw17)}>
                          <div className={styles.c48}>{x.name}</div>
                          <div className={styles.c49}>
                            {x.size && (
                              <>
                                Размер:{" "}
                                <span className={styles.c50}>{x.size}</span>
                              </>
                            )}
                            {x.article && (
                              <>
                                {x.size && " · "}Артикул:{" "}
                                <span className={styles.c51}>{x.article}</span>
                              </>
                            )}
                          </div>
                          <div className={styles.c52}>
                            {formatRub(x.priceRub ?? x.price)}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          )}

          <div className={styles.c53}>
            <div
              className={cn(
                styles.c54,
                card ? styles.paymentGrid3 : styles.tw18,
              )}
            >
              <button
                type="button"
                aria-pressed={paymentMethod === "sbp"}
                onClick={() => {
                  setUseSplit(false);
                  setPaymentMethod("sbp");
                }}
                className={cn(
                  styles.paymentOption,
                  styles.paymentOptionSbp,
                  paymentMethod === "sbp"
                    ? styles.paymentOptionSelected
                    : styles.paymentOptionUnselectedSbp,
                )}
              >
                <span className={cn(styles.c55, styles.tw19)}>
                  <img
                    src="/icons/global/cbp.png"
                    alt=""
                    className={cn(styles.c56)}
                  />
                </span>
                <span className={styles.c57}>СБП</span>
              </button>

              {card ? (
                <button
                  type="button"
                  aria-pressed={paymentMethod === "card"}
                  onClick={() => setPaymentMethod("card")}
                  className={cn(
                    styles.paymentOption,
                    styles.paymentOptionSavedCard,
                    paymentMethod === "card"
                      ? styles.paymentOptionSelected
                      : styles.paymentOptionUnselectedCard,
                  )}
                >
                  <span className={styles.cardBadge}>
                    <img src="/img/tbanklogo.png" alt="tbanklogo" />
                  </span>
                  <span className={styles.savedCardText}>•• {card.last4}</span>
                </button>
              ) : (
                <button
                  type="button"
                  aria-pressed={paymentMethod === "card"}
                  onClick={() => {
                    setPaymentMethod("card");
                    openCardModal();
                  }}
                  className={cn(
                    styles.paymentOption,
                    styles.paymentOptionAddCard,
                    paymentMethod === "card"
                      ? styles.paymentOptionSelected
                      : styles.paymentOptionUnselectedCard,
                  )}
                >
                  <span className={styles.addCardPlus}>+</span>
                  <span className={styles.addCardText}>Добавить карту</span>
                </button>
              )}

              {card ? (
                <button
                  type="button"
                  aria-label="Добавить карту"
                  onClick={() => {
                    setPaymentMethod("card");
                    openCardModal();
                  }}
                  className={cn(
                    styles.paymentOption,
                    styles.paymentOptionAddCard,
                    styles.paymentOptionUnselectedCard,
                  )}
                >
                  <span className={styles.addCardPlus}>+</span>
                  <span className={styles.addCardText}>Добавить карту</span>
                </button>
              ) : null}
            </div>

            <div className={cn(styles.c60, styles.spaceY2)}>
              <div className={styles.c61}>
                <span>
                  {selectedQuantity} {pluralizeItemsRu(selectedQuantity)}
                </span>
                <span className={styles.c62}>
                  {formatRub(selectedSubtotalRub)}
                </span>
              </div>

              <div className={styles.c63}>
                <span className={cn(styles.c64, styles.tw20)}>
                  <span>Скидка</span>
                  <img
                    src="/icons/global/small-arrow.svg"
                    alt=""
                    className={cn(styles.c65, styles.tw21)}
                  />
                </span>
                <span>
                  {discountRub > 0 ? `-${formatRub(discountRub)}` : "0 ₽"}
                </span>
              </div>
              {discountRub > 0 && promo ? (
                <div className={styles.c66}>
                  <span className={styles.c67}>• Промокод {promo.code}</span>
                  <span>-{formatRub(discountRub)}</span>
                </div>
              ) : null}

              <div className={styles.c68}>
                <span className={cn(styles.c69, styles.tw22)}>
                  <span>Доставка</span>
                  <img
                    src="/icons/global/small-arrow.svg"
                    alt=""
                    className={cn(styles.c70, styles.tw23)}
                  />
                </span>
                <span>{deliveryPriceText}</span>
              </div>
              <div className={styles.c71}>
                <span className={styles.c72}>• {deliveryBulletText}</span>
                <span>{deliveryPriceText}</span>
              </div>

              <div className={styles.c73}>
                <span className={styles.c74}>Списать баллы</span>
                <div className={cn(styles.c75, styles.tw24)}>
                  <span className={styles.c76}>
                    {usePoints ? `-${formatRub(200)}` : ""}
                  </span>
                  <button
                    type="button"
                    aria-label="Списать баллы"
                    onClick={() => setUsePoints((v) => !v)}
                    className={cn(
                      styles.toggle,
                      usePoints ? styles.toggleOn : styles.toggleOff,
                    )}
                  >
                    <span
                      className={cn(
                        styles.toggleThumb,
                        usePoints
                          ? styles.toggleThumbOn
                          : styles.toggleThumbOff,
                      )}
                    />
                  </button>
                </div>
              </div>

              <div className={styles.c77}>
                <span className={styles.c78}>Итого</span>
                <span className={styles.c79}>{formatRub(totalRub)}</span>
              </div>
            </div>
          </div>

          <div className={styles.c80}>
            <div className={styles.c81}>
              <div className={styles.c82}>
                <div className={cn(styles.c83, styles.tw25)}>
                  <div className={cn(styles.c84, styles.tw26)}>
                    <img
                      src="/icons/global/split.svg"
                      alt=""
                      className={cn(styles.c85, styles.tw27)}
                    />
                    <div className={cn(styles.c86, styles.tw28)}>
                      <div className={styles.c87}>4×880₽ в сплит</div>
                      <div className={styles.c88}>
                        На 2 месяца без переплаты
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    aria-label="Включить сплит"
                    aria-pressed={useSplit}
                    onClick={() => {
                      setUseSplit((prev) => {
                        const next = !prev;
                        if (next) {
                          setPaymentMethod("card");
                          if (!card) openCardModal();
                        }
                        return next;
                      });
                    }}
                    className={cn(
                      styles.toggle,
                      useSplit ? styles.toggleOn : styles.toggleOff,
                    )}
                  >
                    <span
                      className={cn(
                        styles.toggleThumb,
                        useSplit ? styles.toggleThumbOn : styles.toggleThumbOff,
                      )}
                    />
                  </button>
                </div>

                <div className={styles.c89}>
                  <span>Сегодня</span>
                  <span>Ещё 3 платежа раз в 2 недели</span>
                </div>
                <div className={cn(styles.c90, styles.tw29)}>
                  <div className={cn(styles.c91, styles.tw30)} />
                  <div className={cn(styles.c92, styles.tw31)} />
                  <div className={cn(styles.c93, styles.tw32)} />
                  <div className={cn(styles.c94, styles.tw33)} />
                </div>
              </div>
            </div>
          </div>

          <div>
            <div className={styles.c95}>
              <button
                type="button"
                disabled={selectedQuantity === 0}
                onClick={() => {
                  if (selectedQuantity === 0) return;
                  if (useSplit) {
                    setIsSplitSheetOpen(true);
                    return;
                  }
                }}
                className={`${cn(
                  styles.payButton,
                  selectedQuantity > 0
                    ? styles.payButtonEnabled
                    : styles.payButtonDisabled,
                )} ${paymentMethod === "sbp" ? `${styles.paymentMethodSbp}` : ""}`}
              >
                <span className={styles.payButtonSide} />
                <span className={styles.payButtonLabel}>{payButtonTitle}</span>
                <span className={`${styles.payButtonSide}`}>
                  {paymentMethod === "sbp" ? (
                    <img
                      src="/icons/global/cbp.png"
                      alt=""
                      className={cn(styles.c96, styles.tw34)}
                    />
                  ) : payButtonSuffix ? (
                    <span className={styles.payButtonSuffix}>
                      {payButtonSuffix}
                    </span>
                  ) : null}
                </span>
              </button>

              <SplitPaymentSheet
                open={isSplitSheetOpen}
                onClose={() => setIsSplitSheetOpen(false)}
                price={formatRub(totalRub)}
                splitPayment={splitPayment}
              />

              <div className={cn(styles.c97, styles.tw35)}>
                <img src="/icons/global/security.svg" alt="" />{" "}
                <span>Безопасное оформление заказа</span>
              </div>

              <div className={cn(styles.c98, styles.tw36)}>
                Нажимая «{payButtonTitle}
                », вы принимаете условия{" "}
                <a href="#" className={styles.c99}>
                  публичной оферты
                </a>
                ,{" "}
                <a href="#" className={styles.c100}>
                  пользовательского соглашения
                </a>{" "}
                и даете согласие на{" "}
                <a href="#" className={styles.c101}>
                  обработку персональных данных
                </a>
                .
              </div>
            </div>
          </div>
        </div>
      </div>

      {recipientSheet.mounted ? (
        <div className={styles.c102} style={{ zIndex: 2500 }}>
          <button
            type="button"
            aria-label="Закрыть"
            onClick={() => setIsRecipientModalOpen(false)}
            className={cn(
              styles.c103,
              recipientSheet.active
                ? styles.checkoutModalBackdropOpen
                : styles.checkoutModalBackdropClosed,
            )}
          />

          <div
            className={cn(
              styles.c104,
              styles.checkoutModalSheet,
              recipientSheet.active
                ? styles.checkoutModalSheetOpen
                : styles.checkoutModalSheetClosed,
            )}
          >
            <div className={styles.c105}>
              <div className={styles.c106}>
                <div className={cn(styles.c107, styles.tw38)} />
              </div>

              <div className={styles.c108}>
                <div className={cn(styles.c109, styles.tw39)}>
                  <div className={cn(styles.c110)}>Получатель</div>
                  <button
                    type="button"
                    aria-label="Закрыть"
                    onClick={() => setIsRecipientModalOpen(false)}
                    className={cn(styles.c111, styles.tw40)}
                  >
                    <img
                      src="/icons/global/xiconBlack.svg"
                      alt=""
                      className={cn(styles.c112, styles.tw41)}
                    />
                  </button>
                </div>

                <div className={cn(styles.c113, styles.tw42)}>
                  <img
                    src="/icons/global/Info.svg"
                    alt=""
                    className={cn(styles.c114, styles.tw43)}
                  />
                  <div className={styles.c115}>
                    <div className={styles.c116}>
                      Указывайте настоящие данные
                    </div>
                    <div className={styles.c117}>
                      При заказа потребуется паспорт
                    </div>
                  </div>
                </div>

                <div
                  className={`${cn(styles.c118, styles.spaceY3)} ${recipientErrors.fullName === "invalid" ? `${styles.spaceY3Error}` : ""} ${recipientErrors.phoneDigits === "invalid" ? `${styles.spaceY3Error}` : ""} ${recipientErrors.email === "invalid" ? `${styles.spaceY3Error}` : ""}`}
                >
                  <div>
                    <input
                      value={recipientDraft.fullName}
                      onChange={(e) =>
                        setRecipientDraft((v) => ({
                          ...v,
                          fullName: e.target.value,
                        }))
                      }
                      placeholder="ФИО"
                      className={cn(
                        styles.textInput,
                        recipientErrors.fullName
                          ? styles.textInputError
                          : styles.textInputNormal,
                      )}
                    />
                    {recipientSubmitAttempted &&
                    recipientDraft.fullName.trim() &&
                    recipientErrors.fullName === "invalid" ? (
                      <div className={styles.c119}>ФИ неверный формат</div>
                    ) : null}
                  </div>

                  <div>
                    <input
                      value={formatPhone(recipientDraft.phoneDigits)}
                      onChange={(e) => {
                        const el = e.target;
                        const selectionStart = el.selectionStart;
                        const selectionEnd = el.selectionEnd;

                        // Prevent "overflow" typing: once we have 10 digits after +7,
                        // extra typed digits should be ignored (not shift/replace existing).
                        const raw = el.value || "";
                        let rawDigits = raw.replace(/\D/g, "");
                        const hasPlus7Prefix = /^\s*\+7/.test(raw);
                        if (hasPlus7Prefix && rawDigits.startsWith("7")) {
                          rawDigits = rawDigits.slice(1);
                        }
                        if (
                          rawDigits.length >= 11 &&
                          (rawDigits.startsWith("7") ||
                            rawDigits.startsWith("8"))
                        ) {
                          rawDigits = rawDigits.slice(1);
                        }

                        const isSelectionCollapsed =
                          selectionStart != null &&
                          selectionEnd != null &&
                          selectionStart === selectionEnd;

                        if (
                          recipientDraft.phoneDigits.length >= 10 &&
                          rawDigits.length > 10 &&
                          isSelectionCollapsed
                        ) {
                          return;
                        }

                        const next = normalizePhoneDigits(raw);
                        setRecipientDraft((v) => ({ ...v, phoneDigits: next }));
                      }}
                      inputMode="tel"
                      placeholder="Телефон"
                      className={cn(
                        styles.textInput,
                        recipientErrors.phoneDigits
                          ? styles.textInputError
                          : styles.textInputNormal,
                      )}
                    />
                    {recipientSubmitAttempted &&
                    recipientDraft.phoneDigits.trim() &&
                    recipientErrors.phoneDigits === "invalid" ? (
                      <div className={styles.c120}>
                        Укажите телефон в формате +7 9XX XXX-XX-XX
                      </div>
                    ) : null}
                  </div>

                  <div>
                    <input
                      value={recipientDraft.email}
                      onChange={(e) =>
                        setRecipientDraft((v) => ({
                          ...v,
                          email: e.target.value,
                        }))
                      }
                      inputMode="email"
                      placeholder="Электронная почта"
                      className={cn(
                        styles.textInput,
                        recipientErrors.email
                          ? styles.textInputError
                          : styles.textInputNormal,
                      )}
                    />
                    {recipientSubmitAttempted &&
                    recipientDraft.email.trim() &&
                    recipientErrors.email === "invalid" ? (
                      <div className={styles.c121}>Неверный формат</div>
                    ) : null}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setRecipientSubmitAttempted(true);
                    const errs = validateRecipient(recipientDraft);
                    if (Object.keys(errs).length > 0) return;

                    const next = {
                      fullName: recipientDraft.fullName.trim(),
                      phoneDigits: normalizePhoneDigits(
                        recipientDraft.phoneDigits,
                      ),
                      email: recipientDraft.email.trim(),
                    };

                    setRecipient(next);
                    writeRecipient(next);
                    setIsRecipientModalOpen(false);
                  }}
                  className={cn(styles.c122, styles.tw44)}
                >
                  Сохранить
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {customsSheet.mounted ? (
        <div className={styles.c123} style={{ zIndex: 2500 }}>
          <button
            type="button"
            aria-label="Закрыть"
            onClick={() => setIsCustomsModalOpen(false)}
            className={cn(
              styles.c124,
              customsSheet.active
                ? styles.checkoutModalBackdropOpen
                : styles.checkoutModalBackdropClosed,
            )}
          />

          <div
            className={cn(
              styles.c125,
              styles.checkoutModalSheet,
              customsSheet.active
                ? styles.checkoutModalSheetOpen
                : styles.checkoutModalSheetClosed,
            )}
          >
            <div className={styles.c126}>
              <div className={styles.c127}>
                <div className={cn(styles.c128, styles.tw46)} />
              </div>

              <div className={styles.c129}>
                <div className={cn(styles.c130, styles.tw47)}>
                  <div className={cn(styles.c131)}>Данные для таможни</div>
                </div>
                <button
                  type="button"
                  aria-label="Закрыть"
                  onClick={() => setIsCustomsModalOpen(false)}
                  className={cn(styles.c132, styles.tw48)}
                >
                  <img
                    src="/icons/global/xiconBlack.svg"
                    alt=""
                    className={cn(styles.c133, styles.tw49)}
                  />
                </button>

                <div className={styles.c134}>
                  <div>
                    Данные нужны при декларировании товаров из-за рубежа. Все
                    товары оформляются на таможне согласно приказу
                    <span> ФТС от 05.07.2018 № 1060</span>
                  </div>
                  <div className={styles.c135}>
                    Мы соблюдаем таможенное законодательство и передаем
                    паспортные данные и ИНН получателя в защищенном виде
                  </div>
                  <button type="button" className={styles.c136}>
                    Подробнее
                  </button>
                </div>

                <div className={cn(styles.c137, styles.tw50)}>
                  <img
                    src="/icons/global/Info.svg"
                    alt=""
                    className={cn(styles.c138, styles.tw51)}
                  />
                  <div className={styles.c139}>
                    <div className={styles.c140}>
                      Указывайте настоящие данные
                    </div>
                    <div className={styles.c141}>
                      При таможенном оформлении неверные <br /> данные приведут
                      к отказу в пропуске товара
                    </div>
                  </div>
                </div>

                <div className={cn(styles.c142, styles.spaceY3)}>
                  <div className={cn(styles.c143, styles.tw52)}>
                    <input
                      value={customsDraft.passportSeries}
                      onChange={(e) => {
                        const next = (e.target.value || "")
                          .replace(/[^0-9A-Za-zА-Яа-яЁё]/g, "")
                          .toUpperCase()
                          .slice(0, 10);
                        setCustomsDraft((v) => ({
                          ...v,
                          passportSeries: next,
                        }));
                      }}
                      inputMode="text"
                      autoCapitalize="characters"
                      spellCheck={false}
                      maxLength={10}
                      placeholder="Серия"
                      className={cn(styles.c144, styles.tw53)}
                    />
                    <input
                      value={customsDraft.passportNumber}
                      onChange={(e) => {
                        const next = (e.target.value || "")
                          .replace(/\D/g, "")
                          .slice(0, 6);
                        setCustomsDraft((v) => ({
                          ...v,
                          passportNumber: next,
                        }));
                      }}
                      inputMode="numeric"
                      placeholder="Номер"
                      className={cn(styles.c145, styles.tw54)}
                    />
                  </div>

                  <input
                    value={customsDraft.issueDate}
                    onChange={(e) => {
                      const next = (e.target.value || "")
                        .replace(/[^0-9.]/g, "")
                        .slice(0, 10);
                      setCustomsDraft((v) => ({ ...v, issueDate: next }));
                    }}
                    inputMode="numeric"
                    placeholder="Дата выдачи"
                    className={cn(styles.c146, styles.tw55)}
                  />

                  <input
                    value={customsDraft.birthDate}
                    onChange={(e) => {
                      const next = (e.target.value || "")
                        .replace(/[^0-9.]/g, "")
                        .slice(0, 10);
                      setCustomsDraft((v) => ({ ...v, birthDate: next }));
                    }}
                    inputMode="numeric"
                    placeholder="Дата рождения"
                    className={cn(styles.c147, styles.tw56)}
                  />

                  <div>
                    <input
                      value={customsDraft.inn}
                      onChange={(e) => {
                        const next = (e.target.value || "")
                          .replace(/\D/g, "")
                          .slice(0, 12);
                        setCustomsDraft((v) => ({ ...v, inn: next }));
                      }}
                      inputMode="numeric"
                      placeholder="ИНН"
                      className={cn(styles.c148, styles.tw57)}
                    />
                    <img src="/icons/global/InfoGrey.svg" alt="" />
                    <button type="button" className={styles.c149}>
                      Узнать свой ИНН на Госуслугах
                    </button>
                  </div>
                </div>

                <div className={cn(styles.c150, styles.tw58)}>
                  <img
                    src="/icons/global/security.svg"
                    alt=""
                    className={cn(styles.c151, styles.tw59)}
                  />
                  <span>Данные хранятся и передаются в защищенном виде</span>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    const next = {
                      passportSeries: customsDraft.passportSeries.trim(),
                      passportNumber: customsDraft.passportNumber.trim(),
                      issueDate: customsDraft.issueDate.trim(),
                      birthDate: customsDraft.birthDate.trim(),
                      inn: customsDraft.inn.trim(),
                    };
                    setCustoms(next);
                    writeCustomsData(next);
                    setIsCustomsModalOpen(false);
                  }}
                  className={cn(styles.c152, styles.tw60)}
                >
                  Сохранить
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {cardSheet.mounted ? (
        <div className={styles.c153} style={{ zIndex: 2500 }}>
          <button
            type="button"
            aria-label="Закрыть"
            onClick={closeCardModal}
            className={cn(
              styles.c154,
              cardSheet.active
                ? styles.checkoutModalBackdropOpen
                : styles.checkoutModalBackdropClosed,
            )}
          />

          <div
            className={cn(
              styles.c155,
              styles.checkoutModalSheet,
              cardSheet.active
                ? styles.checkoutModalSheetOpen
                : styles.checkoutModalSheetClosed,
            )}
          >
            <div className={styles.c156}>
              <div className={styles.c157}>
                <div className={cn(styles.c158, styles.tw62)} />
              </div>

              <div className={styles.c159}>
                <div className={cn(styles.c160, styles.tw63)}>
                  <div className={cn(styles.c161)}>Добавить карту</div>
                  <button
                    type="button"
                    aria-label="Закрыть"
                    onClick={closeCardModal}
                    className={cn(styles.c162, styles.tw64)}
                  >
                    <img
                      src="/icons/global/xicon.svg"
                      alt=""
                      className={cn(styles.c163, styles.tw65)}
                    />
                  </button>
                </div>

                <div className={styles.c164}>
                  CVV-код не сохраняется и не хранится.
                </div>

                <div className={cn(styles.c165, styles.spaceY3)}>
                  <div>
                    <input
                      value={formatCardNumber(cardDraft.numberDigits)}
                      onChange={(e) => {
                        const next = normalizeCardNumberDigits(e.target.value);
                        setCardDraft((v) => ({ ...v, numberDigits: next }));
                      }}
                      inputMode="numeric"
                      placeholder="Номер карты"
                      className={cn(
                        styles.textInput,
                        cardErrors.numberDigits
                          ? styles.textInputError
                          : styles.textInputNormal,
                      )}
                    />
                    {cardSubmitAttempted &&
                    cardDraft.numberDigits.trim() &&
                    cardErrors.numberDigits === "invalid" ? (
                      <div className={styles.c166}>Проверьте номер карты</div>
                    ) : null}
                  </div>

                  <div className={cn(styles.c167, styles.tw66)}>
                    <div>
                      <input
                        value={normalizeExpiry(cardDraft.exp)}
                        onChange={(e) => {
                          const next = normalizeExpiry(e.target.value);
                          setCardDraft((v) => ({ ...v, exp: next }));
                        }}
                        inputMode="numeric"
                        placeholder="MM/YY"
                        className={cn(
                          styles.textInput,
                          cardErrors.exp
                            ? styles.textInputError
                            : styles.textInputNormal,
                        )}
                      />
                      {cardSubmitAttempted &&
                      cardDraft.exp.trim() &&
                      cardErrors.exp === "invalid" ? (
                        <div className={styles.c168}>Неверный срок</div>
                      ) : null}
                    </div>

                    <div>
                      <input
                        value={(cardDraft.cvc || "")
                          .replace(/\D/g, "")
                          .slice(0, 4)}
                        onChange={(e) => {
                          const next = (e.target.value || "")
                            .replace(/\D/g, "")
                            .slice(0, 4);
                          setCardDraft((v) => ({ ...v, cvc: next }));
                        }}
                        inputMode="numeric"
                        placeholder="CVV"
                        className={cn(
                          styles.textInput,
                          cardErrors.cvc
                            ? styles.textInputError
                            : styles.textInputNormal,
                        )}
                      />
                      {cardSubmitAttempted &&
                      cardDraft.cvc.trim() &&
                      cardErrors.cvc === "invalid" ? (
                        <div className={styles.c169}>Минимум 3 цифры</div>
                      ) : null}
                    </div>
                  </div>

                  <div>
                    <input
                      value={cardDraft.holder}
                      onChange={(e) => {
                        const next = (e.target.value || "")
                          .replace(/\s+/g, " ")
                          .toUpperCase();
                        setCardDraft((v) => ({ ...v, holder: next }));
                      }}
                      inputMode="text"
                      autoCapitalize="characters"
                      spellCheck={false}
                      placeholder="Имя владельца"
                      className={cn(
                        styles.textInput,
                        cardErrors.holder
                          ? styles.textInputError
                          : styles.textInputNormal,
                      )}
                    />
                    {cardSubmitAttempted &&
                    cardDraft.holder.trim() &&
                    cardErrors.holder === "invalid" ? (
                      <div className={styles.c170}>
                        Укажите имя латиницей или кириллицей
                      </div>
                    ) : null}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setCardSubmitAttempted(true);
                    const errs = validateCardDraft(cardDraft);
                    if (Object.keys(errs).length > 0) return;

                    const numberDigits = normalizeCardNumberDigits(
                      cardDraft.numberDigits,
                    );
                    const exp = normalizeExpiry(cardDraft.exp);
                    const holder = cardDraft.holder.trim();

                    const next = {
                      last4: numberDigits.slice(-4),
                      exp,
                      holder,
                    };

                    setCard(next);
                    writeCard(next);
                    setPaymentMethod("card");
                    setIsCardModalOpen(false);
                  }}
                  className={cn(styles.c171, styles.tw67)}
                >
                  Сохранить
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
