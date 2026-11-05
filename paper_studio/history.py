"""Bounded per-file recovery history, stored outside exported source files."""
import hashlib
import json
import os
from pathlib import Path
import time
import uuid


def folder(project, name):
    return Path(project) / 'history' / hashlib.sha256(name.encode()).hexdigest()


def remember(project, name, content):
    root = folder(project, name)
    root.mkdir(parents=True, exist_ok=True)
    items = sorted(root.glob('*.json'))
    if items and json.loads(items[-1].read_text('utf-8'))['content'] == content:
        return
    entry = {'id': f'{time.time_ns()}-{uuid.uuid4().hex}', 'name': name, 'time': time.time(), 'content': content}
    target = root / (entry['id'] + '.json')
    temp = target.with_suffix('.tmp')
    temp.write_text(json.dumps(entry, ensure_ascii=False), 'utf-8')
    os.replace(temp, target)
    # History is deliberately bounded; current source is never pruned.
    for old in sorted(root.glob('*.json'))[:-40]:
        old.unlink()


def revisions(project, name):
    result = []
    for path in sorted(folder(project, name).glob('*.json'), reverse=True):
        try:
            item = json.loads(path.read_text('utf-8'))
            result.append({k: item[k] for k in ('id', 'time', 'content')})
        except (OSError, ValueError, KeyError):
            continue
    return result
