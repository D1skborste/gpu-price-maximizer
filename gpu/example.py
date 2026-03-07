import os
import datetime
from ollama import chat

MODEL = 'qwen3:4b'

def run_trio_debate(topic, rounds=2):
    personalities = {
        "Scientist": "You are a late memecoin investor trying to recapitalize your losses. Argue which option is the best for mining crypto to recoup your 'bags'. Use crypto slang like HODL, moon, and rug-pull.",
        "Gamer": "You are a hardcore PC gamer. Explain which option gives the most value for money when it comes to high-refresh-rate gaming and Ray Tracing. Use terms like FPS, bottleneck, and RGB.",
        "Tree Hugger": "You are a fanatic Greenpeace activist. Argue for the most environmentally friendly option. Obsess over carbon footprints, e-waste, and renewable energy. Be very judgmental."
    }

    # Initialize conversation
    names = list(personalities.keys())
    transcript = f"DEBATE TOPIC: {topic}\n" + "="*50 + "\n"
    
    # The starting prompt
    current_context = f"The topic is: {topic}. Each of you must argue for the best choice based on your unique goals."
    
    # We loop through the roles multiple times
    for r in range(rounds):
        for name in names:
            print(f"[{name}] is formulating a response...")
            
            # System prompt defines the personality
            system_prompt = f"{personalities[name]} Keep your response concise but punchy."
            
            # Call the LLM
            response = chat(
                model=MODEL,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': f"The current debate state is: {current_context}. What is your take?"}
                ],
                options={'temperature': 0.85} # Higher temp for more personality
            )
            
            reply = response.message.content
            
            # Update the context so the next person knows what was said
            current_context = f"{name} said: {reply}"
            
            # Add to transcript
            entry = f"\n[{name.upper()}]:\n{reply}\n"
            transcript += entry
            print(f"{name} finished speaking.")

    # Save to file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"trio_debate_{timestamp}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(transcript)
    
    print(f"\n[DONE] Debate finished. Full transcript saved to {filename}")

if __name__ == "__main__":
    # Example topic for these personalities
    debate_topic = "Should we buy a used NVIDIA RTX 3090 or a brand new RTX 4060 Ti?"
    run_trio_debate(debate_topic)