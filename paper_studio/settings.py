"""Local settings and lifecycle for an optional existing Rocal LLM runtime."""
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
import logging
from urllib.parse import urlsplit


def local_url(value):
    if not isinstance(value, str):
        raise ValueError('接続先URLを入力してください。')
    parsed = urlsplit(value.rstrip('/'))
    if parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1', 'localhost', '::1'} or parsed.path not in {'', '/v1'} or parsed.query or parsed.fragment or parsed.username:
        raise ValueError('接続先はこのPCのHTTPアドレスのみ指定できます。')
    return value.rstrip('/').removesuffix('/v1')


class Settings:
    def __init__(self, home):
        self.path = Path(home) / 'settings.json'
        self.values = {'llm_url': 'http://127.0.0.1:8771', 'llm_root': ''}
        if Path('D:/rocalLLM/model_catalog.json').is_file():
            self.values['llm_root'] = 'D:/rocalLLM'
        if self.path.is_file():
            try:
                saved = json.loads(self.path.read_text('utf-8'))
                url = local_url(saved['llm_url'])
                if not isinstance(saved.get('llm_root', ''), str):
                    raise ValueError('Invalid model path')
                self.values.update(llm_url=url, llm_root=saved.get('llm_root', ''))
            except (ValueError, KeyError, TypeError):
                backup = self.path.with_name(f'settings-damaged-{time.time_ns()}.json')
                self.path.replace(backup)
                logging.warning('Damaged settings preserved; defaults restored')
        self.workspace = None
        self.context = None
        self.lock = threading.RLock()

    def get(self):
        return dict(self.values, running=self.context is not None)

    def save(self, values):
        with self.lock:
            if self.context is not None:
                raise ValueError('AIを停止してから接続設定を変更してください。')
            url = local_url(values.get('llm_url'))
            root = values.get('llm_root', '')
            if not isinstance(root, str) or len(root) > 1000:
                raise ValueError('モデルフォルダーのパスを確認してください。')
            self.values = {'llm_url': url, 'llm_root': root}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix('.tmp')
            temp.write_text(json.dumps(self.values, ensure_ascii=False, indent=2), 'utf-8')
            os.replace(temp, self.path)
            self.workspace.llm_url = url
            return self.get()

    def start(self):
        with self.lock:
            if self.context is not None:
                return self.get()
            root = Path(self.values['llm_root'])
            if not (root / 'model_catalog.json').is_file():
                raise ValueError('model_catalog.json・models・llama-serverのあるRocal LLMフォルダーを指定してください。')
            if os.name == 'nt':
                result = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True,
                                        creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
                if any(name in result.stdout.lower() for name in [b'rocalstudio.exe', b'qwenplayground.exe']):
                    raise ValueError('モデルの二重ロードを避けるためRocal Studio / QwenPlaygroundを終了してください。')
            import app_runtime
            app_runtime.ROOT = root.resolve()
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', 0))
                port = probe.getsockname()[1]
            context = app_runtime.running_server(port, hidden=True)
            url, _ = context.__enter__()
            self.context = context
            self.workspace.llm_url = url
            return self.get()

    def close(self):
        with self.lock:
            if self.context is not None:
                self.context.__exit__(None, None, None)
                self.context = None
            if self.workspace:
                self.workspace.llm_url = self.values['llm_url']
