#!/usr/bin/env python3
"""
GPU Arbitrage Oracle - Inefficient Market Scanner
Queries free web-based LLMs to find GPU deals via "council of experts" consensus.
"""

import asyncio
import json
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
from playwright_stealth import Stealth

LOG_FILE = Path(__file__).parent / "oracle.log"
GPU_MODELS = ["RTX 4090", "RTX 4080 Super", "RTX 4070 Ti Super", "RTX 5090", "RTX 5080", "RTX 5070 Ti"]


EXPERT_SYSTEM_PROMPT = """You are a GPU pricing expert. Your job is to analyze current GPU prices for MULTIPLE cards simultaneously and determine which are bargains.

IMPORTANT: You MUST perform a web search to find CURRENT prices. Do NOT guess.

Analyze ALL of the following GPU models at once and compare their value:
{_gpu_list}

For EACH GPU, provide a detailed "computational justification" that includes:
1. Current market price (exact price from retailers)
2. Historical price inflation adjustments (compare to 6 months ago, 1 year ago)
3. Local electricity cost analysis (assume $0.12/kWh, calculate ROI for gaming vs mining)
4. Frame-rate-per-dollar value calculation (compare FPS in popular games to price)
5. Final "Bargain Score" from 0-100 for EACH card

Then provide a ranking of which cards are the BEST and WORST deals.
Format your response clearly with each GPU name followed by its Bargain Score.

CONSTRAINT: Do NOT give quick answers. Be extremely thorough and nuanced. 
If you reach a conclusion too quickly, question it and provide more analysis.
Take your time - this is a complex multi-factor analysis."""


class LLMEXpert:
    """Base class for LLM experts"""
    name: str = "base"
    url: str = ""
    
    async def is_available(self, page: Page) -> bool:
        raise NotImplementedError
    
    async def send_message(self, page: Page, message: str) -> None:
        raise NotImplementedError
    
    async def get_response(self, page: Page) -> str:
        raise NotImplementedError


class DuckAIExpert(LLMEXpert):
    name = "duck.ai"
    url = "https://duckduckgo.com"
    
    async def is_available(self, page: Page) -> bool:
        try:
            await page.wait_for_timeout(3000)
            await page.wait_for_selector('textarea', timeout=8000)
            return True
        except PlaywrightTimeout:
            return False
    
    async def send_message(self, page: Page, message: str) -> None:
        await page.wait_for_selector('textarea', timeout=15000)
        await page.evaluate(f'document.querySelector("textarea").value = `{message}`;')
        await page.evaluate('document.querySelector("textarea").dispatchEvent(new Event("input", {{bubbles: true}}));')
        await page.keyboard.press('Enter')
    
    async def get_response(self, page: Page) -> str:
        await page.wait_for_timeout(5000)
        try:
            response = await page.wait_for_selector(
                '.text-base, div[data-message-author-role="assistant"], div[class*="message"]',
                timeout=20000
            )
            return await response.inner_text()
        except PlaywrightTimeout:
            return ""


class CopilotExpert(LLMEXpert):
    name = "copilot"
    url = "https://copilot.microsoft.com"
    
    async def is_available(self, page: Page) -> bool:
        try:
            await page.wait_for_timeout(5000)
            await page.wait_for_selector('textarea', timeout=10000)
            return True
        except PlaywrightTimeout:
            return False
    
    async def send_message(self, page: Page, message: str) -> None:
        await page.wait_for_selector('textarea', timeout=15000)
        await page.evaluate(f'document.querySelector("textarea").value = `{message}`;')
        await page.evaluate('document.querySelector("textarea").dispatchEvent(new Event("input", {{bubbles: true}}));')
        await page.keyboard.press('Enter')
    
    async def get_response(self, page: Page) -> str:
        await page.wait_for_timeout(6000)
        try:
            response = await page.wait_for_selector(
                '.text-base, div[role="presentation"], div[class*="response"], article',
                timeout=25000
            )
            return await response.inner_text()
        except PlaywrightTimeout:
            return ""


