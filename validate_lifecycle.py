"""Exercise the packaged backend's shutdown while TeX is still running."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import zipfile
from urllib.request import Request, urlopen
from urllib.error import HTTPError


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--worker', required=True)
    p.add_argument('--tex-root', required=True)
    p.add_argument('--report', type=Path, required=True)
    p.add_argument('--kit', type=Path)
    args = p.parse_args()
    with tempfile.TemporaryDirectory(prefix='rocal-lifecycle-') as temp:
        token = 'test-session-only'
        env = dict(os.environ, ROCAL_SESSION_TOKEN=token)
        # This explicitly excludes system TeX and installed Python from PATH.
        env['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32')
        worker = subprocess.Popen([args.worker, '--home', temp, '--tex-root', args.tex_root],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(worker.stdout.readline)
                port = json.loads(future.result(timeout=30))['port']
            url = f'http://127.0.0.1:{port}/api/'
            def request(route, body=None):
                req = Request(url+route, data=json.dumps(body).encode() if body is not None else None,
                    headers={'Content-Type':'application/json','X-Rocal-Paper':'1','X-Rocal-Session':token})
                with urlopen(req, timeout=120) as response:
                    return json.load(response)
            try:
                urlopen(url+'projects', timeout=3)
                raise AssertionError('Missing session token was accepted')
            except HTTPError as error:
                assert error.code == 403
            pid = request('projects')[0]['id']
            compiled = request('compile', {'id':pid,'entry':'main.tex'})
            assert compiled['ok'] and compiled['pages'] == 1, compiled
            kit_results = []
            if args.kit:
                source = Path(temp) / 'projects' / pid / 'source'
                with zipfile.ZipFile(args.kit) as archive:
                    for name in ['template.tex','Interspeech.cls','IEEEtran.bst','mybib.bib','figure.pdf']:
                        (source / name).write_bytes(archive.read(name))
                for mode in ['camera-ready','review']:
                    if mode == 'review':
                        tex=(source/'template.tex').read_text('utf-8').replace('\\documentclass[cameraready]{Interspeech}','\\documentclass{Interspeech}',1)
                        request('file',{'id':pid,'name':'template.tex','content':tex})
                    kit_result=request('compile',{'id':pid,'entry':'template.tex'})
                    assert kit_result['ok'] and kit_result['pages']==6, kit_result
                    assert 'undefined citations' not in kit_result['log'].split('This is pdfTeX')[-1]
                    kit_results.append({'mode':mode,'pages':kit_result['pages'],'seconds':kit_result['seconds']})
            request('file', {'id':pid,'name':'main.tex','content':r'\documentclass{article}\begin{document}\loop\iftrue\repeat\end{document}'})
            with concurrent.futures.ThreadPoolExecutor() as pool:
                pending = pool.submit(request, 'compile', {'id':pid,'entry':'main.tex'})
                children = []
                deadline = time.monotonic()+10
                while time.monotonic()<deadline:
                    result = subprocess.run(['powershell.exe','-NoProfile','-Command',
                        f'Get-CimInstance Win32_Process -Filter "ParentProcessId = {worker.pid}" | Select-Object -ExpandProperty ProcessId | ConvertTo-Json'],
                        capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
                    if result.stdout.strip():
                        children = json.loads(result.stdout)
                        children = children if isinstance(children,list) else [children]
                        break
                assert children, 'No TeX child observed'
                started = time.perf_counter()
                worker.stdin.close()
                worker.wait(timeout=3)
                seconds = time.perf_counter()-started
                try:
                    pending.result(timeout=3)
                except Exception:
                    pass
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
            kernel.OpenProcess.restype=wintypes.HANDLE
            kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
            kernel.CloseHandle.argtypes=[wintypes.HANDLE]
            for child in children:
                handle=kernel.OpenProcess(0x100000,False,child)
                if handle:
                    try:
                        assert kernel.WaitForSingleObject(handle,3000)==0, 'TeX child survived'
                    finally:
                        kernel.CloseHandle(handle)
            report={'ok':True,'isolated_path':True,'pdf_pages':compiled['pages'],
                'unauthorized_rejected':True,'close_during_compile_seconds':seconds,'tex_children_terminated':True,'interspeech':kit_results}
            args.report.write_text(json.dumps(report,indent=2),'utf-8')
            print(json.dumps(report))
        finally:
            if worker.poll() is None:
                worker.kill()
                worker.wait(timeout=3)


if __name__ == '__main__':
    main()

