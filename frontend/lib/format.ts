// Amounts are formatted with a fixed locale. `toLocaleString()` without one uses the
// server's locale during SSR and the viewer's locale in the browser, so the two
// renders differ (React hydration error #418) and amounts show as "1703,63".
const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

const usdWhole = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

/** "$1,703.63", "$9,792.30", "$48,000" (cents shown only when there are any). */
export function formatUSD(value: number): string {
  return Number.isInteger(value) ? usdWhole.format(value) : usd.format(value);
}

/** "$6,799" (rounded to whole dollars). */
export function formatUSDWhole(value: number): string {
  return usdWhole.format(value);
}
