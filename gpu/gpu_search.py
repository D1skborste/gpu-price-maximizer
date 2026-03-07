#!/usr/bin/env python3
"""GPU Search - Searches DuckDuckGo for GPU info and saves to oracle.log"""

import os
import json
import datetime
from pathlib import Path

from ddgs import DDGS

LOG_FILE = Path(__file__).parent / "oracle_search.log"
GPU_MODELS = ["RTX 4090", "RTX 4080 Super", "RTX 4070 Ti Super", "RTX 5090", "RTX 5080", "RTX 5070 Ti"]
MAX_LOG_SIZE = 1048576  # 1MB


def search_gpu_info(gpu_list: list[str]) -> str:
    """Search DuckDuckGo for GPU specs and prices"""
    print("\n[SEARCH] Starting DuckDuckGo searches...")
    results = []
    
    for gpu in gpu_list:
        print(f"[SEARCH] Searching for {gpu}...")
        try:
            with DDGS() as ddgs:
                specs_results = ddgs.text(f"{gpu} specs performance price 2025", max_results=3)
                specs_text = "\n".join([r['body'] for r in specs_results]) if specs_results else "No specs found"
                
                price_results = ddgs.text(f"{gpu} price NVIDIA", max_results=3)
                price_text = "\n".join([r['body'] for r in price_results]) if price_results else "No prices found"
                
                results.append(f"\n=== {gpu} ===\nSPECS:\n{specs_text}\n\nPRICES:\n{price_text}")
                print(f"[SEARCH] Found info for {gpu}")
        except Exception as e:
            print(f"[SEARCH] Error searching for {gpu}: {e}")
            results.append(f"\n=== {gpu} ===\nError: {e}")
    
    return "\n".join(results)


def log_search_results(search_results: str) -> None:
    """Log search results to oracle.log"""
    if not LOG_FILE.exists():
        LOG_FILE.touch()
    
    try:
        size = LOG_FILE.stat().st_size
    except PermissionError:
        size = 0
    
    if size > MAX_LOG_SIZE:
        try:
            with open(LOG_FILE, 'r') as f:
                lines = f.readlines()
        except PermissionError:
            lines = []
        
        total_size = size
        while total_size > MAX_LOG_SIZE and lines:
            removed = lines.pop(0)
            total_size -= len(removed.encode('utf-8'))
        
        try:
            with open(LOG_FILE, 'w') as f:
                f.writelines(lines)
            print(f"[SEARCH] Log rotated, removed old entries")
        except PermissionError:
            pass
    
    timestamp = datetime.datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "type": "gpu_search",
        "search_results": search_results,
        "gpus": GPU_MODELS
    }
    
    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        print(f"\n[SEARCH] Results logged to {LOG_FILE}")
    except PermissionError:
        print(f"\n[SEARCH] Error: Cannot write to {LOG_FILE}")


def main():
    print("="*60)
    print("[SEARCH] GPU Search - DuckDuckGo")
    print("="*60)
    
    search_results = search_gpu_info(GPU_MODELS)
    print(f"\n[SEARCH] Done! Got info for {len(GPU_MODELS)} GPUs")
    
    log_search_results(search_results)
    
    return search_results


if __name__ == "__main__":
    main()