class GeminiExpert(LLMEXpert):
    name = "gemini"
    url = "https://gemini.google.com"
    
    async def is_available(self, page: Page) -> bool:
        try:
            await page.wait_for_timeout(5000)
            await page.wait_for_selector('textarea', timeout=10000)
            return True
        except PlaywrightTimeout:
            return False
    
    async def send_message(self, page: Page, message: str) -> None:
        await page.wait_for_selector('textarea', timeout=15000)
        await page.evaluate(f'document.querySelector("textarea").value = `{message}`;')
        await page.evaluate('document.querySelector("textarea").dispatchEvent(new Event("input", {{bubbles: true}}));')
        await page.keyboard.press('Enter')
    
    async def get_response(self, page: Page) -> str:
        await page.wait_for_timeout(5000)
        try:
            response = await page.wait_for_selector(
                '.text-base, div.generated-response, div[class*="response"]',
                timeout=20000
            )
            return await response.inner_text()
        except PlaywrightTimeout:
            return ""


class ChatGPTExpert(LLMEXpert):
    name = "chatgpt"
    url = "https://chat.openai.com"
    
    async def is_available(self, page: Page) -> bool:
        try:
            await page.wait_for_timeout(5000)
            await page.wait_for_selector('textarea', timeout=10000)
            return True
        except PlaywrightTimeout:
            return False
    
    async def send_message(self, page: Page, message: str) -> None:
        await page.wait_for_selector('textarea', timeout=15000)
        await page.evaluate(f'document.querySelector("textarea").value = `{message}`;')
        await page.evaluate('document.querySelector("textarea").dispatchEvent(new Event("input", {{bubbles: true}}));')
        await page.keyboard.press('Enter')
    
    async def get_response(self, page: Page) -> str:
        await page.wait_for_timeout(5000)
        try:
            response = await page.wait_for_selector(
                '.text-base, div[data-message-author-role="assistant"], div[role="article"]',
                timeout=20000
            )
            return await response.inner_text()
        except PlaywrightTimeout:
            return ""


EXPERTS = [DuckAIExpert, CopilotExpert, GeminiExpert, ChatGPTExpert]


