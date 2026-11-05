"""Supervised local backend. The desktop owns its stdin pipe and lifetime."""
import argparse
import ctypes
import faulthandler
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
from http.server import ThreadingHTTPServer

from paper_studio.server import Workspace, Handler
from paper_studio.settings import Settings
from process_job import ProcessJob


def render_pdf(pdf, target):
    import pypdfium2 as pdfium
    with pdfium.PdfDocument(pdf) as document:
        for index in range(len(document)):
            page = document[index]
            bitmap = page.render(scale=min(2, 1400 / page.get_width()))
            try:
                bitmap.to_pil().save(Path(target) / f'page-{index + 1}.png')
            finally:
                bitmap.close()
                page.close()
        print(json.dumps({'pages': len(document)}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--home', type=Path)
    parser.add_argument('--tex-root', type=Path)
    parser.add_argument('--render-pdf', nargs=2)
    args = parser.parse_args()
    if args.render_pdf:
        with (Path(args.render_pdf[1]) / 'render-diagnostic.log').open('w') as trace:
            faulthandler.enable(trace)
            faulthandler.dump_traceback_later(15, file=trace)
            try:
                render_pdf(*args.render_pdf)
            finally:
                faulthandler.cancel_dump_traceback_later()
        return
    args.home.mkdir(parents=True, exist_ok=True)
    logs = args.home / 'logs'
    logs.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, handlers=[RotatingFileHandler(logs / 'backend.log', maxBytes=1_000_000, backupCount=3, encoding='utf-8')])
    fault = (logs / 'native-fault.log').open('a', encoding='utf-8')
    faulthandler.enable(fault)
    # All descendants, including TeX and inference engines, die with this worker.
    job = ProcessJob(SimpleNamespace(_handle=-1)) if os.name == 'nt' else None
    def parent_pipe():
        for _ in sys.stdin:
            pass
        os._exit(0)
    threading.Thread(target=parent_pipe, daemon=True).start()
    import msvcrt
    lock = (args.home / '.instance.lock').open('a+b')
    lock.seek(0)
    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    settings = Settings(args.home)
    engine = args.tex_root / 'TinyTeX/bin/windows/pdflatex.exe'
    if not engine.is_file():
        raise RuntimeError('同梱TeXが見つかりません。インストーラーで修復してください。')
    ws = Workspace(args.home / 'projects', settings.values['llm_url'], str(engine))
    settings.workspace = ws
    if not ws.projects():
        ws.create('My Research Paper')
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    server.workspace, server.settings = ws, settings
    server.auth_token = os.environ['ROCAL_SESSION_TOKEN']
    print(json.dumps({'port': server.server_port}), flush=True)
    logging.info('Backend ready')
    try:
        server.serve_forever()
    finally:
        server.server_close()
        settings.close()
        lock.close()
        if job:
            job.close()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        logging.exception('Backend failed')
        raise
