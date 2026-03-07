import os
import sys
import datetime
from ollama import chat, web_fetch, web_search

# --- Configuration ---
# Set your OLLAMA_API_KEY as an environment variable in Docker
# or uncomment the line below:
# os.environ["OLLAMA_API_KEY"] = "your_key_here"

MODEL = 'qwen3:4b' # Lightweight & fast for 2026 laptops
available_tools = {'web_search': web_search, 'web_fetch': web_fetch}

def save_report(query, content):
    """Saves the final response to a timestamped text file."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"research_{timestamp}.txt"
    
    report_text = f"RESEARCH REPORT\n"
    report_text += f"Query: {query}\n"
    report_text += f"Date: {datetime.datetime.now().strftime('%B %d, %Y')}\n"
    report_text += "="*30 + "\n\n"
    report_text += content
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"\n[SUCCESS] Report saved to: {filename}")

def run_research(user_prompt):
    messages = [{'role': 'user', 'content': user_prompt}]
    print(f"--- Researching: {user_prompt} ---")

    # Limit to 5 loops to prevent "infinite research" on complex topics
    for turn in range(5):
        response = chat(
            model=MODEL,
            messages=messages,
            tools=[web_search, web_fetch],
            think=True, # Enables the Chain of Thought for Qwen3
            options={'num_ctx': 32768} # High context to read full web pages
        )

        # 1. Print Reasoning (Thinking)
        if response.message.thinking:
            print(f"\nThinking... \n{response.message.thinking[:200]}...")

        # 2. Handle Tool Calls
        messages.append(response.message)
        
        if response.message.tool_calls:
            for tool_call in response.message.tool_calls:
                func = available_tools.get(tool_call.function.name)
                if func:
                    print(f"[Tool] Running {tool_call.function.name}...")
                    try:
                        result = func(**tool_call.function.arguments)
                        # We truncate the tool result to 8k tokens to keep the context clean
                        messages.append({
                            'role': 'tool', 
                            'content': str(result)[:8000], 
                            'tool_name': tool_call.function.name
                        })
                    except Exception as e:
                        messages.append({'role': 'tool', 'content': f"Error: {e}", 'tool_name': tool_call.function.name})
            continue # Continue loop to let the model process the results

        # 3. Final Response
        if response.message.content:
            print("\nFinal Answer Received.")
            save_report(user_prompt, response.message.content)
            break

if __name__ == "__main__":
    if not os.getenv("OLLAMA_API_KEY"):
        print("Error: OLLAMA_API_KEY environment variable is missing.")
        sys.exit(1)

    user_query = "Why is red a color? Explain the physics of light and the cultural symbolism."
    run_research(user_query)