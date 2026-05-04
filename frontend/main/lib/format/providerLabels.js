/**
 * Logistics provider code → human label mapping.
 *
 * Spec: SPEC - Frontend Integration Guide §11 — backend "provider_label"
 * yubormaydi, mapping faqat frontend tarafda.
 */

const PROVIDER_LABELS = Object.freeze({
  cdek: "CDEK",
  yandex_delivery: "Яндекс Доставка",
});

const DELIVERY_TYPE_LABELS = Object.freeze({
  courier: "Курьер",
  pickup_point: "Пункт выдачи",
  post_office: "Почтовое отделение",
});

const PICKUP_POINT_TYPE_LABELS = Object.freeze({
  pvz: "ПВЗ",
  postamat: "Постамат",
  post_office: "Почтовое отделение",
  terminal: "Терминал",
});

export function providerLabel(code) {
  if (typeof code !== "string") return "";
  return PROVIDER_LABELS[code] ?? code;
}

export function deliveryTypeLabel(code) {
  if (typeof code !== "string") return "";
  return DELIVERY_TYPE_LABELS[code] ?? code;
}

export function pickupPointTypeLabel(code) {
  if (typeof code !== "string") return "";
  return PICKUP_POINT_TYPE_LABELS[code] ?? code;
}
