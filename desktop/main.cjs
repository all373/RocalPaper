'use strict';
const {app, BrowserWindow, ipcMain, dialog, shell, Menu} = require('electron');
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const readline = require('node:readline');
const {writeDraft, readDraft, clearDraft} = require('./recovery.cjs');

const option = name => { const i = process.argv.indexOf(name); return i < 0 ? null : process.argv[i + 1]; };
const base = app.isPackaged ? path.dirname(process.execPath) : path.resolve(__dirname, '..');
const portableBase = [base, path.dirname(base)].find(p=>fs.existsSync(path.join(p, 'portable.json')));
const home = path.resolve(option('--data-dir') || (portableBase ? path.join(portableBase, 'data') : path.join(process.env.LOCALAPPDATA || app.getPath('appData'), 'RocalPaper')));
fs.mkdirSync(home, {recursive:true});
fs.mkdirSync(path.join(home, 'logs'), {recursive:true});
app.setPath('userData', path.join(home, 'shell'));
const logFile = path.join(home, 'logs', 'desktop.log');
if (fs.existsSync(logFile) && fs.statSync(logFile).size > 1000000) fs.renameSync(logFile, logFile+'.previous');
function log(message) { fs.appendFileSync(logFile, new Date().toISOString()+' '+message+'\n'); }
let win, worker, origin, closing = false, closePrompt = false, startupFinished = false;
const token = crypto.randomBytes(32).toString('hex');
const smoke = option('--smoke-report');
const lock = app.requestSingleInstanceLock();
if (!lock) app.quit();
else {
  app.on('second-instance', () => { if (win) {win.restore();win.focus();} });
  app.on('window-all-closed', () => shutdown());
  app.on('before-quit', event => { if (!closing) {event.preventDefault(); if (win) win.close(); else shutdown();} });
  app.whenReady().then(start).catch(error => fail(error));
}
function shutdown() {
  if (closing) return;
  closing = true;
  log('Shutdown requested');
  // No renderer/AI/compiler acknowledgement is required to close.
  if (worker && worker.exitCode === null) {
    worker.stdin.end();
    worker.once('exit', () => app.exit(0));
    setTimeout(() => {worker.kill(); app.exit(0);}, 2500);
  } else app.exit(0);
}
function fail(error) {
  log(String(error.stack || error));
  if (smoke) fs.writeFileSync(smoke, JSON.stringify({ok:false,error:String(error)}));
  else dialog.showErrorBox('RocalPaper — 起動できません', '処理サービスを起動できませんでした。旧版が起動中なら終了してください。\n修復にはインストーラーを再実行してください。\nログ: '+logFile+'\n'+error.message);
  shutdown();
}
async function start() {
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    {label:'ファイル',submenu:[{label:'終了',accelerator:'Alt+F4',click:()=>win.close()}]},
    {label:'編集',submenu:[{role:'undo'},{role:'redo'},{type:'separator'},{role:'cut'},{role:'copy'},{role:'paste'},{role:'selectAll'}]},
    {label:'表示',submenu:[{role:'zoomIn'},{role:'zoomOut'},{role:'resetZoom'}]},
    {label:'ヘルプ',submenu:[{label:'診断ログを開く',click:()=>shell.openPath(path.join(home,'logs'))},
      {label:'バージョン情報',click:()=>dialog.showMessageBox(win,{message:'RocalPaper '+app.getVersion(),detail:'ローカル論文執筆・LaTeX学習\nデータ: '+home})}]}
  ]));
  const backend = app.isPackaged ? path.join(process.resourcesPath,'backend','RocalPaperWorker.exe') : process.env.ROCAL_PYTHON;
  if (!backend) throw new Error('ROCAL_PYTHON must point to the development Python environment');
  const args = app.isPackaged ? [] : ['-m','paper_studio.worker'];
  args.push('--home',home,'--tex-root',option('--tex-root') || path.join(app.isPackaged ? process.resourcesPath : base,'tex'));
  worker = spawn(backend,args,{cwd: app.isPackaged ? path.dirname(backend) : base,windowsHide:true,stdio:['pipe','pipe','pipe'],env:{...process.env,ROCAL_SESSION_TOKEN:token}});
  worker.stderr.on('data', chunk => log(chunk.toString().slice(0,4000)));
  worker.stdin.on('error', error => log('Worker input: '+error.message));
  const ready = new Promise((resolve,reject) => {
    const deadline = setTimeout(()=>reject(new Error('起動が30秒以内に完了しませんでした。')),30000);
    const lines = readline.createInterface({input:worker.stdout});
    lines.once('line', line => {clearTimeout(deadline);try { const value=JSON.parse(line); if(!Number.isInteger(value.port)||value.port<1||value.port>65535)throw Error('Invalid backend port');resolve(value.port); } catch(e){reject(e);} });
    worker.once('error', e => {clearTimeout(deadline);reject(e);});
    worker.once('exit', code => {clearTimeout(deadline);reject(new Error('Backend exited: '+code));});
  });
  worker.on('exit', code => {
    log('Backend exited: '+code);
    if (!closing && startupFinished) {
      dialog.showMessageBox(win,{type:'error',message:'処理サービスが停止しました。',detail:'保存済みの原稿と復元用下書きは保持されています。アプリを再起動してください。',buttons:['終了']}).then(shutdown);
    }
  });
  origin='http://127.0.0.1:'+await ready;
  win = new BrowserWindow({width:1440,height:920,minWidth:1050,minHeight:700,show:false,backgroundColor:'#f5f6f3',webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true}});
  win.webContents.session.webRequest.onBeforeSendHeaders((details,callback)=>{
    if (details.url.startsWith(origin+'/')) details.requestHeaders['X-Rocal-Session']=token;
    callback({requestHeaders:details.requestHeaders});
  });
  win.webContents.session.setPermissionRequestHandler((_wc,_permission,callback)=>callback(false));
  win.webContents.setWindowOpenHandler(()=>({action:'deny'}));
  win.webContents.on('will-navigate',(event,url)=>{if(!url.startsWith(origin+'/'))event.preventDefault();});
  const validSender = event => event.sender === win.webContents && event.senderFrame.url.startsWith(origin+'/');
  for (const [name,fn] of Object.entries({draft:d=>writeDraft(home,d),saved:d=>clearDraft(home,d),recovery:()=>readDraft(home),logs:()=>shell.openPath(path.join(home,'logs')),version:()=>app.getVersion()}))
    ipcMain.handle(name,(event,arg)=>{if(!validSender(event))throw Error('Invalid sender');return fn(arg);});
  win.on('close', async event => {
    event.preventDefault();
    if (closePrompt || closing) return;
    closePrompt = true;
    if (readDraft(home)) {
      const answer=await dialog.showMessageBox(win,{type:'question',message:'未保存の変更があります。',detail:'変更は復元用下書きとして保持されています。次回起動時に復元できます。',buttons:['終了する','編集に戻る'],defaultId:1,cancelId:1});
      if(answer.response!==0){closePrompt=false;return;}
    }
    win.destroy(); shutdown();
  });
  win.on('unresponsive',async()=>{
    log('Renderer unresponsive');
    const answer=await dialog.showMessageBox(win,{message:'画面の応答がありません。',detail:'保存済み原稿と復元用下書きを保持して終了できます。',buttons:['待つ','終了する'],cancelId:0});
    if(answer.response===1){win.destroy();shutdown();}
  });
  win.webContents.on('render-process-gone',(_event,details)=>{
    log('Renderer gone: '+details.reason);
    if(!closing) dialog.showMessageBox(win,{message:'画面の処理が停止しました。',detail:'復元用下書きを保持しています。',buttons:['再読込','終了']}).then(({response})=>{if(response===0)win.reload();else{win.destroy();shutdown();}});
  });
  await win.loadURL(origin+'/');
  startupFinished = true;
  log('Window ready');
  if(smoke){
    fs.writeFileSync(smoke,JSON.stringify({ok:true,version:app.getVersion(),home,backendPid:worker.pid}));
    win.destroy();shutdown();
  } else win.show();
}
