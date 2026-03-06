How to Use

```bash
cd gpu && python oracle_test.py
```

The script will:
1. Search for GPU prices using DuckDuckGo (Tool 1)
2. Analyze prices with GitHub Models gpt-4o-mini (Tool 2)
3. Calculate bargain scores and verdicts
4. Log results to oracle.log

Output:
- Prices found for each GPU
- Bargain scores (0-100)
- Verdict: STRONG_BUY, MODERATE_DEAL, OVERPRICED, or AVOID
