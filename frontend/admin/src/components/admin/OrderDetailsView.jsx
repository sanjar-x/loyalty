'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useMemo, useState } from 'react';
import { cn, formatCurrency, formatDateTime } from '@/lib/utils';
import { CopyMark } from '@/components/ui/CopyMark';
import { OrderStatusModal } from './OrderStatusModal';

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const STATUS_TITLE = {
  placed: 'Оформлен',
  in_transit: 'В пути',
  pickup_point: 'В пункте выдачи',
  canceled: 'Отменен',
  received: 'Получен',
};

const ITEM_STATUS_META = {
  placed: {
    label: 'Оформлен',
    className: 'bg-white text-[#111111]',
    dotClassName: 'border-[#8f8f8f]',
  },
  in_transit: {
    label: 'В пути',
    className: 'bg-white text-[#111111]',
    dotClassName: 'border-[#4eaa1e]',
  },
  in_transit_alert: {
    label: 'В пути',
    className: 'bg-white text-[#111111]',
    dotClassName: 'border-[#cf4444]',
  },
  pickup_point: {
    label: 'В пункте выдачи',
    className: 'bg-white text-[#111111]',
    dotClassName: 'border-[#8f8f8f]',
  },
  canceled: {
    label: 'Отменен',
    className: 'bg-[#cdcdcd] text-[#202020]',
  },
  received: {
    label: 'Получен',
    className: 'bg-white text-[#111111]',
    dotClassName: 'border-[#8f8f8f]',
  },
};

/* ------------------------------------------------------------------ */
/*  Icons                                                              */
/* ------------------------------------------------------------------ */

/* CopyMark imported from @/components/ui/CopyMark */

function PinIcon() {
  return (
    <svg width="26" height="26" viewBox="0 0 26 26" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M11.9307 1.09888C12.7666 1.0122 13.136 1.01064 13.9424 1.09106C15.8442 1.28073 17.7063 2.00409 19.208 3.13794C19.8405 3.61558 20.8143 4.62544 21.292 5.29907C22.1127 6.4565 22.7012 7.81151 23.0146 9.26001C23.1058 9.68118 23.1503 10.4045 23.1504 11.1165C23.1505 11.8285 23.1065 12.553 23.0156 12.9768C22.4426 15.6472 20.795 18.2861 17.9658 21.1038C17.2925 21.7743 16.3475 22.6485 15.5244 23.3772C15.1128 23.7416 14.7306 24.071 14.4277 24.3206C14.2766 24.4451 14.1441 24.5506 14.0371 24.6311C13.9337 24.7089 13.8435 24.7713 13.7822 24.801C13.3092 25.0307 12.6493 25.0228 12.1895 24.7805C12.0713 24.7183 11.8381 24.54 11.5488 24.302C11.2537 24.0592 10.8854 23.7422 10.4883 23.3909C9.69405 22.6882 8.78153 21.8441 8.10449 21.1721C5.22286 18.3122 3.56143 15.6661 2.98438 12.9768C2.89348 12.553 2.84947 11.8285 2.84961 11.1165C2.84975 10.4045 2.8942 9.68118 2.98535 9.26001C3.29912 7.8101 3.89012 6.44584 4.69629 5.31665C5.19079 4.62409 6.16691 3.60874 6.79199 3.13794C8.25082 2.03931 10.1566 1.2829 11.9307 1.09888ZM14.6357 2.91431C14.006 2.78659 12.6824 2.73266 12.0254 2.80786C10.0774 3.03101 8.25922 3.94356 6.86914 5.39771C5.64106 6.68265 4.89833 8.18434 4.61816 9.94751C4.56549 10.2792 4.54232 10.7789 4.54883 11.2747C4.55536 11.7712 4.59123 12.2492 4.65137 12.5393C5.13399 14.8656 6.46233 17.0445 9.00391 19.6389C9.53034 20.1763 10.465 21.0583 11.3008 21.8206C11.7183 22.2013 12.1104 22.551 12.4131 22.8127C12.5646 22.9437 12.6924 23.0526 12.79 23.1311C12.839 23.1704 12.8792 23.2014 12.9102 23.2239C12.9256 23.2351 12.938 23.2433 12.9473 23.2493C12.9538 23.2534 12.9577 23.2554 12.959 23.2561C12.9889 23.2697 13.0247 23.2758 13.1016 23.2249C13.1816 23.1718 13.4109 22.9786 13.7354 22.6917C14.0552 22.4088 14.4582 22.0439 14.8779 21.6575C15.718 20.884 16.6233 20.0264 17.0732 19.5657C19.5359 17.044 20.8722 14.8358 21.3486 12.5393C21.4088 12.2492 21.4446 11.7712 21.4512 11.2747C21.4577 10.7789 21.4345 10.2792 21.3818 9.94751C20.8193 6.40757 18.1545 3.62839 14.6357 2.91431ZM12.1738 6.33618C14.5491 5.89123 16.9011 7.43142 17.4648 9.79712C17.5257 10.0526 17.5546 10.4375 17.5547 10.8127C17.5548 11.188 17.5265 11.5731 17.4658 11.8293C17.0974 13.3855 15.8628 14.6888 14.3311 15.175L14.0205 15.261C13.7635 15.3224 13.377 15.3508 13 15.3508C12.7173 15.3508 12.4292 15.335 12.1943 15.301L11.9795 15.261C10.306 14.8613 8.92717 13.4893 8.53418 11.8293C8.47351 11.5731 8.44521 11.188 8.44531 10.8127C8.44542 10.4375 8.47433 10.0526 8.53516 9.79712C8.95384 8.0402 10.3952 6.66952 12.1738 6.33618ZM13.5605 8.02368C12.6192 7.82664 11.7106 8.10551 10.9941 8.81763C10.5238 9.28523 10.27 9.7733 10.1748 10.385C9.95298 11.8119 10.8775 13.2089 12.291 13.5754C14.6157 14.1782 16.6092 11.7634 15.5801 9.58813C15.2255 8.83869 14.4039 8.20025 13.5605 8.02368Z" fill="black" stroke="black" strokeWidth="0.3" />
    </svg>
  );
}

