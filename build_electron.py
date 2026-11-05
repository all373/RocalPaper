"""Build the supervised backend and a Windows installer with bundled Chromium/TeX."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from build_paper import prepare_tex, copy_if_changed, python_notices

ROOT = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--tex', type=Path, help='Existing verified TinyTeX directory to reuse')
    p.add_argument('--npm', default='npm.cmd')
    args = p.parse_args()
    build = ROOT / 'build'
    build.mkdir(exist_ok=True)
    tex = args.tex.resolve() if args.tex else prepare_tex(build) / 'TinyTeX'
    if not (tex / 'bin/windows/pdflatex.exe').is_file():
        raise RuntimeError('TinyTeX is incomplete')
    bundled = build / 'tex/TinyTeX'
    if tex != bundled:
        shutil.copytree(tex, bundled, dirs_exist_ok=True, copy_function=copy_if_changed)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onedir', '--console', '--noupx',
        '--name', 'RocalPaperWorker', '--paths', str(ROOT),
        '--add-data', f'{ROOT / "paper_studio/ui"};paper_studio/ui',
        '--collect-all', 'pypdfium2', '--collect-all', 'pypdfium2_raw',
        '--exclude-module', 'webview', '--exclude-module', 'tkinter',
        '--distpath', str(build / 'backend'), '--workpath', str(build / 'worker-work'),
        '--specpath', str(build), str(ROOT / 'paper_studio/worker.py')], check=True, cwd=ROOT)
    python_notices(build)
    env = dict(os.environ)
    npm = shutil.which(args.npm) or args.npm
    env['PATH'] = str(Path(npm).resolve().parent) + os.pathsep + env.get('PATH', '')
    subprocess.run([npm, 'run', 'dist'], check=True, cwd=ROOT, env=env)
    print('Installer: ' + str(ROOT / 'dist/electron/RocalPaper-Setup-0.3.0.exe'))


if __name__ == '__main__':
    main()
