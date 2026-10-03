export async function api(path, opts = {}) {
  const r = await fetch('/api' + path, {
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
    ...opts,
  })
  if (!r.ok) {
    let detail = r.statusText
    try { const j = await r.json(); detail = j.detail || JSON.stringify(j) } catch {}
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  if (r.status === 204) return null
  return r.json()
}

export function fmtScore(v) {
  if (v === null || v === undefined) return '—'
  return Number(v).toFixed(1).replace(/\.0$/, '')
}