function UserIcon() {
  return (
    <svg width="25" height="26" viewBox="0 0 25 26" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M16.819 7.47485C16.6199 10.1597 14.5846 12.3499 12.3503 12.3499C10.1159 12.3499 8.07702 10.1602 7.88151 7.47485C7.67839 4.68188 9.65885 2.59985 12.3503 2.59985C15.0417 2.59985 17.0221 4.73267 16.819 7.47485Z" stroke="black" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M12.3497 15.5999C7.93176 15.5999 3.44778 18.0374 2.61801 22.6381C2.51797 23.1927 2.8318 23.7249 3.41223 23.7249H21.2872C21.8682 23.7249 22.182 23.1927 22.082 22.6381C21.2517 18.0374 16.7677 15.5999 12.3497 15.5999Z" stroke="black" strokeWidth="2" strokeMiterlimit="10" />
    </svg>
  );
}

function CardIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M22.666 3C28.546 3 30.333 4.78699 30.333 10.667V21.333C30.333 27.213 28.546 29 22.666 29H9.33301C3.45301 29 1.66602 27.213 1.66602 21.333V10.667C1.66602 4.78699 3.45301 3 9.33301 3H22.666ZM9.33301 5C4.55967 5 3.66602 5.90699 3.66602 10.667V21.333C3.66602 26.093 4.55967 27 9.33301 27H22.666C27.4393 27 28.333 26.093 28.333 21.333V10.667C28.333 5.90699 27.4393 5 22.666 5H9.33301Z" fill="black" />
      <path d="M22.666 3C28.546 3 30.333 4.78699 30.333 10.667V21.333C30.333 27.213 28.546 29 22.666 29H9.33301C3.45301 29 1.66602 27.213 1.66602 21.333V10.667C1.66602 4.78699 3.45301 3 9.33301 3H22.666ZM9.33301 5C4.55967 5 3.66602 5.90699 3.66602 10.667V21.333C3.66602 26.093 4.55967 27 9.33301 27H22.666C27.4393 27 28.333 26.093 28.333 21.333V10.667C28.333 5.90699 27.4393 5 22.666 5H9.33301Z" stroke="black" />
      <path d="M25.333 9.66675C25.8795 9.66693 26.333 10.1202 26.333 10.6667C26.333 11.2133 25.8795 11.6666 25.333 11.6667H18.666C18.1193 11.6667 17.666 11.2134 17.666 10.6667C17.666 10.1201 18.1193 9.66675 18.666 9.66675H25.333Z" fill="black" />
      <path d="M25.333 9.66675C25.8795 9.66693 26.333 10.1202 26.333 10.6667C26.333 11.2133 25.8795 11.6666 25.333 11.6667H18.666C18.1193 11.6667 17.666 11.2134 17.666 10.6667C17.666 10.1201 18.1193 9.66675 18.666 9.66675H25.333Z" stroke="black" />
      <path d="M25.333 15C25.8797 15 26.333 15.4533 26.333 16C26.333 16.5467 25.8797 17 25.333 17H20C19.4533 17 19 16.5467 19 16C19 15.4533 19.4533 15 20 15H25.333Z" fill="black" />
      <path d="M25.333 15C25.8797 15 26.333 15.4533 26.333 16C26.333 16.5467 25.8797 17 25.333 17H20C19.4533 17 19 16.5467 19 16C19 15.4533 19.4533 15 20 15H25.333Z" stroke="black" />
      <path d="M25.333 20.3333C25.8795 20.3334 26.333 20.7867 26.333 21.3333C26.333 21.8798 25.8795 22.3331 25.333 22.3333H22.666C22.1193 22.3333 21.666 21.8799 21.666 21.3333C21.666 20.7866 22.1193 20.3333 22.666 20.3333H25.333Z" fill="black" />
      <path d="M25.333 20.3333C25.8795 20.3334 26.333 20.7867 26.333 21.3333C26.333 21.8798 25.8795 22.3331 25.333 22.3333H22.666C22.1193 22.3333 21.666 21.8799 21.666 21.3333C21.666 20.7866 22.1193 20.3333 22.666 20.3333H25.333Z" stroke="black" />
      <path d="M11.333 9.22656C13.2129 9.22656 14.7469 10.7598 14.7471 12.6396C14.7471 14.5196 13.213 16.0537 11.333 16.0537C9.45312 16.0536 7.91992 14.5196 7.91992 12.6396C7.92006 10.7598 9.4532 9.2267 11.333 9.22656ZM11.333 11.2266C10.5599 11.2267 9.92006 11.8665 9.91992 12.6396C9.91992 13.4129 10.5598 14.0536 11.333 14.0537C12.1063 14.0537 12.7471 13.413 12.7471 12.6396C12.7469 11.8664 12.1063 11.2266 11.333 11.2266Z" fill="black" />
      <path d="M11.333 9.22656C13.2129 9.22656 14.7469 10.7598 14.7471 12.6396C14.7471 14.5196 13.213 16.0537 11.333 16.0537C9.45312 16.0536 7.91992 14.5196 7.91992 12.6396C7.92006 10.7598 9.4532 9.2267 11.333 9.22656ZM11.333 11.2266C10.5599 11.2267 9.92006 11.8665 9.91992 12.6396C9.91992 13.4129 10.5598 14.0536 11.333 14.0537C12.1063 14.0537 12.7471 13.413 12.7471 12.6396C12.7469 11.8664 12.1063 11.2266 11.333 11.2266Z" stroke="black" />
      <path d="M10.2129 17.1465C10.9462 17.0798 11.6934 17.0798 12.4268 17.1465C14.8267 17.3732 16.7463 19.2804 16.9863 21.667C17.0395 22.2135 16.6393 22.7064 16.0928 22.7598C16.0661 22.773 16.0266 22.7734 16 22.7734C15.4933 22.7734 15.0533 22.3862 15 21.8662C14.8532 20.4266 13.6932 19.2673 12.2402 19.1338C11.6269 19.0805 11.0127 19.0805 10.3994 19.1338C8.94646 19.2673 7.78649 20.4133 7.63965 21.8662C7.58632 22.4128 7.09342 22.8262 6.54688 22.7598C6.00031 22.7064 5.60016 22.2135 5.65332 21.667C5.89331 19.2671 7.7997 17.3599 10.2129 17.1465Z" fill="black" />
      <path d="M10.2129 17.1465C10.9462 17.0798 11.6934 17.0798 12.4268 17.1465C14.8267 17.3732 16.7463 19.2804 16.9863 21.667C17.0395 22.2135 16.6393 22.7064 16.0928 22.7598C16.0661 22.773 16.0266 22.7734 16 22.7734C15.4933 22.7734 15.0533 22.3862 15 21.8662C14.8532 20.4266 13.6932 19.2673 12.2402 19.1338C11.6269 19.0805 11.0127 19.0805 10.3994 19.1338C8.94646 19.2673 7.78649 20.4133 7.63965 21.8662C7.58632 22.4128 7.09342 22.8262 6.54688 22.7598C6.00031 22.7064 5.60016 22.2135 5.65332 21.667C5.89331 19.2671 7.7997 17.3599 10.2129 17.1465Z" stroke="black" />
    </svg>
  );
}

