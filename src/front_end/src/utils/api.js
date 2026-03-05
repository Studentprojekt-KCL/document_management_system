export async function loadTxt() {
  const res = await fetch(import.meta.env.VITE_TEXT_ENDPOINT);

  if (!res.ok) {
    throw new Error(`Failed: ${res.status} ${await res.text()}`);
  }

  return await res.text();
}