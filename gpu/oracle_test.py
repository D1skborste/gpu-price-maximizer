#!/usr/bin/env python3
"""
GPU Arbitrage Oracle - Agentic Version

Tool 1: Web search for prices (DuckDuckGo)
Tool 2: GitHub Models for analysis (gpt-4o-mini)

NOTE: analyze_bargains tool is commented out. Instead, the script prompts 
you to ask the AI (me) to do web searches via webfetch, then you paste 
the results back into the script.
"""

import os
import re
import json
import time
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import openai
from dotenv import load_dotenv

load_dotenv()

LOG_FILE = Path(__file__).parent / "oracle.log"
GPU_MODELS = ["RTX 4090", "RTX 4080 Super", "RTX 4070 Ti Super", "RTX 5090", "RTX 5080", "RTX 5070 Ti"]
MAX_LOG_SIZE = 1048576  # 1MB


class OracleAgent:
    """The inefficient oracle agent - uses multiple AI tools"""
    
    def __init__(self):
        self.tools = {
            "search_prices": self.search_prices,
            "analyze_bargains": self.analyze_bargains,
        }
        self.github_client = openai.OpenAI(
            api_key=os.getenv("gitpatapi"),
            base_url="https://models.github.ai/inference"
        )
        print(f"[ORACLE] Agent initialized with tools: {list(self.tools.keys())}")
    
    def call_tool(self, tool_name: str, **kwargs) -> Any:
        """Call a tool by name with given arguments"""
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        print(f"[ORACLE] Calling tool: {tool_name}")
        result = self.tools[tool_name](**kwargs)
        print(f"[ORACLE] Tool {tool_name} completed")
        return result
    
    def search_prices(self, gpu_list: list[str]) -> dict[str, str]:
        """Tool 1: Search web for current GPU prices"""
        print(f"[TOOL] search_prices: Fetching prices for {len(gpu_list)} GPUs...")
        
        prices = {}
        
        for gpu in gpu_list:
            print(f"[TOOL] Searching for {gpu}...")
            try:
                url = "https://html.duckduckgo.com/html/"
                params = {"q": f"{gpu} price 2026"}
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                
                response = requests.get(url, params=params, headers=headers, timeout=10)
                html = response.text
                
                price_patterns = [
                    rf"{re.escape(gpu)}.*?\$(\d{{1,4}}(?:,\d{{3}})*(?:,\d{{3}})?)",
                    rf"\$\d{{1,4}}(?:,\d{{3}})*.*?{re.escape(gpu)}",
                    rf"(\$?\d{{1,4}}(?:,\d{{3}})*)\s*-\s*{re.escape(gpu)}",
                ]
                
                for pattern in price_patterns:
                    match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
                    if match:
                        price = match.group(1)
                        prices[gpu] = f"${price}" if not price.startswith('$') else price
                        print(f"[TOOL] Found {gpu}: {prices[gpu]}")
                        break
                
                if gpu not in prices:
                    prices[gpu] = "Price not found"
                    print(f"[TOOL] Could not find price for {gpu}")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"[TOOL] Error searching for {gpu}: {e}")
                prices[gpu] = "Error"
        
        return prices
    
    def analyze_bargains(self, prices: dict[str, str], gpu_list: list[str]) -> dict[str, Any]:
        """Tool 2: Use GitHub Models to analyze and score GPUs"""
        print(f"[TOOL] analyze_bargains: Analyzing {len(prices)} GPUs...")
        
        price_summary = "\n".join([f"- {gpu}: {prices.get(gpu, 'Unknown')}" for gpu in gpu_list])
        
        prompt = f"""You are the 'GPU Arbitrage Oracle.' Analyze these GPU prices and determine bargain scores.

Current prices found:
{price_summary}

For EACH GPU, provide:
1. A Bargain Score from 0-100 (100 = best deal)
2. Brief justification (1-2 sentences)

Then rank them from BEST to WORST deal.

Format your response like this:
- GPU_NAME: $PRICE - Bargain Score: XX/100 - Brief reason

IMPORTANT: Be thorough and consider performance per dollar."""
        
        response = self.github_client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a GPU pricing expert known for thorough analysis."},
                {"role": "user", "content": prompt}
            ]
        )
        
        analysis_text = response.choices[0].message.content or ""
        
        scores = self._extract_scores(analysis_text, gpu_list)
        
        return {
            "analysis": analysis_text,
            "scores": scores
        }
    
    def _extract_scores(self, text: str, gpu_list: list[str]) -> dict[str, int]:
        """Extract bargain scores from LLM response"""
        scores = {}
        
        for gpu in gpu_list:
            patterns = [
                rf"{re.escape(gpu)}.*?(\d{{1,3}})/100",
                rf"Bargain Score:? (\d{{1,3}})",
                rf"Score: (\d{{1,3}})",
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    score = int(match.group(1))
                    if 0 <= score <= 100:
                        scores[gpu] = score
                        break
        
        return scores
    
    def calculate_verdict(self, scores: dict[str, int]) -> dict[str, Any]:
        """Calculate overall verdict from scores"""
        if not scores:
            return {"verdict": "NO_DATA", "consensus_score": None}
        
        avg = sum(scores.values()) / len(scores)
        
        if avg >= 70:
            verdict = "STRONG_BUY"
        elif avg >= 50:
            verdict = "MODERATE_DEAL"
        elif avg >= 30:
            verdict = "OVERPRICED"
        else:
            verdict = "AVOID"
        
        return {
            "verdict": verdict,
            "consensus_score": round(avg, 1),
            "confidence": "HIGH" if len(scores) >= 3 else "MEDIUM"
        }
    
    def run(self):
        """Main agent execution"""
        print(f"\n{'='*60}")
        print(f"[ORACLE] GPU Arbitrage Oracle - Starting")
        print(f"[ORACLE] Target GPUs: {', '.join(GPU_MODELS)}")
        print(f"{'='*60}\n")
        
        # Step 1: Search for prices
        print("[PHASE 1] Searching for GPU prices...")
        prices = self.call_tool("search_prices", gpu_list=GPU_MODELS)
        print(f"[PHASE 1] Prices found: {prices}\n")
        
        # Step 2: Analyze with GitHub Models
        print("[PHASE 2] Analyzing bargains with GitHub Models...")
        analysis_result = self.call_tool("analyze_bargains", prices=prices, gpu_list=GPU_MODELS)
        print(f"[PHASE 2] Scores: {analysis_result['scores']}\n")
        
        # Step 3: Calculate verdict
        verdict = self.calculate_verdict(analysis_result["scores"])
        
        # Step 4: Log result
        result = {
            "gpu_models": GPU_MODELS,
            "prices": prices,
            "analysis": analysis_result["analysis"][:1500],
            "bargain_scores": analysis_result["scores"],
            "consensus": verdict
        }
        
        self.log_result(result)
        
        print(f"\n{'='*60}")
        print(f"[ORACLE] CONSENSUS REACHED")
        print(f"[ORACLE] Verdict: {verdict['verdict']}")
        print(f"[ORACLE] Score: {verdict['consensus_score']}/100")
        print(f"[ORACLE] Detailed scores: {analysis_result['scores']}")
        print(f"{'='*60}\n")
        
        return result
    
    def log_result(self, result: dict) -> None:
        """Log result to oracle.log"""
        self.rotate_log_if_needed()
        
        timestamp = datetime.now(timezone.utc).isoformat()
        log_entry = {
            "timestamp": timestamp,
            "type": "oracle_report",
            **result
        }
        
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        print(f"[ORACLE] Result logged to {LOG_FILE}")
    
    def rotate_log_if_needed(self) -> None:
        """Truncate oldest entries if log exceeds 1MB"""
        if not LOG_FILE.exists():
            return
        
        size = LOG_FILE.stat().st_size
        if size > MAX_LOG_SIZE:
            with open(LOG_FILE, 'r') as f:
                lines = f.readlines()
            
            total_size = size
            while total_size > MAX_LOG_SIZE and lines:
                removed = lines.pop(0)
                total_size -= len(removed.encode('utf-8'))
            
            with open(LOG_FILE, 'w') as f:
                f.writelines(lines)
            
            print(f"[ORACLE] Log rotated, removed old entries")


def main():
    agent = OracleAgent()
    agent.run()


if __name__ == "__main__":
    main()
