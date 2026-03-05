// Fetching a local file from public folder in frontend folder
export async function loadTxt() {
  const res = await fetch(import.meta.env.VITE_TXT_ENDPOINT);

  if (!res.ok) {
    throw new Error(`Failed: ${res.status} ${await res.text()}`);
  }

  return await res.text();
}