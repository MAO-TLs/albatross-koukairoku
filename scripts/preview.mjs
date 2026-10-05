import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {extname, resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {previewRoute} from './preview-routing.mjs';
import {SITE_BASE_PATH} from '../site-target.mjs';
const root = fileURLToPath(new URL('../dist/client/', import.meta.url));
const types = {'.html':'text/html; charset=utf-8', '.js':'text/javascript', '.css':'text/css', '.json':'application/json', '.png':'image/png', '.svg':'image/svg+xml', '.rsc':'text/x-component'};
createServer(async (req,res) => {
  if (!['GET','HEAD'].includes(req.method)) {res.writeHead(405).end(); return;}
  const route = previewRoute(req.url ?? '/');
  if (route.redirect) {res.writeHead(302, {Location:route.redirect}).end(); return;}
  if (route.status) {res.writeHead(route.status).end(); return;}
  try {
    const path = resolve(root,route.file);
    if (!path.startsWith(root.endsWith(sep) ? root : root + sep)) {res.writeHead(400).end(); return;}
    const bytes = await readFile(path);
    res.writeHead(200, {'Content-Type':types[extname(path)] ?? 'application/octet-stream', 'Content-Length':bytes.length, 'Cache-Control':'no-store'});
    res.end(req.method === 'HEAD' ? undefined : bytes);
  } catch {res.writeHead(404).end('Not found');}
}).listen(4328,'127.0.0.1', () => console.log(`Private Albatross preview: http://127.0.0.1:4328${SITE_BASE_PATH}/`));
