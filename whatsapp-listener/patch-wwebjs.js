// Workaround for whatsapp-web.js 1.34.x against the WhatsApp Web builds rolled
// out on 2026-09-17: EVERY media send (PDF, image, ...) fails with
//   "Data passed to getter must include an id property ... but got undefined"
// while text still works. Cause: the media model's internal `__x_id` is spread
// into the outgoing message object and overwrites the message's real id.
// Upstream fix (wwebjs/whatsapp-web.js PR #201923, not yet released):
//   delete message.__x_id;
// Applied at image-build time so it survives every rebuild. Remove this file and
// its Dockerfile step once a whatsapp-web.js release includes the fix.
const fs = require('fs');

const FILE = 'node_modules/whatsapp-web.js/src/util/Injected/Utils.js';
const FIX = 'delete message.__x_id;';
const ANCHOR = "// Bot's won't reply if canonicalUrl is set (linking)";

let src = fs.readFileSync(FILE, 'utf8');
if (src.includes(FIX)) {
  console.log('patch-wwebjs: already patched, nothing to do.');
  process.exit(0);
}
const at = src.indexOf(ANCHOR);
if (at < 0) {
  console.warn('patch-wwebjs: WARNING — anchor not found (library layout changed?). ' +
               'Media sends may fail; check whatsapp-web.js for an official fix.');
  process.exit(0);
}
const lineStart = src.lastIndexOf('\n', at) + 1;
const indent = src.slice(lineStart, at);
src = src.slice(0, lineStart) +
  `${indent}${FIX} // media model id must not overwrite the message id (WA Web 2026-09-17)\n` +
  src.slice(lineStart);
fs.writeFileSync(FILE, src);
console.log('patch-wwebjs: patched media send (dropped __x_id).');
