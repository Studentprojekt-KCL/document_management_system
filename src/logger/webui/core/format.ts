// webui/lib/format.ts

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString();
}