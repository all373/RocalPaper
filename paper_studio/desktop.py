"""Native Windows application with bundled Python, TinyTeX and PDFium."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer

from paper_studio.server import Handler, Workspace
from paper_studio.settings import Settings


def application_root():
    return Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]


def bundled_engine(root):
    engine = root / 'tex' / 'TinyTeX' / 'bin' / 'windows' / 'pdflatex.exe'
    if not engine.is_file():
        raise RuntimeError('同梱のTeXが見つかりません。RocalPaperフォルダー全体を展開してください。')
    return engine


def data_home(root, override=None):
    if override:
        return Path(override).resolve()
    if (root / 'portable.json').is_file():
        return root / 'data'
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'RocalPaper'


def self_test(root, output):
    # Never fall back to a machine-installed TeX or an external renderer.
    os.environ['PATH'] = str(Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32')
    os.environ['HTTP_PROXY'] = 'http://127.0.0.1:1'
    os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:1'
    with tempfile.TemporaryDirectory(prefix='rocal-paper-clean-') as temp:
        ws = Workspace(Path(temp) / 'projects', 'http://127.0.0.1:1', str(bundled_engine(root)))
        pid = ws.create('Portable smoke test')['id']
        ws.save(pid, 'refs.bib', '@article{sample,author={Example, A.},title={Example reference},journal={Test Journal},year={2026}}')
        text = ws.file(pid, 'main.tex').read_text('utf-8').replace('\\end{document}', 'A citation~\\cite{sample}.\n\\bibliographystyle{plain}\n\\bibliography{refs}\n\\end{document}')
        ws.save(pid, 'main.tex', text)
        result = ws.compile(pid, 'main.tex')
        if not result['ok'] or result['pages'] < 1 or 'undefined citations' in result['log'].split('This is pdfTeX')[-1]:
            raise RuntimeError(result['log'])
        report = {'ok': True, 'engine': ws.engine, 'pages': result['pages'], 'isolated_path': os.environ['PATH'],
                  'pdfium': True, 'bibtex': True, 'python_installed_required': False, 'tex_installed_required': False}
        Path(output).write_text(json.dumps(report, indent=2), 'utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', metavar='REPORT_JSON')
    parser.add_argument('--tex-root', type=Path)
    parser.add_argument('--data-dir', type=Path)
    args = parser.parse_args()
    root = args.tex_root or application_root()
    if args.self_test:
        self_test(root, args.self_test)
        return
    import webview
    home = data_home(root, args.data_dir)
    home.mkdir(parents=True, exist_ok=True)
    # One process per data folder, released automatically even after a crash.
    import msvcrt
    instance = (home / '.instance.lock').open('a+b')
    instance.seek(0)
    try:
        msvcrt.locking(instance.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        instance.close()
        ctypes.windll.user32.MessageBoxW(None, 'Rocal Paperはすでに起動しています。', 'Rocal Paper', 0x40)
        return
    settings = Settings(home)
    ws = Workspace(home / 'projects', settings.values['llm_url'], str(bundled_engine(root)))
    settings.workspace = ws
    if not ws.projects():
        ws.create('My Research Paper')
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.workspace = ws
    server.settings = settings
    threading.Thread(target=server.serve_forever, daemon=True).start()
    webview.settings['ALLOW_DOWNLOADS'] = True
    webview.settings['ALLOW_FILE_URLS'] = False
    window = webview.create_window('Rocal Paper', f'http://127.0.0.1:{server.server_port}', width=1440, height=920,
                                  min_size=(1050, 700), background_color='#f5f6f3', text_select=True)
    def closing():
        try:
            if window.evaluate_js("document.body.dataset.dirty === 'true'"):
                return window.create_confirmation_dialog('未保存の原稿', '保存されていない変更を破棄して終了しますか？')
            if window.evaluate_js("document.body.dataset.busy === 'true'"):
                return False
        except Exception:
            return True
    window.events.closing += closing
    try:
        webview.start(gui='edgechromium', private_mode=False, storage_path=str(home / 'webview'))
    finally:
        server.shutdown()
        server.server_close()
        settings.close()
        instance.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        if '--self-test' in sys.argv:
            index = sys.argv.index('--self-test')
            Path(sys.argv[index + 1]).write_text(json.dumps({'ok': False, 'error': str(error)}), 'utf-8')
        elif os.name == 'nt':
            ctypes.windll.user32.MessageBoxW(None, str(error), 'Rocal Paper — 起動エラー', 0x10)
        raise
