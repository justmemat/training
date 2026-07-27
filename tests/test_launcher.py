from pathlib import Path
import unittest


class WindowsLauncherTests(unittest.TestCase):
    def test_launcher_uses_local_virtual_environment_and_streamlit_module(self):
        launcher = Path("run_app.bat").read_text(encoding="utf-8")
        self.assertIn('cd /d "%~dp0"', launcher)
        self.assertIn("-m pip install -r requirements.txt", launcher)
        self.assertIn("-m streamlit run main.py", launcher)


if __name__ == "__main__":
    unittest.main()
