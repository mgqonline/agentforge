#!/usr/bin/env python3
"""
AgentForge CLI · 官方环境诊断与快捷运行工具
====================================================================
定位：彻底解决 AI 全栈转型与交付过程中的环境摩擦、依赖不确定性与操作繁琐问题。
设计原则：仅使用 Python 标准库，确保在未安装任何第三方库时也能顺畅运行 doctor 自检。

主要功能：
  1. doctor : 一键诊断本地环境（Python版本、MPS显卡加速、依赖库完整性、数据库与网络）
  2. run    : 快捷运行指定章节（如 run 15 运行全栈协同系统，run 06 运行 LangGraph）
  3. test   : 运行核心全栈冒烟测试
  4. info   : 打印系统技术全景与架构状态
"""

import argparse
import importlib
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# 终端色彩高亮
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

ROOT_DIR = Path(__file__).resolve().parent.parent


def print_banner() -> None:
    banner = f"""
{CYAN}{BOLD}======================================================================
⚡ AgentForge · 智炼工坊 · 官方开发者工具链 (CLI)
   极简主义 · 三层屏蔽 · 让每个人都能快速融入 AI 全栈开发
======================================================================{RESET}
"""
    print(banner)


def check_mark(status: bool) -> str:
    return f"{GREEN}✅ 正常{RESET}" if status else f"{RED}❌ 缺失/异常{RESET}"


def run_doctor() -> None:
    """环境健康巡检：诊断硬件、Python、依赖库与中间件连通性"""
    print(f"\n{BOLD}🔍 正在执行 AgentForge 运行环境全面体检 (doctor)...{RESET}\n")

    # 1. Python 版本检查
    py_version = sys.version_info
    py_ok = py_version.major == 3 and py_version.minor >= 10
    py_str = (
        f"{py_version.major}.{py_version.minor}.{py_version.micro} ({platform.python_implementation()})"
    )
    print(f"  [{check_mark(py_ok)}] Python 运行时基准: {py_str}")
    if not py_ok:
        print(f"       {YELLOW}⚠️ 建议升级至 Python 3.10 或 3.11 版本{RESET}")

    # 2. 虚拟环境激活检查
    in_venv = sys.prefix != sys.base_prefix
    print(
        f"  [{check_mark(in_venv)}] 虚拟环境隔离 (venv/conda): {'已激活 (' + sys.prefix + ')' if in_venv else '未激活 (建议执行 source venv/bin/activate)'}"
    )

    # 3. 硬件与显卡加速检测
    os_name = platform.system()
    machine = platform.machine()
    print(f"  [ℹ️ 信息] 操作系统平台: {os_name} ({machine})")

    has_mps = False
    has_cuda = False
    try:
        import torch

        has_mps = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
        has_cuda = torch.cuda.is_available()
    except Exception:
        pass

    if has_mps:
        accel_info = f"{GREEN}Apple Silicon (MPS 硬件加速就绪){RESET}"
    elif has_cuda:
        accel_info = f"{GREEN}NVIDIA CUDA ({torch.cuda.get_device_name(0)}){RESET}"
    else:
        accel_info = f"{CYAN}标准 CPU / ONNX 模式 (轻量低功耗自洽){RESET}"
    print(f"  [🚀 加速] 计算引擎模式: {accel_info}")

    # 4. 核心核心依赖库检测
    core_packages: List[Tuple[str, str]] = [
        ("fastapi", "FastAPI 高性能网关底座"),
        ("sqlalchemy", "SQLAlchemy 2.0 异步持久化 ORM"),
        ("aiosqlite", "SQLite 异步驱动支持"),
        ("greenlet", "SQLAlchemy 异步协程切换库"),
        ("celery", "Celery 分布式异步任务队列"),
        ("langchain", "LangChain 核心框架"),
        ("langgraph", "LangGraph 有状态状态机引擎"),
        ("openai", "OpenAI / DeepSeek 标准 SDK"),
        ("pydantic", "Pydantic v2 结构化数据校验"),
        ("chromadb", "Chroma 向量数据库"),
    ]

    print(f"\n{BOLD}📦 核心 AI 工程依赖库检查:{RESET}")
    missing_packages = []
    for pkg_name, desc in core_packages:
        installed = False
        try:
            importlib.import_module(pkg_name)
            installed = True
        except ImportError:
            missing_packages.append(pkg_name)
        print(f"  [{check_mark(installed)}] {pkg_name:<14} : {desc}")

    if missing_packages:
        print(
            f"\n  {YELLOW}⚠️ 检测到以下依赖缺失: {', '.join(missing_packages)}{RESET}"
        )
        print(
            f"  👉 建议执行一键修复: {CYAN}pip install {' '.join(missing_packages)}{RESET}"
        )
    else:
        print(
            f"\n  {GREEN}{BOLD}✨ 完美！所有 10 项核心 AI 工程依赖库已全部就绪。{RESET}"
        )

    # 5. Redis 服务连通性探测 (可选)
    print(f"\n{BOLD}🔌 外部中间件连通性检测 (可选):{RESET}")
    redis_ok = False
    try:
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        res = sock.connect_ex(("127.0.0.1", 6379))
        sock.close()
        redis_ok = res == 0
    except Exception:
        pass

    if redis_ok:
        print(f"  [{check_mark(True)}] Redis 消息队列 (127.0.0.1:6379) : 在线就绪")
    else:
        print(
            f"  [{YELLOW}可选未启动{RESET}] Redis 消息队列 (127.0.0.1:6379) : 未检测到运行 (单机内置协程模式不受影响；若运行 Celery 分布式任务可执行 brew services start redis 或 docker-compose up -d)"
        )

    # 6. 配置文件检查
    env_file = ROOT_DIR / ".env"
    env_example = ROOT_DIR / ".env.example"
    has_env = env_file.exists()
    print(
        f"  [{check_mark(has_env)}] 项目环境变量 (.env) : {'已配置' if has_env else '未找到 (.env.example 存在，建议 cp .env.example .env)'}"
    )

    print(f"\n{CYAN}======================================================================{RESET}")
    if not missing_packages and py_ok:
        print(
            f"{GREEN}{BOLD}🎉 恭喜！当前环境健康，可直接运行所有 01-23 学习章节与全栈系统！{RESET}"
        )
        print(f"👉 快速体验建议: {CYAN}python scripts/agentforge_cli.py run 15{RESET}")
    else:
        print(f"{YELLOW}{BOLD}⚠️ 请按上述提示先安装缺失依赖，即可开启无痛体验。{RESET}")
    print(f"{CYAN}======================================================================{RESET}\n")


