"""Quick test of the agent with fallback LM."""
from agent.graph_hybrid import HybridAgent
import json

print("Initializing agent with fallback LM...")
try:
    agent = HybridAgent()
    print("OK: Agent initialized\n")
    
    # Test a simple RAG question
    question = "According to the product policy, what is the return window (days) for unopened Beverages? Return an integer."
    print(f"Question: {question}\n")
    
    result = agent.answer_question(
        question=question,
        format_hint="int",
        question_id="test1"
    )
    
    print("Result:")
    print(json.dumps(result, indent=2))
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
