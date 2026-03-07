#!/usr/bin/env python3
"""
GPU Arbitrage Oracle - Local LLM Debate Version

Step 1: DuckDuckGo search for GPU specs and prices
Step 2: Ollama local LLM debate (3 personalities)
Step 3: Loop until 2-1 consensus
Step 4: Log to oracle.log
"""

import os
import json
import datetime
from pathlib import Path

from ollama import Client
from ddgs import DDGS

LOG_FILE = Path(__file__).parent / "oracle.log"
GPU_MODELS = ["RTX 4090", "RTX 4080 Super", "RTX 4070 Ti Super", "RTX 5090", "RTX 5080", "RTX 5070 Ti"]
MAX_LOG_SIZE = 1048576  # 1MB

MODEL = "qwen3:4b"

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
ollama_client = Client(host=OLLAMA_HOST)


PERSONALITIES = {
    "Bag Holder": "You are a crypto investor who lost big on a memecoin. You need to recoup your losses by mining. Argue which GPU is the best for mining profitability. Use crypto slang like HODL, moon, rug-pull, based, and degen. Be aggressive and dismiss other opinions.",
    "Gamer": "You are a hardcore PC gamer who demands the best performance for high-refresh-rate gaming and Ray Tracing. Argue which GPU gives the most value for money. Use terms like FPS, bottleneck, raster, RT, and VRAM. Be dismissive of non-gaming concerns.",
    "Tree Hugger": "You are a fanatic Greenpeace activist who obsesses over carbon footprints, e-waste, and renewable energy. Argue which GPU is the most environmentally friendly. Be very judgmental of others' choices. Use terms like CO2, carbon footprint, e-waste, and sustainable."
}


def search_gpu_info(gpu_list: list[str]) -> str:
    """Search DuckDuckGo for GPU specs and prices"""
    print("\n[SEARCH] Starting DuckDuckGo searches...")
    results = []
    
    for gpu in gpu_list:
        print(f"[SEARCH] Searching for {gpu}...")
        try:
            with DDGS() as ddgs:
                # Search for specs
                specs_results = ddgs.text(f"{gpu} specs performance price 2025", max_results=3)
                specs_text = "\n".join([r['body'] for r in specs_results]) if specs_results else "No specs found"
                
                # Search for price
                price_results = ddgs.text(f"{gpu} price NVIDIA", max_results=3)
                price_text = "\n".join([r['body'] for r in price_results]) if price_results else "No prices found"
                
                results.append(f"\n=== {gpu} ===\nSPECS:\n{specs_text}\n\nPRICES:\n{price_text}")
                print(f"[SEARCH] Found info for {gpu}")
        except Exception as e:
            print(f"[SEARCH] Error searching for {gpu}: {e}")
            results.append(f"\n=== {gpu} ===\nError: {e}")
    
    return "\n".join(results)


