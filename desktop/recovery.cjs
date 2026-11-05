'use strict';
const fs = require('node:fs');
const path = require('node:path');
function validDraft(d) {
  return d && /^[a-f0-9]{32}$/.test(d.pid) && typeof d.filename === 'string' &&
    d.filename.length <= 500 && typeof d.content === 'string' && Buffer.byteLength(d.content) <= 2000000;
}
function writeDraft(home, d) {
  if (!validDraft(d)) throw new Error('Invalid recovery draft');
  const file = path.join(home, 'recovery.json');
  fs.writeFileSync(file + '.tmp', JSON.stringify({...d, time: Date.now()}));
  fs.renameSync(file + '.tmp', file);
}
function readDraft(home) {
  try { const d = JSON.parse(fs.readFileSync(path.join(home, 'recovery.json'), 'utf8')); return validDraft(d) ? d : null; }
  catch { return null; }
}
function clearDraft(home, d) {
  const saved = readDraft(home);
  if (saved && saved.pid === d.pid && saved.filename === d.filename && saved.content === d.content)
    fs.unlinkSync(path.join(home, 'recovery.json'));
}
module.exports = {validDraft, writeDraft, readDraft, clearDraft};
