from pathlib import Path
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"skills/research-lookup-enhanced/scripts"))
from rle import extraction


class ParserRuntimeSettingsTests(unittest.TestCase):
    def test_local_settings_environment_and_explicit_adapter_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            fake_module=root/"scripts/rle/extraction.py"
            (root/"config").mkdir()
            (root/"config/local.json").write_text(json.dumps({"mineru_wrapper":str(root/"local.py"),"mineru_python":sys.executable}),encoding="utf-8")
            with patch.object(extraction,"__file__",str(fake_module)),patch.dict(os.environ,{},clear=True):
                parser=extraction.MinerUParser(allow_remote=False,is_open_access=True)
                self.assertEqual(parser.wrapper_path,root/"local.py")
                with patch.dict(os.environ,{"MINERU_WRAPPER":str(root/"env.py")}):
                    self.assertEqual(extraction.MinerUParser(allow_remote=False,is_open_access=True).wrapper_path,root/"env.py")
                    self.assertEqual(extraction.MinerUParser(allow_remote=False,is_open_access=True,wrapper_path=str(root/"explicit.py")).wrapper_path,root/"explicit.py")

    def test_missing_wrapper_is_an_explicit_unavailable_adapter(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{},clear=True):
            with patch.object(extraction,"__file__",str(Path(tmp)/"scripts/rle/extraction.py")):
                parser=extraction.MinerUParser(allow_remote=False,is_open_access=True)
                self.assertIsNone(parser.wrapper_path)
                self.assertEqual(parser.python_executable,Path(sys.executable))


if __name__=="__main__":unittest.main()
