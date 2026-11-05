const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {writeDraft,readDraft,clearDraft}=require('./recovery.cjs');
test('an older save response never clears a newer recovery draft',()=>{
  const home=fs.mkdtempSync(path.join(os.tmpdir(),'rocal-recovery-'));
  try{
    const d={pid:'a'.repeat(32),filename:'main.tex',content:'first'};
    writeDraft(home,d);writeDraft(home,{...d,content:'newer'});
    clearDraft(home,d);assert.equal(readDraft(home).content,'newer');
    clearDraft(home,{...d,content:'newer'});assert.equal(readDraft(home),null);
    assert.throws(()=>writeDraft(home,{...d,content:'a'.repeat(2000001)}));
  }finally{fs.rmSync(home,{recursive:true,force:true});}
});
