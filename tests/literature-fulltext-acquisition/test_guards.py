from pathlib import Path
import os
import re
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
            (["openalex","download","--ids","W000","--content","pdf","--filter","!open_access.is_oa:true","-o",out],"OA or license"),
            (["openalex","download","--ids","W000","--content","pdf","--filter","primary_location.license:null","-o",out],"OA or license"),
            (["openalex","download","--ids","W000","--content","pdf","-f","open_access.is_oa:true","-f","type:article","-o",out],"OA or license"),
            (["openalex","download","--ids","W000","--content","pdf","--query","open_access.is_oa:true","-o",out],"OA or license"),
            (["openalex","download","--ids","W000","--workers","5","-o",out],"between 1 and 4"),
            (["openalex","download","--ids","W000","--workers","1","--workers","64","-o",out],"between 1 and 4"),
            (["instsci","papers","synthetic.txt"],"explicit"),
            (["instsci","papers","synthetic.txt","--output",out,"--concurrency","3"],"between 1 and 2"),
            (["instsci","papers","synthetic.txt","--output",out,"-j","1","-j","8"],"between 1 and 2"),
            (["instsci","papers","synthetic.txt","--output",out,"-j8"],"between 1 and 2"),
            (["instsci","batch","synthetic.txt","--output",out,"--concurrency","3"],"between 1 and 2"),
            (["instsci","est-batch","synthetic.txt","--output",out,"--concurrency","3"],"between 1 and 2"),
            (["paper-search","download","arxiv","synthetic","-o",str(self.protected/"downloads")],"protected tool workspace"),
            (["paper-search","download","arxiv","synthetic","-o",out,"-o",str(self.protected/"downloads")],"protected tool workspace"),
            (["paper-search","download","arxiv","synthetic","-o",r"\\localhost\c$\temp"],"UNC and device-namespace"),
            (["paper-search","download","arxiv","synthetic","-o",str(self.root/"PROTEC~1"/"downloads")],"8.3 short paths"),
            (["paper-search","search","sci-hub fallback"],"Blocked by policy"),
            (["paper-search","search","annas-archive mirror"],"Blocked by policy"),
            (["paper-search","search","anna's archive mirror"],"Blocked by policy"),
            (["paper-search","search","z-lib download"],"Blocked by policy"),
            (["openalex","status","--proxy","http://127.0.0.1:8080"],"Blocked by policy"),
            (["openalex","status","--proxy-server","http://127.0.0.1:8080"],"Blocked by policy"),
            (["openalex","status","--api_key","secret"],"Credential-bearing"),
            (["openalex","status","--cookie","session=secret"],"Credential-bearing"),
            (["openalex","status","--header","Authorization: Bearer x"],"Credential-bearing"),
        ]
        for args,message in cases:
            with self.subTest(args=args):
                result=self.run_wrapper(*args)
                self.assertNotEqual(result.returncode,0)
                # PowerShell's concise view may color and wrap the same exception
                # over decorated lines. Compare its text, retaining all guard checks.
                diagnostic=re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]","",result.stdout+result.stderr)
                diagnostic=re.sub(r"(?m)^\s*(?:\d+\s*)?\|\s?","",diagnostic)
                self.assertIn(message," ".join(diagnostic.split()))
                self.assertNotIn("not a valid",result.stderr)
        self.assertFalse(Path(out).exists())
        self.assertFalse((self.protected/"downloads").exists())

    def test_credential_option_rejected_without_value_disclosure(self):
        marker="SYNTHETIC_SECRET_MARKER_6f8571"
        result=self.run_wrapper("openalex","status","--api-key",marker)
        self.assertNotEqual(result.returncode,0)
        self.assertIn("Credential-bearing",result.stderr)
        self.assertNotIn(marker,result.stdout+result.stderr)

    def test_junction_output_escape_is_rejected(self):
        if os.name != "nt":
            self.skipTest("Windows directory junction test")
        self.protected.mkdir(parents=True, exist_ok=True)
        link = self.root / "escape-junction"
        created = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(self.protected)],
            capture_output=True,
            text=True,
        )
        if created.returncode != 0:
            self.skipTest(f"Unable to create directory junction: {created.stderr}")
        result = self.run_wrapper("paper-search", "download", "arxiv", "synthetic", "-o", str(link / "sub"))
        self.assertNotEqual(result.returncode, 0)
        diagnostic = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", result.stdout + result.stderr)
        diagnostic = re.sub(r"(?m)^\s*(?:\d+\s*)?\|\s?", "", diagnostic)
        self.assertIn("symlinks or directory junctions", " ".join(diagnostic.split()))

    def test_windows_existing_short_path_is_canonicalized(self):
        if os.name != "nt":
            self.skipTest("Windows 8.3 short-path canonicalization test")
        import ctypes

        def to_short(path: Path) -> str:
            buf = ctypes.create_unicode_buffer(1024)
            length = ctypes.windll.kernel32.GetShortPathNameW(str(path), buf, len(buf))
            return buf.value if length else str(path)

        safe_parent = self.root / "safe_long_temp_directory"
        safe_parent.mkdir(parents=True, exist_ok=True)
        short_safe = to_short(safe_parent)
        self.protected.mkdir(parents=True, exist_ok=True)
        protected_long = self.protected / "nested_protected_directory"
        protected_long.mkdir(parents=True, exist_ok=True)
        short_protected = to_short(protected_long)
        if "~" not in short_safe and "~" not in short_protected:
            self.skipTest("Volume does not generate Windows 8.3 short names")

        safe_result = self.run_wrapper(
            "openalex", "download", "--ids", "W000", "--content", "pdf", "-o", str(Path(short_safe) / "out")
        )
        self.assertNotEqual(safe_result.returncode, 0)
        safe_diag = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", safe_result.stdout + safe_result.stderr)
        safe_diag = re.sub(r"(?m)^\s*(?:\d+\s*)?\|\s?", "", safe_diag)
        self.assertIn("OA or license", " ".join(safe_diag.split()))

        prot_result = self.run_wrapper(
            "paper-search", "download", "arxiv", "synthetic", "-o", str(Path(short_protected) / "downloads")
        )
        self.assertNotEqual(prot_result.returncode, 0)
        prot_diag = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", prot_result.stdout + prot_result.stderr)
        prot_diag = re.sub(r"(?m)^\s*(?:\d+\s*)?\|\s?", "", prot_diag)
        self.assertIn("protected tool workspace", " ".join(prot_diag.split()))


if __name__=="__main__":unittest.main()
