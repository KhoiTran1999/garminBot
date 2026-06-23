import fs from 'fs';
const code = fs.readFileSync('cloudflare_worker.js', 'utf8');
console.log("length:", code.length);
