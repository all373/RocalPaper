import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from paper_studio.desktop import data_home
from build_paper import copy_if_changed


class DesktopTests(unittest.TestCase):
    def test_portable_home_and_explicit_override(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'portable.json').write_text('{}')
            self.assertEqual(data_home(root), root / 'data')
            self.assertEqual(data_home(root, root / 'other'), (root / 'other').resolve())

    def test_unchanged_build_files_are_not_replaced(self):
        with tempfile.TemporaryDirectory() as temp:
            a, b = Path(temp) / 'source', Path(temp) / 'dest'
            a.write_bytes(b'unchanged')
            copy_if_changed(a, b)
            inode = b.stat().st_ino
            copy_if_changed(a, b)
            self.assertEqual(inode, b.stat().st_ino)
            a.write_bytes(b'new content')
            copy_if_changed(a, b)
            self.assertEqual(b.read_bytes(), b'new content')

    @unittest.skipUnless(os.name == 'nt', 'Windows Job Object')
    def test_child_exits_when_job_owner_is_terminated(self):
        import ctypes
        from ctypes import wintypes
        with tempfile.TemporaryDirectory() as temp:
            pidfile = Path(temp) / 'child.pid'
            code = ('import subprocess,sys,time; from pathlib import Path; from process_job import ProcessJob; '
                    'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"]); '
                    'j=ProcessJob(p); Path(sys.argv[1]).write_text(str(p.pid)); time.sleep(60)')
            owner = subprocess.Popen([sys.executable, '-c', code, str(pidfile)], cwd=Path(__file__).resolve().parents[1],
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                deadline = time.monotonic() + 10
                while not pidfile.is_file() and owner.poll() is None and time.monotonic() < deadline:
                    time.sleep(.05)
                self.assertTrue(pidfile.exists(), 'Job setup failed')
                kernel = ctypes.WinDLL('kernel32', use_last_error=True)
                kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
                kernel.OpenProcess.restype = wintypes.HANDLE
                kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
                kernel.CloseHandle.argtypes = [wintypes.HANDLE]
                child = kernel.OpenProcess(0x100000, False, int(pidfile.read_text()))
                self.assertTrue(child)
                try:
                    owner.terminate()
                    owner.wait(timeout=5)
                    self.assertEqual(kernel.WaitForSingleObject(child, 5000), 0, 'Inference child survived owner exit')
                finally:
                    kernel.CloseHandle(child)
            finally:
                if owner.poll() is None:
                    owner.terminate()
                    owner.wait(timeout=5)
