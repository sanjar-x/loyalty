/**
 * Audit 1.5 / 1.6 — focus trap + return focus regression tests.
 *
 * Pre-fix: a Tab from the last focusable element inside the dialog
 * would escape into the background page; closing the modal lost focus
 * entirely. The fix adds a single `useEffect` keyed on `open` that
 * autofocuses the first focusable, traps Tab cycle, and returns focus
 * to the original trigger.
 */
import { useState } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import { Modal } from '../Modal';

function Harness({ initiallyOpen = false }) {
  const [open, setOpen] = useState(initiallyOpen);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        Открыть модалку
      </button>
      <Modal open={open} onClose={() => setOpen(false)} title="Тест">
        <button type="button">Первая</button>
        <button type="button">Вторая</button>
        <button type="button">Третья</button>
      </Modal>
    </>
  );
}

afterEach(() => {
  // jsdom keeps `body.style.overflow` between tests when scroll-lock
  // doesn't run its cleanup — reset so the next test sees a clean slate.
  document.body.style.overflow = '';
});

describe('<Modal>', () => {
  it('autofocuses first focusable button on open', async () => {
    render(<Harness />);

    fireEvent.click(screen.getByRole('button', { name: 'Открыть модалку' }));

    await new Promise((r) => setTimeout(r, 16));

    expect(screen.getByRole('button', { name: 'Первая' })).toHaveFocus();
  });

  it('cycles focus on Tab from the last button to the first', async () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole('button', { name: 'Открыть модалку' }));
    await new Promise((r) => setTimeout(r, 16));

    const third = screen.getByRole('button', { name: 'Третья' });
    third.focus();
    expect(third).toHaveFocus();

    fireEvent.keyDown(document, { key: 'Tab' });
    expect(screen.getByRole('button', { name: 'Первая' })).toHaveFocus();
  });

  it('cycles focus on Shift+Tab from the first button back to the last', async () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole('button', { name: 'Открыть модалку' }));
    await new Promise((r) => setTimeout(r, 16));

    const first = screen.getByRole('button', { name: 'Первая' });
    first.focus();
    expect(first).toHaveFocus();

    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
    expect(screen.getByRole('button', { name: 'Третья' })).toHaveFocus();
  });

  it('returns focus to the trigger on close', async () => {
    render(<Harness />);
    const trigger = screen.getByRole('button', { name: 'Открыть модалку' });
    // jsdom doesn't focus a button on click — explicit focus mirrors
    // the real-browser behaviour where the trigger is the active
    // element at the moment the modal opens.
    trigger.focus();
    fireEvent.click(trigger);
    await new Promise((r) => setTimeout(r, 16));

    fireEvent.keyDown(window, { key: 'Escape' });

    expect(trigger).toHaveFocus();
  });
});
