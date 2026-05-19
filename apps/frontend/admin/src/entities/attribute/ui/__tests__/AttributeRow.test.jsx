/**
 * Audit 8.1 — verify the flag-icon glyphs in <AttributeRow> are
 * aria-hidden so screen readers announce only the textual labels.
 */
import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';
import { AttributeRow } from '../AttributeRow';

const FULL_FLAGS_ATTRIBUTE = {
  id: 'a1',
  code: 'color',
  slug: 'color',
  nameI18N: { ru: 'Цвет', en: 'Color' },
  level: 'variant',
  dataType: 'string',
  uiType: 'color_swatch',
  isDictionary: true,
  isFilterable: true,
  isSearchable: true,
  searchWeight: 5,
  isComparable: true,
  isVisibleOnCard: true,
};

describe('<AttributeRow>', () => {
  it('every emoji glyph is wrapped in an aria-hidden span', () => {
    const { container } = render(
      <table>
        <tbody>
          <AttributeRow attribute={FULL_FLAGS_ATTRIBUTE} />
        </tbody>
      </table>,
    );
    const items = container.querySelectorAll('li');
    expect(items.length).toBe(5);
    for (const li of items) {
      const emojiSpan = li.querySelector('span[aria-hidden="true"]');
      expect(emojiSpan).not.toBeNull();
      // Each glyph must occupy its own aria-hidden host so SR reads only
      // the surrounding label text.
      expect(emojiSpan.textContent.length).toBeGreaterThan(0);
    }
  });

  it('renders only the flags that are toggled on', () => {
    const { container } = render(
      <table>
        <tbody>
          <AttributeRow
            attribute={{
              ...FULL_FLAGS_ATTRIBUTE,
              isFilterable: false,
              isComparable: false,
              isVisibleOnCard: false,
            }}
          />
        </tbody>
      </table>,
    );
    const items = container.querySelectorAll('li');
    expect(items.length).toBe(2); // dictionary + searchable
  });
});