CHAPTER_SCRIPTS: Dict[str, str] = {
    "01": "01-prompt-engineering/03_chain_of_thought.py",
    "02": "02-function-calling/01_basic_function_calling.py",
    "03": "03-mcp/01_simple_server.py",
    "04": "04-rag/01_basic_rag.py",
    "05": "05-embedding/01_cosine_similarity.py",
    "06": "06-agent-basics/01_simple_langgraph_agent.py",
    "07": "07-advanced-memory/01_summary_memory.py",
    "08": "08-multimodal/01_test_vision.py",
    "09": "09-evaluation/01_ragas_simulation.py",
    "10": "10-production/01_production_stability.py",
    "11": "11-python-advanced/advanced_python_demo.py",
    "12": "12-fastapi-advanced/app.py",
    "13": "13-sqlalchemy-advanced/advanced_orm.py",
    "14": "14-celery-advanced/tasks.py",
    "15": "15-agent-architecture/full_stack_agent_system.py",
    "16": "16-face-recognition/test_accuracy.py",
    "17": "17-transformers-basics/04_attention_basics.py",
    "18": "18-inference-serving/benchmark_concurrent.py",
    "20-agent": "20-agent-frameworks/basic_agent.py",
    "20-graph": "20-graph-rag/extract_entities.py",
    "21": "21-multi-agent-scale/crewai_demo.py",
    "22": "22-ai-security/plugin_security_demo.py",
    "23": "23-edge-ai/edge_inference.py",
}


