#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
课程内容自检脚本 (Curriculum Content Validator)
================================================================================

[为什么需要它]
每个关卡的官方参考解（`solution_code`）应该是「能通过本关卡全部单元测试」的
标准答案。但关卡内容分散在 backend/curriculum_engine.py 的内置字典和各阶段
目录的真实模块文件里，一旦有人改了测试却没同步更新参考解（或反之），
学员就会看到「照抄官方答案也过不了关」的荒谬局面——这属于教学系统里最严重的
内容缺陷，而在服务运行时完全不会被发现。

本脚本把「参考解必须通过自己的测试」变成一条可重复执行的自检：
  1. 遍历所有关卡；
  2. 用与运行时完全相同的沙箱（SandboxRunner）跑 `solution_code + test_code`；
  3. 汇总通关 / 失败 / 跳过（无内置测试）三类结果，并打印失败详情。

[用法]
    python3 backend/validate_curriculum.py              # 全量自检
    python3 backend/validate_curriculum.py 17-transformers-basics   # 只查指定关卡

退出码：0 表示全部参考解通关；1 表示存在失败关卡（可直接用于 CI 卡口）。
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from curriculum_engine import CurriculumEngine
from sandbox_runner import SandboxRunner

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# 沙箱单关卡的执行上限（秒）。参考解通常应在数秒内跑完，
# 给宽松一些以避免偶发的模型加载/冷启动导致误报。
PER_PHASE_TIMEOUT = 30

# 这些占位测试由 curriculum_engine 自动生成（无真实评测点）。
PLACEHOLDER_TEST_MARK = "self.assertTrue(True)"

# 测试代码里出现的「外部依赖」导入：这些模块只在学员本机运行时存在，
# 沙箱里没有，说明该测试根本不是为了在沙箱内评测参考解而写的。
_EXTERNAL_TEST_IMPORTS = (
    "from face_api import",
    "from test_accuracy import",
    "from more_fastapi_examples import",
    "uvicorn",
    "TestClient",
)

# 测试具备「真实评测点」的信号：出现断言或 unittest 断言方法
_ASSERTION_SIGNALS = ("self.assert", "assert ", "unittest.main", "pytest.raises")


def _analyze_testability(solution: str, test_code: str) -> tuple:
    """
    判断某个关卡的「参考解 + 测试」是否构成可在沙箱内执行的自洽评测对。

    返回 (可评测?, 原因)。不可评测的关卡会归入「未纳入自动校验」，
    而不是报成失败——因为参考解根本没跑过，没有证据说它错。

    判定依据（全部基于实测到的内容缺陷）：
      1. 空测试或自动生成的占位断言 → 无评测点；
      2. 测试导入了外部模块（face_api / more_fastapi_examples / uvicorn 等），
         说明它需要在沙箱之外启动服务，无法在沙箱内自洽运行；
      3. 测试没有任何断言 → 跑通也不证明参考解正确。
    """
    if not test_code or not test_code.strip():
        return False, "测试代码为空"
    if PLACEHOLDER_TEST_MARK in test_code and "class TestSolution" in test_code:
        return False, "占位测试（无真实评测点）"

    for ext in _EXTERNAL_TEST_IMPORTS:
        if ext in test_code:
            return False, f"测试依赖沙箱外的外部模块（{ext}），无法在沙箱内自洽运行"

    if not any(sig in test_code for sig in _ASSERTION_SIGNALS):
        return False, "测试不含任何断言，跑通不构成验证"

    if not solution or not solution.strip():
        return False, "参考解为空"

    return True, ""


def validate(only_phase: str = "") -> int:
    engine = CurriculumEngine(base_dir=PROJECT_ROOT)
    runner = SandboxRunner()

    phases = engine.get_all_phases()
    if only_phase:
        phases = [p for p in phases if p.get("id") == only_phase]
        if not phases:
            print(f"[自检] 未找到关卡: {only_phase}")
            return 1

    passed, failed, not_verifiable = [], [], []

    print(f"[自检] 开始校验 {len(phases)} 个关卡的官方参考解...\n")

    for phase in phases:
        phase_id = phase.get("id", "?")
        try:
            detail = engine.get_phase_detail(phase_id)
        except Exception as e:
            failed.append((phase_id, f"读取关卡详情异常: {e}"))
            print(f"  ❌ {phase_id}: 读取详情异常 {e}")
            continue

        if not detail:
            not_verifiable.append((phase_id, "无详情"))
            print(f"  ⏭️  {phase_id}: 无详情，跳过")
            continue

        solution = detail.get("solution_code") or ""
        test_code = detail.get("test_code") or ""

        verifiable, reason = _analyze_testability(solution, test_code)
        if not verifiable:
            not_verifiable.append((phase_id, reason))
            print(f"  ⚪ {phase_id}: {reason}")
            continue

        script = solution + "\n\n" + test_code
        start = time.time()
        try:
            res = runner.run_code(script, timeout=PER_PHASE_TIMEOUT)
        except Exception as e:
            failed.append((phase_id, f"沙箱调用异常: {e}"))
            print(f"  ❌ {phase_id}: 沙箱调用异常 {e}")
            continue
        elapsed = round(time.time() - start, 2)

        if res.get("exit_code") == 0:
            passed.append(phase_id)
            print(f"  ✅ {phase_id}: 参考解通关 ({elapsed}s)")
        else:
            stderr = (res.get("stderr") or "").strip()
            tail = "\n      ".join(stderr.splitlines()[-8:]) or "(无 stderr)"
            failed.append((phase_id, stderr[-800:]))
            print(f"  ❌ {phase_id}: 参考解未能通关 ({elapsed}s)\n      {tail}")

    print("\n" + "=" * 72)
    print(
        f"[自检汇总] 通关 {len(passed)} | 失败 {len(failed)} | "
        f"未纳入自动校验 {len(not_verifiable)}"
    )
    if failed:
        print("\n失败关卡清单（教学内容缺陷，需修复参考解或测试）:")
        for pid, reason in failed:
            print(f"  - {pid}: {reason.splitlines()[0] if reason else '未知原因'}")
    if not_verifiable:
        print("\n未纳入自动校验的关卡（参考解不可在沙箱内验证，属内容侧待补项）:")
        for pid, reason in not_verifiable:
            print(f"  - {pid}: {reason}")
    print("=" * 72)

    return 1 if failed else 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.exit(validate(target))