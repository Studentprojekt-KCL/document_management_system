export async function loadTxt() {
  const res = await fetch("http://localhost:8000/txt-content");

  if (!res.ok) {
    throw new Error(`Failed: ${res.status} ${await res.text()}`);
  }

  return await res.text();
}