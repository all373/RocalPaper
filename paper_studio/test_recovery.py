import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from paper_studio.server import Workspace
from paper_studio.history import revisions
from paper_studio.settings import Settings


class RecoveryTests(unittest.TestCase):
    def test_history_restore_preserves_previous_current_version(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = Workspace(temp, 'http://127.0.0.1:1', engine='missing-tex')
            pid = ws.create('History')['id']
            ws.save(pid, 'main.tex', 'version one')
            ws.save(pid, 'main.tex', 'version two')
            history = revisions(ws.project(pid), 'main.tex')
            self.assertEqual(history[0]['content'], 'version one')
            ws.save(pid, 'main.tex', history[0]['content'])
            self.assertEqual(revisions(ws.project(pid), 'main.tex')[0]['content'], 'version two')
            self.assertEqual(ws.file(pid, 'main.tex').read_text(), 'version one')
            for i in range(45):
                ws.save(pid, 'main.tex', str(i))
            self.assertEqual(len(revisions(ws.project(pid), 'main.tex')), 40)

    def test_damaged_settings_and_project_do_not_prevent_startup(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            (home / 'settings.json').write_text('{broken')
            settings = Settings(home)
            self.assertEqual(settings.values['llm_url'], 'http://127.0.0.1:8771')
            self.assertEqual(len(list(home.glob('settings-damaged-*.json'))), 1)
            ws = Workspace(home / 'projects', 'http://127.0.0.1:1', engine='missing-tex')
            first = ws.create('Good')
            bad = ws.create('Bad')
            (ws.project(bad['id']) / 'project.json').write_text('{broken')
            self.assertEqual(ws.projects(), [first])

    def test_learning_tasks_keep_explanation_separate_from_manuscript(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = Workspace(temp, 'http://127.0.0.1:1', engine='missing-tex')
            for task in ['explain', 'howto', 'learn_translate', 'translate_ja']:
                with patch.object(ws, 'llm', return_value={'choices':[{'message':{'content':'学習の説明'}}]}) as llm:
                    result = ws.assist(task, '表を作りたい', 'local')
                    self.assertEqual(result['text'], '学習の説明')
                    self.assertIn('Japanese', llm.call_args.args[1]['messages'][0]['content'])

    def test_generated_example_is_checked_without_changing_user_project(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = Workspace(temp, 'http://127.0.0.1:1')
            if not ws.engine:
                self.skipTest('LaTeX not installed')
            project = ws.create('Untouched')
            before = ws.file(project['id'], 'main.tex').read_bytes()
            for code, expected in [(r'\begin{itemize}\item First\end{itemize}', True),
                                   (r'\undefinedRocalCommand', False)]:
                with patch.object(ws, 'llm', return_value={'choices':[{'message':{'content':'```latex\n'+code+'\n```'}}]}):
                    result = ws.assist('howto', 'Teach a list', 'local')
                    self.assertEqual(result['example_check']['ok'], expected)
            self.assertEqual(ws.projects(), [project])
            self.assertEqual(ws.file(project['id'], 'main.tex').read_bytes(), before)
