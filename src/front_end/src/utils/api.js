// Fetching a local file from public folder in frontend folder
export async function loadTxt() {
  const res = await fetch('/api/txt-content') // import.meta.env.VITE_TXT_ENDPOINT'http://localhost:8000/txt-content'

  if (!res.ok) {
    throw new Error(`Failed: ${res.status} ${await res.text()}`)
  }

  return await res.text()
}