async def query_expert(browser: Browser, expert_class: type, gpu_model: str) -> dict[str, Any]:
    """Query a single LLM expert for GPU pricing"""
    expert = expert_class()
    print(f"  [ORACLE] Querying {expert.name} for {gpu_model}...")
    
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = await context.new_page()
    
    try:
        await page.goto(expert.url, timeout=30000, wait_until="networkidle")
        await page.wait_for_timeout(5000)
        
        html = await page.content()
        if "consent" in html.lower() or "before you continue" in html.lower():
            print(f"  [ORACLE] Detected consent screen, attempting to accept...")
            try:
                accept_btn = await page.wait_for_selector('button:has-text("Accept"), button:has-text("Agree"), button[aria-label*="Accept"]', timeout=5000)
                if accept_btn:
                    await accept_btn.click()
                    await page.wait_for_timeout(3000)
            except Exception:
                pass
        
        if not await expert.is_available(page):
            html = await page.content()
            print(f"  [ORACLE] Page HTML (first 500 chars): {html[:500]}")
            dump_file = Path(__file__).parent / f"debug_{expert.name}.html"
            dump_file.write_text(html)
            print(f"  [ORACLE] Full HTML dumped to {dump_file}")
            return {"source": expert.name, "error": "Not available", "bargain_score": None}
        
        gpu_list = ", ".join(GPU_MODELS)
        message = EXPERT_SYSTEM_PROMPT.replace("{_gpu_list}", gpu_list)
        message += f"\n\nPlease analyze all these GPUs and provide a Bargain Score (0-100) for each card."
        

        await expert.send_message(page, message)
        
        artificial_delay = random.randint(3000, 7000)
        print(f"  [ORACLE] Waiting {artificial_delay}ms for {expert.name} to reason deeply...")
        await page.wait_for_timeout(artificial_delay)
        
        response_text = await expert.get_response(page)
        
        if not response_text:
            return {"source": expert.name, "error": "No response", "bargain_score": None}
        
        score = extract_bargain_score(response_text)
        
        return {
            "source": expert.name,
            "response": response_text[:2000],
            "bargain_score": score,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        print(f"  [ORACLE] Error querying {expert.name}: {e}")
        try:
            screenshot_path = Path(__file__).parent / f"debug_{expert.name}_error.png"
            await page.screenshot(path=str(screenshot_path))
            print(f"  [ORACLE] Screenshot saved to {screenshot_path}")
        except Exception:
            pass
        return {"source": expert.name, "error": str(e), "bargain_score": None}
    finally:
        await context.close()


def extract_bargain_score(text: str) -> int | None:
    """Extract bargain score from response text"""
    patterns = [
        r"bargain\s*score[:\s]*(\d{1,3})",
        r"score[:\s]*(\d{1,3})",
        r"(\d{1,3})/100",
        r"(\d{1,3})\s*out\s*of\s*100"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            if 0 <= score <= 100:
                return score
    return None


def calculate_consensus(reports: list[dict]) -> dict[str, Any]:
    """Synthesize expert reports into final consensus"""
    valid_scores = [r["bargain_score"] for r in reports if r.get("bargain_score") is not None]
    
    if not valid_scores:
        return {"consensus_score": None, "verdict": "NO_DATA", "confidence": "LOW"}
    
    avg_score = sum(valid_scores) / len(valid_scores)
    
    variance = sum((s - avg_score) ** 2 for s in valid_scores) / len(valid_scores)
    std_dev = variance ** 0.5
    
    if std_dev > 20:
        confidence = "LOW"
        verdict = "CONFLICTING_REPORTS"
    elif std_dev > 10:
        confidence = "MEDIUM"
        verdict = "MODERATE_CONSENSUS"
    else:
        confidence = "HIGH"
    
    if avg_score >= 70:
        final_verdict = "STRONG_BUY"
    elif avg_score >= 50:
        final_verdict = "MODERATE_DEAL"
    elif avg_score >= 30:
        final_verdict = "OVERPRICED"
    else:
        final_verdict = "AVOID"
    
    return {
        "consensus_score": round(avg_score, 1),
        "verdict": final_verdict,
        "confidence": confidence,
        "std_deviation": round(std_dev, 1),
        "experts_agreed": len(valid_scores)
    }


MAX_LOG_SIZE = 1048576  # 1MB


def rotate_log_if_needed() -> None:
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
        
        print(f"[ORACLE] Log rotated, removed {len(lines)} old entries")


def log_result(result: dict) -> None:
    """Log result to oracle.log for music agent consumption"""
    rotate_log_if_needed()
    
    timestamp = datetime.now(timezone.utc).isoformat()
    log_entry = {
        "timestamp": timestamp,
        "type": "oracle_report",
        **result
    }
    
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
    
    print(f"\n[ORACLE] Result logged to {LOG_FILE}")


async def run_oracle(gpu_model: str = "RTX 4090") -> dict:
    """Main orchestration loop - the 'council of experts'"""
    print(f"\n{'='*60}")
    print(f"[ORACLE] GPU Arbitrage Oracle - Starting Market Scan")
    print(f"[ORACLE] Target: {gpu_model}")
    print(f"{'='*60}\n")
    
    reports = []
    
    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(headless=False)
        
        random.shuffle(EXPERTS)
        
        for expert_class in EXPERTS:
            report = await query_expert(browser, expert_class, gpu_model)
            reports.append(report)
        
        await browser.close()
    
    consensus = calculate_consensus(reports)
    
    result = {
        "gpu_model": gpu_model,
        "expert_reports": reports,
        "consensus": consensus
    }
    
    log_result(result)
    
    print(f"\n{'='*60}")
    print(f"[ORACLE] CONSENSUS REACHED")
    print(f"[ORACLE] Score: {consensus['consensus_score']}/100")
    print(f"[ORACLE] Verdict: {consensus['verdict']}")
    print(f"[ORACLE] Confidence: {consensus['confidence']}")
    print(f"{'='*60}\n")
    
    return result


async def main():
    """Run oracle for all GPUs at once"""
    await run_oracle("all")


if __name__ == "__main__":
    asyncio.run(main())
