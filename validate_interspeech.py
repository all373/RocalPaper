"""Download the official 2026 kit and compile both modes using bundled TeX."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import time
import urllib.request
import zipfile

from paper_studio.server import Workspace, TEXT_EXT

KIT_URL = 'https://drive.google.com/uc?export=download&id=1Nq1j_1AfOtadLkBx71-vLVLxZOaiAnzs'
KIT_SHA256 = '7cddd7ab6136e8ca0157b9dbd479cb016f321cd54dff6582dffa8e059980a712'
OFFICIAL_PAGE = 'https://interspeech2026.org/pages/author-resources/submission-policy'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-root', type=Path, required=True)
    args = parser.parse_args()
    root = args.app_root.resolve()
    report_dir = root / 'validation' / 'interspeech2026'
    report_dir.mkdir(parents=True, exist_ok=True)
    archive = report_dir / 'paper-kit.zip'
    if not archive.is_file():
        urllib.request.urlretrieve(KIT_URL, archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != KIT_SHA256:
        raise RuntimeError('The official paper kit has changed; review the new version before updating the checksum.')
    ws = Workspace(root / 'data/projects', 'http://127.0.0.1:1', str(root / 'tex/TinyTeX/bin/windows/pdflatex.exe'))
    results = []
    for mode in ['camera-ready', 'review']:
        title = f'Interspeech 2026 — {mode} validation'
        # Re-running validation never overwrites a user-edited validation project.
        project = ws.create(title)
        source = ws.project(project['id']) / 'source'
        (source / 'main.tex').unlink()
        with zipfile.ZipFile(archive) as zipped:
            for info in zipped.infolist():
                if Path(info.filename).name != info.filename:
                    raise ValueError('Unexpected archive layout')
                if Path(info.filename).suffix in TEXT_EXT or info.filename == 'figure.pdf':
                    (source / info.filename).write_bytes(zipped.read(info))
        if mode == 'review':
            tex = (source / 'template.tex').read_text('utf-8')
            tex = tex.replace('\\documentclass[cameraready]{Interspeech}', '\\documentclass{Interspeech}', 1)
            (source / 'template.tex').write_text(tex, 'utf-8')
        started = time.perf_counter()
        result = ws.compile(project['id'], 'template.tex', force=True)
        seconds = time.perf_counter() - started
        (report_dir / f'{mode}.log').write_text(result['log'], 'utf-8')
        if not result['ok']:
            raise RuntimeError(result['log'][-4000:])
        shutil.copy2(ws.project(project['id']) / 'preview.pdf', report_dir / f'{mode}.pdf')
        last_pass = result['log'].split('This is pdfTeX')[-1]
        unresolved = bool(re.search(r'(undefined citations|undefined references|Citation .+ undefined|Reference .+ undefined)', last_pass))
        cached_start = time.perf_counter()
        cached = ws.compile(project['id'], 'template.tex')
        results.append({'mode': mode, 'project_id': project['id'], 'entry': 'template.tex',
                        'pages': result['pages'], 'seconds': seconds, 'cached_seconds': time.perf_counter()-cached_start,
                        'cache_hit': cached['cached'], 'unresolved_references': unresolved})
        if unresolved:
            raise RuntimeError('Unresolved citations/references remain')
    report = {'official_page': OFFICIAL_PAGE, 'kit_url': KIT_URL, 'kit_sha256': KIT_SHA256,
              'engine': ws.engine, 'results': results}
    (report_dir / 'results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
