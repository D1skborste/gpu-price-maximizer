#!/usr/bin/env python3
"""Oracle Master - Orchestrates GPU search and debate"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


def run_script(script_name: str) -> bool:
    """Run a Python script and return success status"""
    script_path = SCRIPT_DIR / script_name
    print(f"\n{'='*60}")
    print(f"[MASTER] Running {script_name}...")
    print(f"{'='*60}\n")
    
    result = subprocess.run([sys.executable, str(script_path)])
    return result.returncode == 0


def main():
    print("="*60)
    print("[MASTER] GPU Price Maximizer - Oracle Master")
    print("="*60)
    
    # Step 1: GPU Search (commented out for testing)
    # print("\n[MASTER] Step 1: GPU Search")
    # if not run_script("gpu_search.py"):
    #     print("[MASTER] GPU search failed!")
    #     return
    
    # Step 2: Debate
    print("\n[MASTER] Step 2: LLM Debate")
    if not run_script("debate.py"):
        print("[MASTER] Debate failed!")
        return
    
    print("\n" + "="*60)
    print("[MASTER] Done!")
    print("="*60)


if __name__ == "__main__":
    main()
