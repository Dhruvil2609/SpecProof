export type UnitSystem = 'metric' | 'imperial';

export function formatTimestamp(utcIso: string, locale = 'en-GB'): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(utcIso));
}

export function formatDistance(
  millimetres: number,
  unitSystem: UnitSystem,
  locale = 'en-GB',
): string {
  const value = unitSystem === 'metric' ? millimetres : millimetres / 25.4;
  const unit = unitSystem === 'metric' ? 'mm' : 'in';
  return `${new Intl.NumberFormat(locale, {
    minimumFractionDigits: unitSystem === 'metric' ? 1 : 2,
    maximumFractionDigits: unitSystem === 'metric' ? 1 : 2,
  }).format(value)} ${unit}`;
}

export function formatPercent(value: number, locale = 'en-GB'): string {
  return new Intl.NumberFormat(locale, {
    style: 'percent',
    maximumFractionDigits: 0,
  }).format(value);
}
