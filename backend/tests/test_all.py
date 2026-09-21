import sys
import time
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure tests folder is on path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from test_stage1 import test_stage1
from test_stage2 import run_stage2_tests
from test_stage3 import run_stage3_tests
from test_stage4 import run_stage4_tests
from test_benchmark import run_all_benchmarks

def run_all_suites():
    start_time = time.time()
    print("#################################################################")
    print("   KnoQuest Enterprise Knowledge Agent — Unified Test Suite")
    print("#################################################################")
    
    stages = [
        ("Stage 1: Foundation & Day 1 Milestone", test_stage1),
        ("Stage 2: Knowledge Base, RAG & Anti-Hallucination", run_stage2_tests),
        ("Stage 3: Upload, Multilingual & Speech", run_stage3_tests),
        ("Stage 4: MCP Tools & Tool Invocation", run_stage4_tests),
        ("Comprehensive Benchmark (19 Evaluation Cases)", run_all_benchmarks)
    ]

    results = []
    for name, test_fn in stages:
        print(f"\n>>>>>> Starting {name} <<<<<<")
        try:
            ok = test_fn()
            results.append((name, ok, None))
        except Exception as e:
            results.append((name, False, str(e)))

    elapsed = round(time.time() - start_time, 2)

    print("\n\n" + "=" * 65)
    print("                 KNOQUEST TEST EXECUTION REPORT")
    print("=" * 65)
    all_passed = True
    for name, status, err in results:
        status_str = "PASS" if status else "FAIL"
        if not status:
            all_passed = False
        mark = "✓" if status else "✗"
        print(f" [{mark}] {name:<50} : {status_str}")
        if err:
            print(f"     Error: {err}")

    print("-" * 65)
    print(f" Total Execution Time: {elapsed}s")
    if all_passed:
        print(" OVERALL STATUS: ALL TEST SUITES PASSED SUCCESSFULLY (100%)")
        print(" KnoQuest Enterprise Knowledge Agent is 100% Verified!")
    else:
        print(" OVERALL STATUS: SOME SUITES FAILED")
    print("=" * 65)
    return all_passed

if __name__ == "__main__":
    success = run_all_suites()
    sys.exit(0 if success else 1)
