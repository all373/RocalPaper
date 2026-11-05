import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from paper_studio.settings import Settings, local_url


class SettingsTests(unittest.TestCase):
    def test_local_only_endpoint_validation(self):
        for url in ['https://example.com', 'http://127.0.0.1.evil.test', 'file:///x',
                    'http://127.0.0.1:80/v1?redirect=1', 'http://user@localhost:80']:
            with self.assertRaises(ValueError):
                local_url(url)
        self.assertEqual(local_url('http://127.0.0.1:8080/v1/'), 'http://127.0.0.1:8080')

    def test_settings_survive_restart_and_restore_external_endpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            settings = Settings(folder)
            settings.workspace = SimpleNamespace(llm_url='')
            settings.save({'llm_url': 'http://127.0.0.1:8080/v1', 'llm_root': 'D:/test-models'})
            self.assertEqual(Settings(folder).values, settings.values)
            self.assertEqual(settings.workspace.llm_url, 'http://127.0.0.1:8080')
            settings.workspace.llm_url = 'http://127.0.0.1:54321'
            settings.close()
            self.assertEqual(settings.workspace.llm_url, 'http://127.0.0.1:8080')
            self.assertNotIn('api_key', json.loads((Path(folder) / 'settings.json').read_text('utf-8')))

    def test_missing_model_runtime_does_not_start_or_change_endpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            settings = Settings(folder)
            settings.workspace = SimpleNamespace(llm_url='http://127.0.0.1:8080')
            settings.values['llm_root'] = folder
            with self.assertRaises(ValueError):
                settings.start()
            self.assertIsNone(settings.context)
            self.assertEqual(settings.workspace.llm_url, 'http://127.0.0.1:8080')


if __name__ == '__main__':
    unittest.main()
