const $ = id => document.getElementById(id);
let pid='', filename='', dirty=false, busy=false, snapshot=null, lastLog='', pdfUrl='';
const editor=$('editor');
function notify(text=''){$('notice').textContent=text;$('notice').hidden=!text;}
async function api(path,body){const res=await fetch('/api/'+path,{signal:AbortSignal.timeout(path==='compile'?400000:200000),...(body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Rocal-Paper':'1'},body:JSON.stringify(body)})});const data=await res.json();if(!res.ok)throw Error(data.error||'処理に失敗しました');return data;}
async function action(fn){if(busy)return;busy=true;document.body.dataset.busy='true';const ids=['save','compile','newProject','newFile','project','entry','refresh','export','apply','history'];ids.forEach(id=>$(id).disabled=true);notify();try{await fn();}catch(e){notify(e.name==='TimeoutError'?'処理が時間内に完了しませんでした。原稿は保持されています。':e.message);}finally{busy=false;document.body.dataset.busy='false';ids.forEach(id=>$(id).disabled=false);}}
function counts(){document.body.dataset.dirty=String(dirty);const text=editor.value;$('lineNumbers').textContent=Array.from({length:text.split('\n').length},(_,i)=>i+1).join('\n');$('count').textContent=`${text.trim()?text.trim().split(/\s+/).length:0} words · ${text.length} chars`;$('saveStatus').textContent=dirty?'未保存':'保存済み';}
function invalidateProposal(){snapshot=null;$('suggestion').hidden=true;}
function clearPdf(){if(pdfUrl)URL.revokeObjectURL(pdfUrl);pdfUrl='';$('pdf').removeAttribute('src');$('pdf').hidden=true;$('pages').hidden=true;$('pages').replaceChildren();$('pdfLink').hidden=true;$('previewEmpty').hidden=false;}
let saveQueue=Promise.resolve();
async function save(){
  const target={pid,filename,content:editor.value};
  if(!pid||!filename||!dirty)return;
  const request=saveQueue.catch(()=>{}).then(async()=>{
    await api('file',{id:target.pid,name:target.filename,content:target.content});
    if(window.desktop)await window.desktop.saved(target);
    if(pid===target.pid&&filename===target.filename&&editor.value===target.content){dirty=false;counts();}
  });
  saveQueue=request;return request;
}
function changed(){dirty=true;counts();if(window.desktop)window.desktop.draft({pid,filename,content:editor.value}).catch(e=>notify('復元用下書きの保存に失敗しました。Ctrl+Sで保存してください。 '+e.message));}
setInterval(()=>{if(dirty)save().catch(e=>notify('自動保存に失敗しました。原稿は画面に残っています。 '+e.message));},3000);
async function openFile(name){editor.readOnly=true;try{await save();const result=await api('file?'+new URLSearchParams({id:pid,name}));filename=name;editor.value=result.content;dirty=false;$('filename').textContent=name;invalidateProposal();counts();document.querySelectorAll('#files button').forEach(b=>b.classList.toggle('active',b.dataset.name===name));}finally{editor.readOnly=false;}}
async function refreshFiles(){const files=await api('files?id='+pid);$('files').replaceChildren();const prior=$('entry').value;$('entry').replaceChildren();for(const name of files){const b=document.createElement('button');b.textContent='▤  '+name;b.dataset.name=name;b.classList.toggle('active',name===filename);b.onclick=()=>action(()=>openFile(name));if(/\.(png|jpe?g|pdf|eps)$/i.test(name)){b.disabled=true;b.title='画像・添付ファイル';}$('files').append(b);if(name.endsWith('.tex'))$('entry').add(new Option(name,name));}if(files.includes(prior))$('entry').value=prior;else if(files.includes('main.tex'))$('entry').value='main.tex';return files;}
async function openProject(id){editor.readOnly=true;try{await save();pid=id;filename='';$('project').value=id;const files=await refreshFiles();clearPdf();lastLog='';$('log').textContent='まだ生成していません。';await openFile(files.includes('main.tex')?'main.tex':(files.find(name=>name.endsWith('.tex'))||files[0]));}finally{editor.readOnly=false;}}
async function projects(select){const list=await api('projects');$('project').replaceChildren(...list.map(p=>new Option(p.title,p.id)));await openProject(select||list[0].id);}
async function status(){const s=await api('status');$('engineStatus').textContent=s.engine?'● LaTeX ready':'LaTeX未検出';$('llmStatus').textContent=s.model_error||'● 接続済み · '+s.llm_url;const old=$('model').value;$('model').replaceChildren(...s.models.map(m=>new Option(m.id,m.id)));if(!s.models.length)$('model').add(new Option('モデル未接続',''));else if(s.models.some(m=>m.id===old))$('model').value=old;else if(s.models.some(m=>m.id==='Qwen3-4B-Instruct-2507'))$('model').value='Qwen3-4B-Instruct-2507';}
editor.addEventListener('input',changed);editor.addEventListener('scroll',()=>{$('lineNumbers').scrollTop=editor.scrollTop;});editor.addEventListener('select',()=>{const n=editor.selectionEnd-editor.selectionStart;$('selectionInfo').textContent=n?`${n}文字を選択中`:'未選択：ファイル全体が対象（最大10,000文字）';});
editor.addEventListener('keydown',e=>{if(e.key==='Tab'){e.preventDefault();editor.setRangeText('  ',editor.selectionStart,editor.selectionEnd,'end');changed();}});
window.addEventListener('beforeunload',e=>{if(dirty&&!window.desktop){e.preventDefault();e.returnValue='';}});
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='s'){e.preventDefault();action(save);}});
$('save').onclick=()=>action(save);
$('project').onchange=()=>{const next=$('project').value;$('project').value=pid;action(()=>openProject(next));};
$('newProject').onclick=async()=>{const title=await askName('プロジェクト名');if(title)action(async()=>{await save();const p=await api('projects',{title});await projects(p.id);});};
$('newFile').onclick=async()=>{const name=await askName('ファイル名（例：sections/methods.tex）');if(name)action(async()=>{await save();const files=await api('files?id='+pid);if(files.includes(name))throw Error('同名のファイルが存在します。');await api('file',{id:pid,name,content:''});await refreshFiles();await openFile(name);});};
$('compile').onclick=()=>action(async()=>{await save();clearPdf();$('compile').textContent='生成中…';try{const result=await api('compile',{id:pid,entry:$('entry').value});lastLog=result.log;$('log').textContent=lastLog;$('logs').open=!result.ok;if(!result.ok)throw Error('PDFを生成できませんでした。ログを確認してください。');const res=await fetch('/api/pdf?id='+pid);if(!res.ok)throw Error('PDFを取得できませんでした。');pdfUrl=URL.createObjectURL(await res.blob());$('pdf').src=pdfUrl;$('pdf').hidden=!!result.pages;if(result.pages){$('pages').hidden=false;for(let page=1;page<=result.pages;page++){const image=document.createElement('img');image.alt=`PDF page ${page}`;image.src='/api/page?'+new URLSearchParams({id:pid,page,t:Date.now()});$('pages').append(image);}}$('previewEmpty').hidden=true;$('pdfLink').href=pdfUrl;$('pdfLink').hidden=false;notify(result.cached?'変更がないため保存済みPDFを表示しました。':`PDF生成完了（${result.seconds?.toFixed(2)||'?'}秒）`);}finally{$('compile').textContent='▶ PDFを生成';}});
$('export').onclick=()=>action(async()=>{await save();const res=await fetch('/api/export?id='+pid);if(!res.ok)throw Error('ZIPを書き出せませんでした。');const url=URL.createObjectURL(await res.blob());const a=document.createElement('a');a.href=url;a.download='rocal-paper.zip';a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);});
$('refresh').onclick=()=>action(status);
let aiBusy=false;
$('assist').onclick=async()=>{
  if(aiBusy)return;
  const task=$('task').value,start=editor.selectionStart,end=editor.selectionEnd,source=editor.value;
  const origin={pid,filename,source,start:start===end?0:start,end:start===end?source.length:end};
  const text=task==='howto'?$('instruction').value:task==='error'?lastLog.slice(-8000):(start===end?source:source.slice(start,end));
  try{
    if(!$('model').value)throw Error('設定からローカルAIを起動してください。「TeXを学ぶ」はAIなしでも使えます。');
    if(!text.trim())throw Error(task==='howto'?'「追加の指示」に、やりたいことを書いてください。例：2列の表を作りたい。':'対象の文章・TeXを選択してください。');
    aiBusy=true;$('assist').disabled=true;invalidateProposal();$('assist').textContent='考えています… 編集は続けられます';
    const response=await api('assist',{task,text,model:$('model').value,instruction:task==='howto'?'':$('instruction').value});
    if(pid!==origin.pid||filename!==origin.filename){notify('別のファイルに移動したためAI回答の反映を中止しました。');return;}
    $('answer').textContent=response.text+(response.example_check?'\n\n【例の動作確認】\n'+response.example_check.message:'');$('suggestion').hidden=false;
    $('apply').hidden=!['polish','translate'].includes(task);snapshot={...origin,text:response.text};
  }catch(e){notify(e.message);}finally{aiBusy=false;$('assist').disabled=false;$('assist').textContent='✧ AIに相談する';}
};
$('apply').onclick=()=>action(async()=>{if(!snapshot||snapshot.pid!==pid||snapshot.filename!==filename||snapshot.source!==editor.value)throw Error('生成後に原稿が変更されています。文章を選び直して再生成してください。');await save();editor.focus();editor.setSelectionRange(snapshot.start,snapshot.end);const inserted=document.execCommand('insertText',false,snapshot.text);if(!inserted)editor.setRangeText(snapshot.text,snapshot.start,snapshot.end,'select');changed();invalidateProposal();});
$('copy').onclick=async()=>{try{await navigator.clipboard.writeText($('answer').textContent);notify('提案をコピーしました。');}catch(e){notify(e.message);}};
action(async()=>{await projects();await checkRecovery();});
status().catch(e=>notify(e.message));