def run_chapter(target: str) -> None:
    """快捷运行指定章节的核心示例脚本"""
    clean_target = target.strip().lower()
    script_rel_path = None

    # 精确或前缀匹配
    for key, path in CHAPTER_SCRIPTS.items():
        if clean_target == key or clean_target == key.replace("-", ""):
            script_rel_path = path
            break
        if clean_target in ["15", "full", "fullstack", "architecture"]:
            script_rel_path = CHAPTER_SCRIPTS["15"]
            break

    if not script_rel_path:
        # 补全 0 前缀尝试
        if len(clean_target) == 1 and f"0{clean_target}" in CHAPTER_SCRIPTS:
            script_rel_path = CHAPTER_SCRIPTS[f"0{clean_target}"]

    if not script_rel_path:
        print(f"\n{RED}❌ 未找到章节 '{target}' 的快捷启动入口。{RESET}")
        print(f"💡 可选章节代码: {', '.join(sorted(CHAPTER_SCRIPTS.keys()))}")
        return

    script_path = ROOT_DIR / script_rel_path
    if not script_path.exists():
        print(f"\n{RED}❌ 脚本文件不存在: {script_path}{RESET}")
        return

    print(f"\n{BOLD}🚀 正在启动章节 [{target}] -> {script_rel_path}{RESET}")
    print(f"{CYAN}{'='*60}{RESET}\n")

    cmd = [sys.executable, str(script_path)]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n{RED}❌ 执行遇到异常 (退出码: {e.returncode}){RESET}")
    except KeyboardInterrupt:
        print(f"\n{YELLOW}🛑 已中断运行{RESET}")


def run_smoke_tests() -> None:
    """运行全局冒烟测试套件"""
    print(f"\n{BOLD}🧪 正在执行核心全栈冒烟测试 (Smoke Test)...{RESET}\n")
    smoke_test_script = ROOT_DIR / "tests" / "test_e2e_smoke.py"
    if not smoke_test_script.exists():
        print(f"{YELLOW}⚠️ 冒烟测试脚本尚未创建: {smoke_test_script}{RESET}")
        return

    cmd = [sys.executable, "-m", "pytest", str(smoke_test_script), "-v"]
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        # 如果当前环境没有 pytest，回退使用 python 直接运行
        fallback_cmd = [sys.executable, str(smoke_test_script)]
        subprocess.run(fallback_cmd)


def main() -> None:
    print_banner()
    parser = argparse.ArgumentParser(
        description="AgentForge 官方开发者工具链",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例用法:
  python scripts/agentforge_cli.py doctor         # 一键环境诊断与体检
  python scripts/agentforge_cli.py run 15         # 运行第15章企业全栈协同闭环
  python scripts/agentforge_cli.py run 06         # 运行第06章 LangGraph Agent
  python scripts/agentforge_cli.py test           # 运行全套核心冒烟测试
""",
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # doctor 子命令
    subparsers.add_parser("doctor", help="环境健康检查与一键诊断")

    # run 子命令
    run_parser = subparsers.add_parser("run", help="快捷运行指定章节示例")
    run_parser.add_argument(
        "chapter",
        type=str,
        nargs="?",
        default="15",
        help="章节编号 (如 01, 04, 06, 12, 13, 14, 15 等)",
    )

    # test 子命令
    subparsers.add_parser("test", help="执行核心全栈冒烟测试")

    # poc 子命令
    subparsers.add_parser("poc", help="一键运行企业级 POC (概念验证) 自动化验收演示")

    args = parser.parse_args()

    if args.command == "doctor":
        run_doctor()
    elif args.command == "run":
        run_chapter(args.chapter)
    elif args.command == "test":
        run_smoke_tests()
    elif args.command == "poc":
        poc_script = ROOT_DIR / "scripts" / "run_enterprise_poc.py"
        subprocess.run([sys.executable, str(poc_script)])
    else:
        # 默认无参数时运行 doctor
        run_doctor()


if __name__ == "__main__":
    main()
