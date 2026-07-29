export function toNumber(value: string | number): number {
  return typeof value === "number" ? value : parseFloat(value);
}

export function formatPrice(value: string | number): string {
  return toNumber(value).toFixed(2);
}

export function formatScore(value: string | number): string {
  return `${(toNumber(value) * 100).toFixed(0)}%`;
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatSession(session: string): string {
  return session.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();
}