function askName(title){$('nameTitle').textContent=title;$('nameInput').value='';$('nameDialog').returnValue='cancel';$('nameDialog').showModal();return new Promise(resolve=>{$('nameDialog').addEventListener('close',()=>resolve($('nameDialog').returnValue==='ok'?$('nameInput').value:null),{once:true});});}
function showSettings(s){$('llmUrl').value=s.llm_url||'';$('llmRoot').value=s.llm_root||'';$('runtimeState').textContent=s.running?'● アプリが起動したAIは実行中':'AIの起動・停止はこのアプリが管理します。';$('startAI').disabled=!!s.running;$('stopAI').disabled=!s.running;$('saveSettings').disabled=!!s.running;}
$('settingsButton').onclick=()=>action(async()=>{const s=await api('settings');if(s.desktop===false)throw Error('ブラウザー版の接続先は起動引数で指定してください。');showSettings(s);$('settingsError').textContent='';$('settingsDialog').showModal();});
$('closeSettings').onclick=()=>{$('settingsDialog').close();};
async function settingAction(operation){$('settingsError').textContent='処理中…';for(const id of ['saveSettings','startAI','stopAI'])$(id).disabled=true;try{showSettings(await operation());await status();$('settingsError').textContent='完了しました。';}catch(e){$('settingsError').textContent=e.message;showSettings(await api('settings'));}finally{$('closeSettings').disabled=false;}}
$('saveSettings').onclick=()=>settingAction(()=>api('settings',{llm_url:$('llmUrl').value,llm_root:$('llmRoot').value}));
$('startAI').onclick=()=>settingAction(async()=>{await api('settings',{llm_url:$('llmUrl').value,llm_root:$('llmRoot').value});return api('settings/start',{});});
$('stopAI').onclick=()=>settingAction(()=>api('settings/stop',{}));

