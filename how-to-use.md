# How to Use

## Run the GPU Oracle

```bash
cd gpu
pip install -r requirements.txt
python oracle_test.py
```

## What It Does

1. **Step 1**: Searches DuckDuckGo for GPU specs and prices
2. **Step 2**: Runs Ollama local LLM debate (qwen3:4b)
3. **Step 3**: Loops until 2-1 consensus reached
4. **Step 4**: Logs to oracle.log

## Debate Personalities

| Personality | Goal | Style |
|-------------|------|-------|
| **Bag Holder** | Recoup crypto losses via mining | HODL, moon, rug-pull |
| **Gamer** | Best FPS/ray tracing value | FPS, bottleneck, VRAM |
| **Tree Hugger** | Most environmentally friendly | CO2, carbon footprint, e-waste |

## Output

- Full debate transcript in oracle.log
- Condensed round summaries
- Final consensus (2-1 majority)

## Requirements

- Ollama installed and running
- qwen3:4b model pulled: `ollama pull qwen3:4b`
- Python packages: `pip install -r requirements.txt`
