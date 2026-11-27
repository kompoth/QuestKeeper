/**
 * Formats an ISO date string as day-month-year.
 *
 * 'en-GB' forces day-month-year (European) order - plain toLocaleDateString() can resolve to
 * American month-day-year depending on the browser's default locale.
 */
export function formatDate (isoDate: string): string {
  return new Date(isoDate).toLocaleDateString('en-GB')
}
