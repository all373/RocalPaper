import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer

from server import Workspace, Handler


class PaperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ws = Workspace(self.temp.name, 'http://127.0.0.1:8771')
        self.pid = self.ws.create('A test paper')['id']

    def test_paths_and_persistent_save(self):
        for name in ['../outside.tex', '/outside.tex', 'C:/outside.tex', 'a/../../out.tex', 'a\\out.tex', '.hidden.tex']:
            with self.assertRaises(ValueError):
                self.ws.save(self.pid, name, 'bad')
        self.ws.save(self.pid, 'sections/results.tex', 'Results with α')
        reopened = Workspace(self.temp.name, 'http://localhost:8771')
        self.assertEqual(reopened.file(self.pid, 'sections/results.tex').read_text('utf-8'), 'Results with α')

    def test_compile_and_failed_compile_clears_old_pdf(self):
        if not self.ws.engine:
            self.skipTest('LaTeX not installed')
        result = self.ws.compile(self.pid, 'main.tex')
        self.assertTrue(result['ok'], result['log'])
        pdf = self.ws.project(self.pid) / 'preview.pdf'
        self.assertTrue(pdf.read_bytes().startswith(b'%PDF'))
        self.ws.save(self.pid, 'main.tex', '\\documentclass{article}\n\\begin{document}\\undefinedCommand\\end{document}')
        result = self.ws.compile(self.pid, 'main.tex')
        self.assertFalse(result['ok'])
        self.assertFalse(pdf.exists())

    def test_ai_contract_and_local_only(self):
        with self.assertRaises(ValueError):
            Workspace(self.temp.name, 'https://example.com')
        captured = []
        def mock(path, body):
            captured.append((path, body))
            return {'choices': [{'message': {'content': 'Revised passage.'}}]}
        self.ws.llm = mock
        self.assertEqual(self.ws.assist('polish', 'Our results is good.', 'local')['text'], 'Revised passage.')
        self.assertEqual(captured[0][0], '/v1/chat/completions')
        self.assertIn('Our results is good.', captured[0][1]['messages'][1]['content'])
        with self.assertRaises(ValueError):
            self.ws.assist('polish', 'a' * 10001, 'local')

    def test_http_rejects_cross_origin_and_exports(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.workspace = self.ws
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        url = f'http://127.0.0.1:{server.server_port}'
        with urlopen(url + '/api/projects') as response:
            self.assertEqual(json.load(response)[0]['id'], self.pid)
        with urlopen(url + '/api/export?id=' + self.pid) as response:
            self.assertTrue(response.read().startswith(b'PK'))
        request = Request(url + '/api/projects', data=b'{"title":"forged"}', headers={
            'Content-Type': 'application/json', 'X-Rocal-Paper': '1', 'Origin': 'https://example.com'})
        with self.assertRaises(HTTPError) as error:
            urlopen(request)
        self.assertEqual(error.exception.code, 403)


if __name__ == '__main__':
    unittest.main()
