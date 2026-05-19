'use client';

import {
  validateEmail,
  validateNonEmptyString,
  validatePhone,
} from '../../lib/validators';
import { FormSection, TextField } from './FormSection';

// Minimum profile for the walk-in customer — backend provisions a fresh
// Identity from these fields. Email is the only optional input; phone and
// fullName are required by the backend (see `WalkInProfileSchema`).
export function CustomerProfileSection({
  profile,
  setProfileField,
  touched,
  onTouch,
}) {
  const showFullNameError =
    touched.profileFullName && !validateNonEmptyString(profile.fullName);
  const showPhoneError = touched.profilePhone && !validatePhone(profile.phone);
  const showEmailError =
    touched.profileEmail &&
    profile.email.length > 0 &&
    !validateEmail(profile.email);

  return (
    <FormSection
      title="Клиент"
      description="Данные для создания учётной записи покупателя"
    >
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <TextField
          label="ФИО"
          required
          name="profileFullName"
          autoComplete="off"
          value={profile.fullName}
          onChange={(e) => setProfileField('fullName', e.target.value)}
          onBlur={() => onTouch('profileFullName')}
          error={showFullNameError ? 'Введите ФИО клиента' : null}
        />
        <TextField
          label="Телефон"
          required
          name="profilePhone"
          inputMode="tel"
          placeholder="+79108897762"
          value={profile.phone}
          onChange={(e) => setProfileField('phone', e.target.value)}
          onBlur={() => onTouch('profilePhone')}
          error={showPhoneError ? 'Неверный формат телефона' : null}
        />
        <TextField
          label="Email"
          name="profileEmail"
          type="email"
          value={profile.email}
          onChange={(e) => setProfileField('email', e.target.value)}
          onBlur={() => onTouch('profileEmail')}
          error={showEmailError ? 'Неверный формат email' : null}
          helper="Опционально — для уведомлений по заказу"
        />
      </div>
    </FormSection>
  );
}
