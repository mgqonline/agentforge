import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from sandbox_runner import CodeSecurityAuditor, SandboxRunner

def test_security_auditor_blocks_dangerous_modules():
    dangerous_codes = [
        "import subprocess\nsubprocess.run(['ls'])",
        "import shutil\nshutil.rmtree('/tmp')",
        "import pty",
        "import ctypes",
        "import socket",
        "from subprocess import Popen"
    ]
    for code in dangerous_codes:
        is_safe, reason = CodeSecurityAuditor.audit(code)
        assert not is_safe, f"Should block: {code}"
        assert "安全边界策略拦截" in reason

def test_security_auditor_blocks_dangerous_calls():
    dangerous_calls = [
        "import os\nos.system('whoami')",
        "import os\nos.popen('ls')",
        "import os\nos.remove('important.txt')",
        "eval('1 + 1')",
        "exec('a = 1')",
        "__import__('os').system('ls')"
    ]
    for code in dangerous_calls:
        is_safe, reason = CodeSecurityAuditor.audit(code)
        assert not is_safe, f"Should block: {code}"
        assert "安全边界策略拦截" in reason

def test_security_auditor_blocks_sandbox_escape_attributes():
    escape_codes = [
        "().__class__.__bases__[0].__subclasses__()",
        "def f(): pass\nf.__globals__",
        "def f(): pass\nf.__code__",
    ]
    for code in escape_codes:
        is_safe, reason = CodeSecurityAuditor.audit(code)
        assert not is_safe, f"Should block: {code}"
        assert "受限内部底层属性" in reason

def test_security_auditor_blocks_getattr_escape():
    # 反射绕过攻击
    escape_code = "import os\ngetattr(os, 'system')('id')"
    is_safe, reason = CodeSecurityAuditor.audit(escape_code)
    assert not is_safe
    assert "安全边界策略拦截" in reason

def test_security_auditor_blocks_credential_theft():
    # 试图读取宿主 API 密钥
    steal_codes = [
        "import os\nprint(os.environ['OPENAI_API_KEY'])",
        "import os\nprint(os.environ.get('OPENAI_API_KEY'))",
        "import os\nprint(os.getenv('OPENAI_API_KEY'))",
    ]
    for code in steal_codes:
        is_safe, reason = CodeSecurityAuditor.audit(code)
        assert not is_safe, f"Should block: {code}"
        assert "凭据" in reason or "机密" in reason or "安全" in reason

def test_security_auditor_allows_safe_ai_code():
    safe_codes = [
        "import math\nprint(math.sqrt(16))",
        "import json\nd = json.loads('{\"a\": 1}')\nprint(d)",
        "from typing import List, Dict, Optional\ndef foo(x: int) -> int: return x * 2",
        "import numpy as np\nprint([x for x in range(10)])",
        "text = 'Hello world'\nprint(text.upper())"
    ]
    for code in safe_codes:
        is_safe, reason = CodeSecurityAuditor.audit(code)
        assert is_safe, f"Should allow safe code: {code}, got reason: {reason}"

def test_sandbox_runner_e2e_blocks_blocked_code():
    runner = SandboxRunner()
    res = runner.run_code("import subprocess\nsubprocess.call(['id'])")
    assert res["status"] == "blocked"
    assert res["exit_code"] == 403
    assert "安全边界策略拦截" in res["stderr"]
