'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import ChevronIcon from '@/assets/icons/chevron.svg';
import dayjs from '@/lib/dayjs';
import { cn } from '@/lib/utils';

const weekDays = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс'];

export function DateRangePicker({ value, onChange, placeholder = 'Выбрать период', forcePlaceholder = false }) {
  const [isOpen, setIsOpen] = useState(false);
  const [currentMonth, setCurrentMonth] = useState(dayjs().startOf('month'));
  const ref = useRef(null);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handleClickOutside(event) {
      const target = event.target;
      if (!ref.current) {
        return;
      }
      if (typeof Node !== 'undefined' && target instanceof Node && ref.current.contains(target)) {
        return;
      }
      setIsOpen(false);
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const months = useMemo(() => [currentMonth.startOf('month'), currentMonth.add(1, 'month').startOf('month')], [currentMonth]);

  const label = useMemo(() => {
    if (!value.from && !value.to) {
      return placeholder;
    }

    if (value.from && !value.to) {
      return value.from.format('D MMM YYYY');
    }

    if (value.from && value.to) {
      return `${value.from.format('D MMM')} — ${value.to.format('D MMM')}`;
    }

    return placeholder;
  }, [value.from, value.to, placeholder]);

  const buttonLabel = forcePlaceholder ? placeholder : label;

  function buildMonthGrid(monthStart) {
    const daysInMonth = monthStart.daysInMonth();
    const firstWeekDay = (monthStart.day() + 6) % 7;

    const grid = Array.from({ length: firstWeekDay }, () => null);

    for (let i = 1; i <= daysInMonth; i += 1) {
      grid.push(monthStart.date(i));
    }

    return grid;
  }

  function isInRange(day) {
    if (!value.from || !value.to) {
      return false;
    }

    return day.isSameOrAfter(value.from, 'day') && day.isSameOrBefore(value.to, 'day');
  }

  function handleSelect(day) {
    if (!value.from || (value.from && value.to)) {
      onChange({ from: day, to: null });
      return;
    }

    if (day.isBefore(value.from, 'day')) {
      onChange({ from: day, to: value.from });
      setIsOpen(false);
      return;
    }

    onChange({ from: value.from, to: day });
    setIsOpen(false);
  }

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="inline-flex items-center gap-1.5 text-base font-medium leading-5 text-[#7e7e7e] transition-colors hover:text-[#2d2d2d]"
      >
        <span>{buttonLabel}</span>
        <ChevronIcon className={cn('h-4 w-4 text-[#7e7e7e] transition-transform', isOpen && 'rotate-180')} />
      </button>

      {isOpen && (
        <div className="absolute right-0 z-30 mt-4 w-[min(760px,calc(100vw-2rem))] animate-fadeIn rounded-3xl bg-[#f4f3f1] p-5 shadow-[0_14px_34px_rgba(26,27,29,0.14)]">
          <div className="mb-4 flex items-center justify-between">
            <button
              type="button"
              onClick={() => setCurrentMonth((prev) => prev.subtract(1, 'month'))}
              className="flex h-9 w-9 items-center justify-center rounded-full text-base text-app-muted hover:bg-app-bg md:h-10 md:w-10 md:text-lg"
            >
              {'<'}
            </button>
            <button
              type="button"
              onClick={() => {
                onChange({ from: null, to: null });
                setIsOpen(false);
              }}
              className="text-sm text-app-muted underline-offset-2 hover:underline md:text-base"
            >
              Сбросить
            </button>
            <button
              type="button"
              onClick={() => setCurrentMonth((prev) => prev.add(1, 'month'))}
              className="flex h-9 w-9 items-center justify-center rounded-full text-base text-app-muted hover:bg-app-bg md:h-10 md:w-10 md:text-lg"
            >
              {'>'}
            </button>
          </div>

          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 md:gap-6">
            {months.map((month) => (
              <div key={month.format('YYYY-MM')}>
                <h4 className="mb-3 text-center text-base font-semibold text-app-text md:text-xl">{month.format('MMMM YYYY')}</h4>
                <div className="mb-2 grid grid-cols-7 text-center text-xs text-app-muted md:text-sm">
                  {weekDays.map((day) => (
                    <span key={day}>{day}</span>
                  ))}
                </div>
                <div className="grid grid-cols-7 gap-1">
                  {buildMonthGrid(month).map((day, index) => {
                    if (!day) {
                      return <div key={`empty-${month}-${index}`} className="h-8 md:h-10" />;
                    }

                    const isStart = value.from?.isSame(day, 'day') ?? false;
                    const isEnd = value.to?.isSame(day, 'day') ?? false;
                    const selected = isStart || isEnd;

                    return (
                      <button
                        key={day.format('YYYY-MM-DD')}
                        type="button"
                        onClick={() => handleSelect(day)}
                        className={cn(
                          'h-8 rounded-full text-sm transition-colors md:h-10 md:text-base',
                          isInRange(day) && 'bg-[#f1f1f3] text-app-text',
                          selected && 'bg-app-text text-white',
                          !selected && 'hover:bg-[#f3f4f5]',
                        )}
                      >
                        {day.date()}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

