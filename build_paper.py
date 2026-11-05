"""Build a portable Windows app; only the build machine needs Python/network."""
import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile

TEX_VERSION = 'v2026.11'
TEX_URL = f'https://github.com/rstudio/tinytex-releases/releases/download/{TEX_VERSION}/TinyTeX-{TEX_VERSION}.zip'
TEX_SHA256 = 'a13d14ba987873d1bdf81773f5bdfcc34537882b825dd2134f61eb6ee21d5f69'
SOURCE = Path(__file__).resolve().parent


def prepare_tex(cache):
    archive = cache / f'TinyTeX-{TEX_VERSION}.zip'
    if not archive.is_file():
        print('Downloading pinned TinyTeX distribution (247 MB)...', flush=True)
        partial = archive.with_suffix('.part')
        urllib.request.urlretrieve(TEX_URL, partial)
        partial.replace(archive)
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != TEX_SHA256:
        raise RuntimeError('TinyTeX checksum mismatch. Remove the cached archive and retry.')
    folder = cache / 'tex'
    stamp = folder / '.verified-sha256'
    if not stamp.is_file() or stamp.read_text('ascii') != TEX_SHA256:
        folder.mkdir(exist_ok=True)
        with zipfile.ZipFile(archive) as zipped:
            for entry in zipped.infolist():
                dest = (folder / entry.filename).resolve()
                if not dest.is_relative_to(folder.resolve()):
                    raise RuntimeError('Archive entry escapes extraction directory')
            zipped.extractall(folder)
        stamp.write_text(TEX_SHA256, 'ascii')
    return folder


def python_notices(destination):
    notices = destination / 'licenses' / 'python-packages'
    notices.mkdir(parents=True, exist_ok=True)
    inventory = []
    for dist in metadata.distributions():
        name = dist.metadata['Name']
        inventory.append({'name': name, 'version': dist.version, 'license': dist.metadata.get('License-Expression', dist.metadata.get('License', 'See package notices'))})
        for file in dist.files or []:
            if any(word in file.name.lower() for word in ('license', 'copying', 'notice')) and '.dist-info/' in str(file).replace('\\', '/'):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    target = notices / name / Path(*file.parts[1:])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    (destination / 'licenses' / 'python-inventory.json').write_text(json.dumps(inventory, indent=2), 'utf-8')


def copy_if_changed(source, destination):
    source, destination = Path(source), Path(destination)
    if destination.is_file():
        a, b = source.stat(), destination.stat()
        if a.st_size == b.st_size and a.st_mtime_ns == b.st_mtime_ns:
            return str(destination)
    return shutil.copy2(source, destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=SOURCE / 'build')
    parser.add_argument('--output', type=Path, default=SOURCE / 'dist' / 'RocalPaper')
    parser.add_argument('--reuse-tex', action='store_true', help='Keep the existing output TeX distribution; do not download or copy it')
    args = parser.parse_args()
    cache, destination = args.cache.resolve(), args.output.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    if args.reuse_tex:
        if not (destination / 'tex/TinyTeX/bin/windows/pdflatex.exe').is_file():
            raise RuntimeError('--reuse-tex requires an existing bundled TeX directory')
        tex = destination / 'tex'
    else:
        tex = prepare_tex(cache)
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onedir', '--windowed', '--noupx',
                    '--name', 'RocalPaper', '--contents-directory', '_internal',
                    '--paths', str(SOURCE), '--add-data', f'{SOURCE / "paper_studio/ui"};paper_studio/ui',
                    '--collect-all', 'pypdfium2', '--collect-all', 'pypdfium2_raw',
                    '--exclude-module', 'tkinter', '--exclude-module', 'PyQt5', '--exclude-module', 'PySide6',
                    '--distpath', str(cache / 'dist'), '--workpath', str(cache / 'work'),
                    '--specpath', str(cache), str(SOURCE / 'paper_studio/desktop.py')], check=True, cwd=SOURCE)
    built = cache / 'dist' / 'RocalPaper'
    if destination == built:
        raise ValueError('Output must differ from the staging folder')
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(built, destination, dirs_exist_ok=True, copy_function=copy_if_changed)
    print('Bundling TinyTeX...', flush=True)
    if not args.reuse_tex:
        shutil.copytree(tex / 'TinyTeX', destination / 'tex' / 'TinyTeX', dirs_exist_ok=True, copy_function=copy_if_changed)
    for name in ['README.md', 'LICENSE', 'THIRD_PARTY.md', 'VALIDATION.md']:
        shutil.copy2(SOURCE / name, destination / name)
    python_notices(destination)
    (destination / 'build-info.json').write_text(json.dumps({'app_version': '0.2.0', 'tex_reused': args.reuse_tex, 'tinytex_version': TEX_VERSION,
        'tinytex_url': TEX_URL, 'tinytex_sha256': TEX_SHA256, 'python': sys.version}, indent=2), 'utf-8')
    report = destination / 'self-test.json'
    report.unlink(missing_ok=True)
    subprocess.run([str(destination / 'RocalPaper.exe'), '--self-test', str(report)], check=True, timeout=180)
    result = json.loads(report.read_text('utf-8'))
    if not result['ok']:
        raise RuntimeError(result)
    print(f'Built and tested: {destination / "RocalPaper.exe"}', flush=True)


if __name__ == '__main__':
    main()
