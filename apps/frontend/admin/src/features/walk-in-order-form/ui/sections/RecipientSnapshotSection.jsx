'use client';

import {
  validateEmail,
  validateInn,
  validateIsoDate,
  validateNonEmptyString,
  validatePassportNumber,
  validatePassportSerial,
  validatePhone,
} from '../../lib/validators';
import { FormSection, TextField } from './FormSection';

// RecipientSnapshot — the customs-bound copy of the customer. Backend
// freezes this on order creation; subsequent edits go through a separate
// support flow. The warning callout makes that contract visible to the
// admin BEFORE they hit submit.
export function RecipientSnapshotSection({
  recipient,
  setRecipientField,
  touched,
  onTouch,
}) {
  return (
    <FormSection
      title="Данные для таможни (получатель)"
      description="Frozen snapshot — после создания заказа правки только через support-flow"
    >
      <div className="bg-app-warningSoft text-app-text border-app-border rounded-2xl border px-4 py-3 text-sm">
        ⚠ Эти поля сохраняются как неизменяемый снапшот. Проверьте паспорт и ИНН
        перед отправкой формы.
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <TextField
          label="ФИО (RU)"
          required
          name="recipientFullNameRu"
          value={recipient.fullNameRu}
          onChange={(e) => setRecipientField('fullNameRu', e.target.value)}
          onBlur={() => onTouch('recipientFullNameRu')}
          error={
            touched.recipientFullNameRu &&
            !validateNonEmptyString(recipient.fullNameRu)
              ? 'Введите ФИО на русском'
              : null
          }
        />
        <TextField
          label="ФИО (Latin)"
          required
          name="recipientFullNameLat"
          value={recipient.fullNameLat}
          onChange={(e) => setRecipientField('fullNameLat', e.target.value)}
          onBlur={() => onTouch('recipientFullNameLat')}
          error={
            touched.recipientFullNameLat &&
            !validateNonEmptyString(recipient.fullNameLat)
              ? 'Введите ФИО латиницей'
              : null
          }
        />

        <div className="grid grid-cols-[1fr_2fr] gap-3">
          <TextField
            label="Серия паспорта"
            required
            name="recipientPassportSerial"
            inputMode="numeric"
            maxLength={4}
            placeholder="1234"
            value={recipient.passportSerial}
            onChange={(e) =>
              setRecipientField(
                'passportSerial',
                e.target.value.replace(/\D/g, ''),
              )
            }
            onBlur={() => onTouch('recipientPassportSerial')}
            error={
              touched.recipientPassportSerial &&
              !validatePassportSerial(recipient.passportSerial)
                ? '4 цифры'
                : null
            }
          />
          <TextField
            label="Номер паспорта"
            required
            name="recipientPassportNumber"
            inputMode="numeric"
            maxLength={6}
            placeholder="567890"
            value={recipient.passportNumber}
            onChange={(e) =>
              setRecipientField(
                'passportNumber',
                e.target.value.replace(/\D/g, ''),
              )
            }
            onBlur={() => onTouch('recipientPassportNumber')}
            error={
              touched.recipientPassportNumber &&
              !validatePassportNumber(recipient.passportNumber)
                ? '6 цифр'
                : null
            }
          />
        </div>

        <TextField
          label="ИНН"
          required
          name="recipientInn"
          inputMode="numeric"
          maxLength={12}
          placeholder="500100732272"
          value={recipient.inn}
          onChange={(e) =>
            setRecipientField('inn', e.target.value.replace(/\D/g, ''))
          }
          onBlur={() => onTouch('recipientInn')}
          error={
            touched.recipientInn && !validateInn(recipient.inn)
              ? 'ИНН — 12 цифр'
              : null
          }
        />

        <TextField
          label="Дата выдачи паспорта"
          required
          name="recipientPassportIssueDate"
          type="date"
          value={recipient.passportIssueDate}
          onChange={(e) =>
            setRecipientField('passportIssueDate', e.target.value)
          }
          onBlur={() => onTouch('recipientPassportIssueDate')}
          error={
            touched.recipientPassportIssueDate &&
            !validateIsoDate(recipient.passportIssueDate)
              ? 'Укажите дату'
              : null
          }
        />
        <TextField
          label="Дата рождения"
          required
          name="recipientBirthDate"
          type="date"
          value={recipient.birthDate}
          onChange={(e) => setRecipientField('birthDate', e.target.value)}
          onBlur={() => onTouch('recipientBirthDate')}
          error={
            touched.recipientBirthDate && !validateIsoDate(recipient.birthDate)
              ? 'Укажите дату'
              : null
          }
        />

        <TextField
          label="Email"
          required
          name="recipientEmail"
          type="email"
          value={recipient.email}
          onChange={(e) => setRecipientField('email', e.target.value)}
          onBlur={() => onTouch('recipientEmail')}
          error={
            touched.recipientEmail && !validateEmail(recipient.email)
              ? 'Неверный формат email'
              : null
          }
        />
        <TextField
          label="Телефон"
          required
          name="recipientPhone"
          inputMode="tel"
          placeholder="+79108897762"
          value={recipient.phone}
          onChange={(e) => setRecipientField('phone', e.target.value)}
          onBlur={() => onTouch('recipientPhone')}
          error={
            touched.recipientPhone && !validatePhone(recipient.phone)
              ? 'Неверный формат телефона'
              : null
          }
        />
      </div>
    </FormSection>
  );
}
