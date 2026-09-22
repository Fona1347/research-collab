from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]


class PortableGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="acquisition guards ")
        self.root=Path(self.temp.name)
        self.wrapper=self.root/"skill/scripts/literature-tools.ps1"
        self.wrapper.parent.mkdir(parents=True)
        shutil.copy2(ROOT/"skills/literature-fulltext-acquisition/scripts/literature-tools.ps1",self.wrapper)
        self.tools=self.root/"tools"
        for tool in ("paper-search","openalex","instsci"):
            exe=self.tools/f"runtimes/{tool}/.venv/Scripts/{tool}.exe"
            exe.parent.mkdir(parents=True);exe.write_bytes(b"not-an-executable")
        patch=self.tools/"runtimes/openalex/.venv/Lib/site-packages/openalex_cli/downloader.py"
        patch.parent.mkdir(parents=True);patch.write_text("# registered_signals\n# except (NotImplementedError, RuntimeError)\n",encoding="utf-8")
        (self.tools/"state/instsci/cloakbrowser").mkdir(parents=True)
        self.protected=self.root/"protected"
        self.env=os.environ.copy()
        self.env["LITERATURE_TOOLS_ROOT"]=str(self.tools)
        self.env["LITERATURE_PROTECTED_ROOT"]=str(self.protected)

    def tearDown(self):self.temp.cleanup()

    def run_wrapper(self,*args,env=None):
        return subprocess.run(["pwsh","-NoProfile","-File",str(self.wrapper),*args],env=env or self.env,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=20)

    def test_missing_runtime_status_does_not_install(self):
        env=self.env.copy();env.pop("LITERATURE_TOOLS_ROOT",None);env.pop("LITERATURE_PROTECTED_ROOT",None)
        result=self.run_wrapper("status",env=env)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("paper-search: missing",result.stdout)
        self.assertFalse((self.wrapper.parent.parent/".unconfigured").exists())

    def test_guards_fail_before_fake_executable_or_output_creation(self):
        out=str(self.root/"never-created")
        cases=[
            (["paper-search","download","arxiv","synthetic"],"explicit"),
            (["openalex","download","--ids","W000","--content","pdf","-o",out],"OA or license"),
            (["openalex","download","--ids","W000","--workers","5","-o",out],"between 1 and 4"),
            (["instsci","papers","synthetic.txt"],"explicit"),
            (["instsci","papers","synthetic.txt","--output",out,"--concurrency","3"],"between 1 and 2"),
            (["paper-search","download","arxiv","synthetic","-o",str(self.protected/"downloads")],"protected tool workspace"),
            (["paper-search","search","sci-hub fallback"],"Blocked by policy"),
        ]
        for args,message in cases:
            with self.subTest(args=args):
                result=self.run_wrapper(*args)
                self.assertNotEqual(result.returncode,0)
                self.assertIn(message,result.stdout+result.stderr)
                self.assertNotIn("not a valid",result.stderr)
        self.assertFalse(Path(out).exists())
        self.assertFalse((self.protected/"downloads").exists())

    def test_credential_option_rejected_without_value_disclosure(self):
        marker="SYNTHETIC_SECRET_MARKER_6f8571"
        result=self.run_wrapper("openalex","status","--api-key",marker)
        self.assertNotEqual(result.returncode,0)
        self.assertIn("Credential-bearing",result.stderr)
        self.assertNotIn(marker,result.stdout+result.stderr)


if __name__=="__main__":unittest.main()
