import {SITE_BASE_PATH} from '../site-target.mjs';
export function previewRoute(rawUrl) {
  const url = new URL(rawUrl, 'http://127.0.0.1');
  if (url.pathname === '/' || url.pathname === SITE_BASE_PATH) return {redirect: `${SITE_BASE_PATH}/${url.search}`};
  if (url.pathname === '/script' || url.pathname === '/script/') return {redirect: `${SITE_BASE_PATH}/script/${url.search}`};
  if (!url.pathname.startsWith(`${SITE_BASE_PATH}/`)) return {status: 404};
  let local;
  try { local = decodeURIComponent(url.pathname.slice(SITE_BASE_PATH.length + 1)); }
  catch { return {status: 400}; }
  if (local.startsWith('/') || local.split('/').includes('..') || local.includes('\\') || local.includes('\0')) return {status: 400};
  if (local === 'script') return {redirect: `${SITE_BASE_PATH}/script/${url.search}`};
  return {file: local.endsWith('/') || local === '' ? `${local}index.html` : local};
}
