#!/usr/bin/env python3
"""离线 Git 历史密钥扫描器（无外部依赖，供 CI / pre-commit 复用）。

用法：
    python3 tools/secret_scan.py            # 扫描当前工作区
    python3 tools/secret_scan.py --history  # 扫描全部 git 历史
    python3 tools/secret_scan.py --staged   # 只扫描暂存区（pre-commit 用）

退出码：0 = 无命中；1 = 命中高危密钥。
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from typing import Iterable, List, Tuple

# ====================== 高危密钥指纹规则 ======================
# 每条规则： (名称, 正则, 说明)
SECRET_PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    ("OpenAI/DeepSeek API Key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "LLM 平台 API Key"),
    ("Anthropic API Key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"), "Anthropic API Key"),
    ("AWS Access Key ID", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), "AWS 访问密钥"),
    ("Google API Key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "Google API Key"),
    ("GitHub Token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), "GitHub 令牌"),
    ("Slack Token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "Slack 令牌"),
    ("Private Key Block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"), "私钥文件"),
    ("JWT Token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"), "JWT 令牌"),
    ("Bearer/硬编码口令", re.compile(r"""(?:password|passwd|pwd|secret|token|api_key|apikey|access_key)\s*[:=]\s*["'][A-Za-z0-9_\-!@#$%^&*]{12,}["']"""), "疑似硬编码口令"),
    ("数据库连接串", re.compile(r"(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s:@/]+:(?![<{\[])[^\s:@/]{3,}@"), "带口令的数据库连接串"),
]

# 明确允许的占位 / 教学样例（避免误报阻断开发）
ALLOWLIST_PATTERNS: List[re.Pattern] = [
    re.compile(r"sk-your[-_]?api[-_]?key", re.I),
    re.compile(r"sk-xxx+", re.I),
    re.compile(r"AKIAIOSFODNN7EXAMPLE"),          # AWS 官方文档示例
    re.compile(r"AIza[0-9A-Za-z_-]{35}.*(?:example|demo|sample)", re.I),
    re.compile(r"your[-_]?(?:api[-_]?key|token|password)", re.I),
    re.compile(r"(?:change|replace)[-_]?me", re.I),
    re.compile(r"<[^>]*(?:key|token|secret|password)[^>]*>", re.I),
    re.compile(r"\$\{[A-Z_]+\}"),                  # ${ENV_VAR} 占位
    re.compile(r"os\.(?:getenv|environ)|process\.env", re.I),
    re.compile(r"REDACTED|PLACEHOLDER|DUMMY", re.I),
    re.compile(r"<[^>]*>"),                        # <your-strong-password> 之类尖括号占位
    re.compile(r"=\{1,}[^=]*$"),                   # 值被占位或为空
]

# 扫描时跳过的路径（二进制、依赖、示例数据）
SKIP_PATH_PATTERNS: List[re.Pattern] = [
    re.compile(r"(^|/)(node_modules|venv|\.venv|dist|build|__pycache__|\.git)/"),
    re.compile(r"package-lock\.json$"),
    re.compile(r"\.(?:png|jpe?g|gif|webp|ico|pdf|zip|gz|whl|so|dylib|bin|onnx|safetensors|pt|pth)$", re.I),
    re.compile(r"tools/secret_scan\.py$"),          # 本文件自身含规则样例
]


def _is_skipped(path: str) -> bool:
    return any(p.search(path) for p in SKIP_PATH_PATTERNS)


def _is_allowlisted(line: str) -> bool:
    return any(p.search(line) for p in ALLOWLIST_PATTERNS)


def scan_text(path: str, text: str) -> List[str]:
    """扫描单段文本，返回命中描述列表。"""
    findings: List[str] = []
    if _is_skipped(path):
        return findings
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _is_allowlisted(line):
            continue
        for name, pattern, desc in SECRET_PATTERNS:
            m = pattern.search(line)
            if m:
                # 只输出前 6 位，避免把完整密钥再次写进日志
                snippet = m.group(0)[:6] + "***"
                findings.append(f"{path}:{lineno} [{name}] {desc} → {snippet}")
                break
    return findings


def _run(cmd: List[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, errors="replace").stdout


def scan_worktree() -> List[str]:
    files = [f for f in _run(["git", "ls-files", "-z"]).split("\0") if f]
    findings: List[str] = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                findings.extend(scan_text(f, fh.read()))
        except (OSError, IsADirectoryError):
            continue
    return findings


def scan_staged() -> List[str]:
    diff = _run(["git", "diff", "--cached", "--unified=0", "--no-color", "--diff-filter=ACM"])
    findings: List[str] = []
    current = "<unknown>"
    lineno = 0
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            lineno = int(m.group(1)) if m else 0
        elif line.startswith("+") and not line.startswith("+++"):
            findings.extend(scan_text(current, line[1:]))
            lineno += 1
    return findings


def scan_history(max_commits: int = 0) -> List[str]:
    """逐提交扫描，只扫每提交的变更行，避免全历史重扫导致过慢。"""
    revs = _run(["git", "rev-list", "--all"]).split()
    if max_commits:
        revs = revs[:max_commits]
    findings: List[str] = []
    for rev in revs:
        diff = _run(["git", "show", rev, "--unified=0", "--no-color", "--pretty=format:%H%n%an%n%ad%n%s"])
        label = rev[:8]
        for line in diff.splitlines():
            if line.startswith(("+", "diff --git", "--- ", "+++ ", "@@", "index ", "new file", "deleted file", "similarity")):
                continue
        # 逐行扫（含文件名行，便于定位）
        for line in diff.splitlines():
            if not line.startswith("+++ b/") and not line.startswith("diff --git"):
                continue
            path = line[6:] if line.startswith("+++ b/") else line.split(" b/")[-1]
            for name, pattern, desc in SECRET_PATTERNS:
                if _is_skipped(path):
                    break
                m = pattern.search(path)
                if m:
                    findings.append(f"{label} {path} [{name}] 文件名命中")
        blob_lines = diff.splitlines()
        path = "<unknown>"
        for line in blob_lines:
            if line.startswith("+++ b/"):
                path = line[6:]
                continue
            if line.startswith("+") and not line.startswith("+++"):
                for f in scan_text(f"{label}:{path}", line[1:]):
                    findings.append(f)
    return findings


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AgentForge 离线密钥扫描器")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--history", action="store_true", help="扫描全部 git 历史")
    group.add_argument("--staged", action="store_true", help="只扫描暂存区（pre-commit）")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.history:
        mode, findings = "git 历史", scan_history()
    elif args.staged:
        mode, findings = "暂存区", scan_staged()
    else:
        mode, findings = "工作区", scan_worktree()

    if findings:
        print(f"❌ [密钥扫描] {mode}发现 {len(findings)} 处疑似敏感凭据：")
        for f in findings[:200]:
            print("   " + f)
        if len(findings) > 200:
            print(f"   ... 其余 {len(findings) - 200} 条已省略")
        print("\n请改为环境变量注入，并参考 docs/security/密钥泄漏应急响应.md 处理。")
        return 1

    print(f"✅ [密钥扫描] {mode}未发现高危凭据。")
    return 0


if __name__ == "__main__":
    sys.exit(main())