function MessageIcon() {
  return (
    <svg width="30" height="30" viewBox="0 0 30 30" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <circle cx="9.83333" cy="13.3333" r="1.33333" fill="black" />
      <circle cx="15.1654" cy="13.3333" r="1.33333" fill="black" />
      <circle cx="20.4993" cy="13.3333" r="1.33333" fill="black" />
      <path d="M10.0625 27.8998C10.4875 27.8998 10.9125 27.7748 11.275 27.5373L16.6 23.9873H21.3125C25.6125 23.9873 28.5 21.0998 28.5 16.7998V9.2998C28.5 4.9998 25.6125 2.1123 21.3125 2.1123H8.8125C4.5125 2.1123 1.625 4.9998 1.625 9.2998V16.7998C1.625 20.7748 4.1 23.5498 7.875 23.9373V25.7123C7.875 26.5248 8.31252 27.2623 9.02502 27.6373C9.35002 27.8123 9.7125 27.8998 10.0625 27.8998ZM21.3125 3.97479C24.5375 3.97479 26.625 6.06229 26.625 9.28729V16.7873C26.625 20.0123 24.5375 22.0998 21.3125 22.0998H16.3125C16.125 22.0998 15.95 22.1498 15.7875 22.2623L10.225 25.9623C10.0875 26.0498 9.96249 26.0123 9.89999 25.9748C9.83749 25.9373 9.73749 25.8623 9.73749 25.6998V23.0373C9.73749 22.5248 9.31249 22.0998 8.79999 22.0998C5.57499 22.0998 3.48749 20.0123 3.48749 16.7873V9.28729C3.48749 6.06229 5.57499 3.97479 8.79999 3.97479H21.3125Z" fill="#292D32" />
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/*  Small presentational components                                    */
/* ------------------------------------------------------------------ */

function AvatarVisual() {
  return (
    <div className="relative h-12.5 w-12.5 overflow-hidden rounded-full bg-[#f0b37f]">
      <div className="absolute inset-x-0 top-0 h-5 bg-[#2f2f2f]" />
      <div className="absolute top-5 left-3.25 h-2 w-2 rounded-full bg-[#1f1f1f]" />
      <div className="absolute top-5 right-3.25 h-2 w-2 rounded-full bg-[#1f1f1f]" />
      <div className="absolute top-8 left-4.25 h-1 w-4 rounded-full bg-[#c96d58]" />
    </div>
  );
}

function InfoRow({ icon, title, lineOne, lineTwo }) {
  return (
    <div className="grid grid-cols-[26px_minmax(0,1fr)] gap-5 px-5 py-5">
      <div className="mt-1">{icon}</div>
      <div>
        <p className="text-[16px] leading-5 font-normal text-[#5f5f5f]">
          {title}
        </p>
        <p className="mt-1.5 text-[20px] leading-5 font-normal text-[#111111]">
          {lineOne}
        </p>
        <p className="mt-1.5 text-[16px] leading-5 font-normal text-[#7e7e7e]">
          {lineTwo}
        </p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Status helper functions                                            */
/* ------------------------------------------------------------------ */

function getDefaultItemStatuses(order) {
  if (order.status === 'in_transit') {
    if (order.items.length <= 1) {
      return ['in_transit'];
    }

    return order.items.map((_, index) => {
      if (index === 1) {
        return 'canceled';
      }

      if (index === order.items.length - 1) {
        return 'in_transit_alert';
      }

      return 'in_transit';
    });
  }

  return order.items.map(() => order.status);
}

function toModalStatus(status) {
  if (status === 'canceled') {
    return 'Отменен';
  }
  if (status === 'in_transit' || status === 'in_transit_alert') {
    return 'В пути';
  }
  return 'Оформлен';
}

function toDetailStatus(status) {
  if (status === 'Отменен') {
    return 'canceled';
  }
  if (status === 'В пути') {
    return 'in_transit';
  }
  return 'placed';
}

function getActiveCount(statuses) {
  return statuses.filter((status) => status !== 'canceled').length;
}

function getStatusTitle(statuses, fallback) {
  if (!statuses.length) {
    return STATUS_TITLE[fallback];
  }

  const activeStatuses = statuses.filter((status) => status !== 'canceled');
  if (!activeStatuses.length) {
    return 'Отменен';
  }

  if (
    activeStatuses.some(
      (status) => status === 'in_transit' || status === 'in_transit_alert',
    )
  ) {
    return 'В пути';
  }

  if (activeStatuses.every((status) => status === 'pickup_point')) {
    return 'В пункте выдачи';
  }

  if (activeStatuses.every((status) => status === 'received')) {
    return 'Получен';
  }

  return 'Оформлен';
}

export function OrderDetailsView({ order }) {
  const [statusModalOpen, setStatusModalOpen] = useState(false);
  const [savedItemStatuses, setSavedItemStatuses] = useState(null);
  const [savedTrackNumbers, setSavedTrackNumbers] = useState({});

  const defaultItemStatuses = useMemo(
    () => getDefaultItemStatuses(order),
    [order],
  );

  const itemStatuses = useMemo(
    () =>
      order.items.map((item, index) => {
        if (!savedItemStatuses) {
          return defaultItemStatuses[index];
        }
        return toDetailStatus(
          savedItemStatuses[item.id] ??
            toModalStatus(defaultItemStatuses[index]),
        );
      }),
    [defaultItemStatuses, order.items, savedItemStatuses],
  );

  const modalInitialStatuses = useMemo(() => {
    if (savedItemStatuses) {
      return savedItemStatuses;
    }

    const initial = {};
    order.items.forEach((item, index) => {
      initial[item.id] = toModalStatus(defaultItemStatuses[index]);
    });
    return initial;
  }, [defaultItemStatuses, order.items, savedItemStatuses]);

  const activeCount = getActiveCount(itemStatuses);
  const statusTitle = getStatusTitle(itemStatuses, order.status);
  const summaryDotClass =
    activeCount === 0 ? 'border-[#cf4444]' : 'border-[#4eaa1e]';

  const goodsTotal = order.items.reduce((sum, item) => sum + item.price, 0);
  const promoCodeDiscount = 500;
  const bonusDiscount = 200;
  const totalDiscount = promoCodeDiscount + bonusDiscount;
  const shippingFee = 750;
  const pickupFee = 750;
  const finalTotal = goodsTotal - totalDiscount + shippingFee;

  const handleSaveStatuses = (payload) => {
    setSavedItemStatuses(payload.itemStatuses);
    setSavedTrackNumbers(payload.trackNumbers);
  };

  return (
    <section className="animate-fadeIn">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Link
          href="/admin/orders"
          className="inline-flex h-11.5 w-27.75 items-center gap-2.5 rounded-[15px] bg-[#f4f3f1] px-3.25 py-3 text-[16px] leading-5 font-medium text-[#000000]"
        >
          <span>Заказы</span>
          <span className="text-xl leading-none">›</span>
        </Link>

        <span className="inline-flex h-11.5 items-center rounded-[15px] bg-[#f4f3f1] px-3.25 py-3 text-[16px] leading-5 font-medium text-[#000000]">
          №{order.orderNumber}
          <CopyMark text={order.orderNumber} />
        </span>
        <span className="inline-flex h-11.5 items-center rounded-[15px] bg-[#f4f3f1] px-3.25 py-3 text-[16px] leading-5 font-medium text-[#000000]">
          {order.trackId}
          <CopyMark text={order.trackId} />
        </span>
        <span className="text-[16px] leading-5 font-medium text-[#7e7e7e]">
          {formatDateTime(order.createdAt)}
        </span>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_594px]">
        <div>
          <h1 className="text-[26px] leading-8 font-bold tracking-[-0.42px] text-[#3d3c3a]">
            {statusTitle}
          </h1>
          <p className="mt-1 text-[16px] leading-5 font-medium text-[#000000]">
            {activeCount} из {order.items.length}
          </p>
          <button
            type="button"
            className="mt-4 inline-flex h-11.5 w-40.25 items-center gap-2.5 rounded-[15px] bg-[#f4f3f1] px-3.25 py-3 text-[16px] leading-5 font-medium text-[#000000]"
          >
            История заказа
          </button>

          <article className="mt-4 rounded-[20px] bg-[#f4f3f1] p-5">
            <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2 text-[16px] leading-5 font-medium text-[#7e7e7e]">
                <span className="inline-flex items-center">
                  №{order.orderNumber}
                  <CopyMark text={order.orderNumber} />
                </span>
                <span>•</span>
                <span className="inline-flex items-center">
                  {order.trackId}
                  <CopyMark text={order.trackId} />
                </span>
                <span>•</span>
                <span>{formatDateTime(order.createdAt)}</span>
                {order.fromChina && (
                  <>
                    <span>•</span>
                    <span className="rounded-full bg-[#f2e5c2] px-3 py-1 text-[16px] leading-5 font-medium text-[#5c4a17]">
                      Из Китая
                    </span>
                  </>
                )}
                <span className="rounded-full bg-[#2d2d2d] px-3 py-1 text-[16px] leading-5 font-medium text-white">
                  Оригинал
                </span>
              </div>

              <button
                type="button"
                onClick={() => setStatusModalOpen(true)}
                className="inline-flex h-11.5 min-w-51.5 items-center justify-center gap-2 rounded-[15px] bg-white px-3.25 py-3 text-[16px] leading-5 font-medium text-[#000000]"
              >
                <span
                  className={cn('h-4 w-4 rounded-full border', summaryDotClass)}
                />
                <span>{statusTitle}</span>
                <span className="text-[#7e7e7e]">
                  {activeCount} из {order.items.length}
                </span>
                <span className="text-[#8f8f8f]"></span>
              </button>
            </div>

            <div className="space-y-4">
              {order.items.map((item, index) => {
                const statusMeta = ITEM_STATUS_META[itemStatuses[index]];

                return (
                  <div
                    key={item.id}
                    className="grid items-center gap-x-4 gap-y-3 sm:grid-cols-[74px_minmax(0,246px)_86px_minmax(0,1fr)]"
                  >
                    <Image
                      src={item.image}
                      alt={item.title}
                      width={64}
                      height={64}
                      className="h-16 w-16 rounded"
                    />
                    <div>
                      <p className="max-w-61.5 text-[16px] leading-5 font-medium text-[#000000]">
                        {item.title}
                      </p>
                      <p className="mt-1 text-[16px] leading-5 font-medium text-[#7e7e7e]">
                        Размер: {item.size}
                      </p>
                    </div>
                    <p className="text-[16px] leading-5 font-medium text-[#000000]">
                      {formatCurrency(item.price)}
                    </p>
                    <div className="justify-self-end">
                      <button
                        type="button"
                        onClick={() => setStatusModalOpen(true)}
                        className={cn(
                          'inline-flex h-9.5 min-w-30.25 items-center justify-center gap-2 rounded-xl px-4 text-[16px] leading-5 font-medium',
                          statusMeta.className,
                        )}
                      >
                        {statusMeta.dotClassName && (
                          <span
                            className={cn(
                              'h-4 w-4 rounded-full border',
                              statusMeta.dotClassName,
                            )}
                          />
                        )}
                        {statusMeta.label}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </article>
        </div>

        <aside className="space-y-4">
          <article className="h-25 rounded-[20px] bg-[#f4f3f1] px-6.25 py-6.25">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3.5">
                <AvatarVisual />
                <div>
                  {/* TODO: order.customerName, order.customerId not yet in seed data */}
                  <p className="text-[20px] leading-[100%] font-medium text-[#1f1f1f]">
                    {order.customerName ?? 'Artem Maltsev'}
                  </p>
                  <p className="mt-1.5 inline-flex items-center text-[16px] leading-5 font-medium text-[#7e7e7e]">
                    ID {order.customerId ?? '707635394'}
                    <CopyMark text={String(order.customerId ?? '707635394')} />
                  </p>
                </div>
              </div>

              <button
                type="button"
                className="flex h-10.5 w-10.5 items-center justify-center rounded-[14px] bg-white"
              >
                <MessageIcon />
              </button>
            </div>
          </article>

          <article className="overflow-hidden rounded-[20px] bg-[#f4f3f1]">
            <InfoRow
              icon={<PinIcon />}
              title="Пункт выдачи"
              lineOne={order.pickupAddress ?? 'Москва, Никольская ул., 24, стр 3'}
              lineTwo={order.pickupMeta ?? 'СДЕК · 7 дней хранения'}
            />
            <div className="h-px bg-[#dddcd9]" />
            {/* TODO: order.recipientName, order.recipientPhone, order.recipientEmail not yet in seed data */}
            <InfoRow
              icon={<UserIcon />}
              title="Получатель"
              lineOne={order.recipientName ?? 'Овечкин Александр Михайлович'}
              lineTwo={`${order.recipientPhone ?? '+7 910 889-77-62'} · ${order.recipientEmail ?? 'Avalex@gmail.com'}`}
            />
            <div className="h-px bg-[#dddcd9]" />
            {/* TODO: order.passportSeries, order.inn, order.passportDate, order.birthDate not yet in seed data */}
            <InfoRow
              icon={<CardIcon />}
              title="Данные для таможни"
              lineOne={order.customsData ?? '5330 030220 · 775598987121'}
              lineTwo={order.customsDates ?? '31.12.2020 · 31.08.2002'}
            />
          </article>

          <article className="min-h-64.25 rounded-[20px] bg-[#f4f3f1] p-5">
            <div className="flex items-center justify-between text-[16px] leading-5 font-bold text-[#111111]">
              <span>{order.items.length} товара</span>
              <span>{formatCurrency(goodsTotal)}</span>
            </div>

            <div className="mt-3 space-y-2 text-[16px] leading-5 font-normal text-[#111111]">
              <div className="flex items-center justify-between">
                <span>Скидка</span>
                <span>-{formatCurrency(totalDiscount)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="pl-3">• Промокод PROMO100</span>
                <span>-{formatCurrency(promoCodeDiscount)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="pl-3">• Подарочные баллы</span>
                <span>-{formatCurrency(bonusDiscount)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Доставка</span>
                <span>{formatCurrency(shippingFee)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="pl-3">• В пункт выдачи</span>
                <span>{formatCurrency(pickupFee)}</span>
              </div>
            </div>

            <div className="mt-6 flex items-end justify-between">
              <span className="text-[20px] leading-[120%] font-bold text-[#2d2d2d]">
                Итого
              </span>
              <span className="text-[26px] leading-8 font-bold tracking-[-0.42px] text-[#3d3c3a]">
                {formatCurrency(finalTotal)}
              </span>
            </div>
          </article>
        </aside>
      </div>

      <OrderStatusModal
        open={statusModalOpen}
        order={order}
        onClose={() => setStatusModalOpen(false)}
        onSave={handleSaveStatuses}
        initialItemStatuses={modalInitialStatuses}
        initialTrackNumbers={savedTrackNumbers}
      />
    </section>
  );
}