def run_debate(gpu_list: list[str], search_results: str) -> dict:
    """Run the trio debate until 2-1 consensus"""
    print("\n[DEBATE] Starting Ollama debate...")
    
    names = list(PERSONALITIES.keys())
    round_num = 0
    max_rounds = 10
    
    full_transcript = f"DEBATE TOPIC: Best GPU for different needs\n"
    full_transcript += f"GPUs: {', '.join(gpu_list)}\n"
    full_transcript += f"Search results:\n{search_results}\n"
    full_transcript += "="*50 + "\n"
    
    round_summaries = []
    consensus = None
    
    current_context = f"The GPUs to debate: {', '.join(gpu_list)}\n\nSearch results:\n{search_results}\n\nEach person must argue for their preferred GPU based on their unique goals."
    
    while round_num < max_rounds and consensus is None:
        round_num += 1
        print(f"\n[DEBATE] Round {round_num}")
        
        round_args = []
        
        for name in names:
            print(f"[DEBATE] {name} is formulating...")
            
            system_prompt = f"{PERSONALITIES[name]} Keep your response concise (2-3 sentences max) but punchy. State clearly which GPU you recommend and WHY."
            
            try:
                response = ollama_client.chat(
                    model=MODEL,
                    messages=[
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': f"The current debate state:\n{current_context}\n\nWhat is your take? Which GPU do you recommend?"}
                    ],
                    options={'temperature': 0.85}
                )
                
                reply = response.message.content
                
                # Extract GPU recommendation and reason for summary
                summary = f"{name}: {reply}"
                round_args.append(summary)
                
                current_context = f"{name} said: {reply}"
                full_transcript += f"\n\n[ROUND {round_num} - {name.upper()}]:\n{reply}"
                
                print(f"[DEBATE] {name} finished.")
                
            except Exception as e:
                print(f"[DEBATE] Error with {name}: {e}")
                round_args.append(f"{name}: Error - {e}")
        
        # Create round summary
        round_summary = f"Round {round_num}:\n" + "\n".join([f"- {arg}" for arg in round_args])
        round_summaries.append(round_summary)
        
        print(f"\n[DEBATE] Round {round_num} summary:\n{round_summary}")
        
        # Check for 2-1 consensus
        gpu_mentions = {}
        for arg in round_args:
            for gpu in gpu_list:
                if gpu.lower() in arg.lower():
                    gpu_mentions[gpu] = gpu_mentions.get(gpu, 0) + 1
        
        if gpu_mentions:
            # Find majority
            max_mentions = max(gpu_mentions.values())
            if max_mentions >= 2:
                # Found consensus
                winners = [g for g, c in gpu_mentions.items() if c == max_mentions]
                consensus = {
                    "winner": winners[0] if len(winners) == 1 else winners,
                    "votes": max_mentions,
                    "round": round_num,
                    "all_mentions": gpu_mentions
                }
                full_transcript += f"\n\n=== CONSENSUS REACHED in Round {round_num} ==="
                full_transcript += f"\nWinner: {consensus['winner']} ({consensus['votes']}/3 votes)"
                print(f"\n[DEBATE] CONSENSUS: {consensus['winner']} wins with {consensus['votes']}/3 votes!")
    
    if consensus is None:
        consensus = {
            "winner": "NO CONSENSUS",
            "votes": 0,
            "round": round_num,
            "note": f"Debate ended after {round_num} rounds without consensus"
        }
        full_transcript += f"\n\n=== NO CONSENSUS REACHED ==="
    
    return {
        "full_transcript": full_transcript,
        "round_summaries": round_summaries,
        "consensus": consensus,
        "rounds": round_num
    }


def log_result(result: dict) -> None:
    """Log result to oracle.log"""
    rotate_log_if_needed()
    
    timestamp = datetime.datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "type": "oracle_debate",
        **result
    }
    
    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        print(f"\n[ORACLE] Result logged to {LOG_FILE}")
    except PermissionError:
        fallback = Path("/tmp/oracle.log")
        with open(fallback, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        print(f"\n[ORACLE] Result logged to {fallback}")


def rotate_log_if_needed() -> None:
    """Truncate oldest entries if log exceeds 1MB"""
    if not LOG_FILE.exists():
        return
    
    try:
        size = LOG_FILE.stat().st_size
    except PermissionError:
        return
    
    if size > MAX_LOG_SIZE:
        try:
            with open(LOG_FILE, 'r') as f:
                lines = f.readlines()
        except PermissionError:
            return
        
        total_size = size
        while total_size > MAX_LOG_SIZE and lines:
            removed = lines.pop(0)
            total_size -= len(removed.encode('utf-8'))
        
        try:
            with open(LOG_FILE, 'w') as f:
                f.writelines(lines)
            print(f"[ORACLE] Log rotated, removed old entries")
        except PermissionError:
            pass


def main():
    print("="*60)
    print("[ORACLE] GPU Arbitrage Oracle - Local LLM Debate")
    print("="*60)
    
    # Step 1: Search DuckDuckGo
    print("\n[STEP 1] Searching DuckDuckGo for GPU info...")
    search_results = search_gpu_info(GPU_MODELS)
    print(f"\n[SEARCH] Done! Got info for {len(GPU_MODELS)} GPUs")
    
    # Step 2: Run debate
    print("\n[STEP 2] Running Ollama debate...")
    debate_result = run_debate(GPU_MODELS, search_results)
    
    # Step 3: Log results
    print("\n[STEP 3] Logging results...")
    log_result(debate_result)
    
    # Print summary
    print("\n" + "="*60)
    print("[ORACLE] DEBATE SUMMARY")
    print("="*60)
    
    for summary in debate_result["round_summaries"]:
        print(f"\n{summary}")
    
    print(f"\n{'='*60}")
    print(f"FINAL RESULT: {debate_result['consensus']['winner']}")
    print(f"Rounds: {debate_result['rounds']}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