let oldVersions=[];
$('history').onclick=()=>action(async()=>{
  await save();oldVersions=await api('history?'+new URLSearchParams({id:pid,name:filename}));
  $('revision').replaceChildren(...oldVersions.map((v,i)=>new Option(new Date(v.time*1000).toLocaleString(),i)));
  $('revisionText').textContent=oldVersions[0]?.content||'まだ以前の保存内容がありません。';
  $('restoreRevision').disabled=!oldVersions.length;$('historyDialog').showModal();
});
$('revision').onchange=()=>{$('revisionText').textContent=oldVersions[Number($('revision').value)].content;};
$('restoreRevision').onclick=()=>action(async()=>{await save();editor.value=oldVersions[Number($('revision').value)].content;changed();await save();invalidateProposal();$('historyDialog').close();notify('以前の内容を復元しました。復元前の内容も履歴に残っています。');});
$('closeHistory').onclick=()=>$('historyDialog').close();
async function checkRecovery(){
  if(!window.desktop)return;
  const draft=await window.desktop.recovery();if(!draft)return;
  $('recoveryText').textContent=draft.filename+' — '+new Date(draft.time).toLocaleString();
  $('recoveryDialog').showModal();
  $('recoverDraft').onclick=()=>action(async()=>{await openProject(draft.pid);await openFile(draft.filename);editor.value=draft.content;changed();await save();$('recoveryDialog').close();notify('前回の未保存分を復元しました。');});
}
$('laterRecovery').onclick=()=>$('recoveryDialog').close();
$('diagnostics').onclick=()=>window.desktop?.logs();
const lessons=[
  {title:'1. 見出しと段落',code:'\\section{Introduction}\nWrite your first paragraph here.\n\nWrite the next paragraph here.',explain:'本文の中（\\begin{document} と \\end{document} の間）に挿入します。sectionは見出し、空行は段落の区切りです。練習：IntroductionをMethodsに変えてPDFを生成してみましょう。'},
  {title:'2. 数式',code:'The mean is $\\mu$.\n\\begin{equation}\n  y = ax + b\n\\end{equation}',explain:'本文に挿入します。$で囲むと文中の数式、equationで囲むと独立した番号付き数式になります。練習：bを0に変え、PDFの変化を確認しましょう。'},
  {title:'3. 表',code:'\\begin{table}[ht]\n\\centering\n\\begin{tabular}{lr}\nMethod & Value \\\\\n\\hline\nExample & 0.0 \\\\\n\\end{tabular}\n\\caption{Example table}\n\\label{tab:example}\n\\end{table}',explain:'本文に挿入します。lは左寄せ、rは右寄せ、&は列の区切り、\\\\は行の終わりです。数値は練習用の例です。練習：行を1つ追加しましょう。'},
  {title:'4. 図と参照',code:'\\begin{figure}[ht]\n\\centering\n\\includegraphics[width=0.8\\linewidth]{figure.pdf}\n\\caption{Example figure}\n\\label{fig:example}\n\\end{figure}\nSee Figure~\\ref{fig:example}.',explain:'本文に挿入します。事前に画像ファイルを用意し、前置き（documentより前）に \\usepackage{graphicx} が必要です。Interspeechのkitにはfigure.pdfがあります。練習：幅を0.5に変更しましょう。'},
  {title:'5. 引用',code:'Previous work~\\cite{your_bib_key} supports this approach.',explain:'本文に挿入します。your_bib_keyは.bibファイルの実在するキーに置き換えます。テンプレートにbibliographyの設定が必要です。練習：Interspeechのmybib.bibでキーを1つ探し、引用してみましょう。出典はAIに作らせず実物を確認します。'}
];
$('lesson').replaceChildren(...lessons.map((v,i)=>new Option(v.title,i)));
function showLesson(){const l=lessons[Number($('lesson').value)];$('lessonCode').textContent=l.code;$('lessonExplanation').textContent=l.explain;}
$('lesson').onchange=showLesson;
$('learn').onclick=()=>{showLesson();$('learnDialog').showModal();};
$('closeLearn').onclick=()=>$('learnDialog').close();
$('insertLesson').onclick=()=>action(async()=>{await save();const text=lessons[Number($('lesson').value)].code;editor.setRangeText(text,editor.selectionStart,editor.selectionEnd,'select');changed();$('learnDialog').close();notify('カーソル位置へ練習例を挿入しました。配置を確認してPDFを生成してください。');});
