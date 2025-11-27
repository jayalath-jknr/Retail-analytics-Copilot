"""DSPy signatures and modules for the hybrid agent."""
import dspy
from typing import Literal


# ============================================================================
# Signatures
# ============================================================================

class RouteQuery(dspy.Signature):
    """Classify whether a query needs RAG, SQL, or both (hybrid).
    
    - rag: Question answered from documents only (policies, definitions, dates)
    - sql: Question needs database queries only (pure numerical analysis)
    - hybrid: Question needs both documents (context/constraints) AND database (numbers)
    """
    
    question = dspy.InputField(desc="The user's analytics question")
    reasoning = dspy.OutputField(desc="Brief reasoning for classification")
    route = dspy.OutputField(desc="One of: rag, sql, or hybrid")


class GenerateSQL(dspy.Signature):
    """Generate SQLite query for Northwind database.
    
    Rules:
    - Use exact table names: Orders, "Order Details", Products, Customers, Categories
    - Revenue formula: SUM(UnitPrice * Quantity * (1 - Discount))
    - Always use proper JOINs
    - Return only valid SQLite syntax
    """
    
    question = dspy.InputField(desc="Natural language question")
    schema = dspy.InputField(desc="Database schema description")
    context = dspy.InputField(desc="Additional context from documents (if any)")
    sql_query = dspy.OutputField(desc="Valid SQLite query")


class RefineSQL(dspy.Signature):
    """Fix a SQL query that failed or returned incorrect results."""
    
    original_question = dspy.InputField(desc="The original question")
    failed_sql = dspy.InputField(desc="The SQL query that failed")
    error_message = dspy.InputField(desc="Error message or issue description")
    schema = dspy.InputField(desc="Database schema")
    refined_sql = dspy.OutputField(desc="Corrected SQL query")


class SynthesizeAnswer(dspy.Signature):
    """Synthesize a typed, formatted answer with citations.
    
    The answer MUST match the format_hint exactly:
    - int: return plain integer
    - float: return float rounded to 2 decimals
    - {key:type, ...}: return dict with exact keys
    - list[{...}]: return list of dicts
    """
    
    question = dspy.InputField(desc="Original question")
    format_hint = dspy.InputField(desc="Expected output format (int, float, dict, list)")
    doc_context = dspy.InputField(desc="Retrieved document chunks (if any)")
    sql_result = dspy.InputField(desc="SQL query result (if any)")
    reasoning = dspy.OutputField(desc="Brief explanation (<=2 sentences)")
    answer = dspy.OutputField(desc="Final answer matching format_hint exactly")


class ExtractConstraints(dspy.Signature):
    """Extract constraints from question and documents for SQL generation.
    
    Extract:
    - Date ranges (e.g., 1997-06-01 to 1997-06-30)
    - Categories (e.g., Beverages, Condiments)
    - KPI formulas (e.g., AOV, Gross Margin)
    - Customer/Product filters
    """
    
    question = dspy.InputField(desc="User question")
    doc_context = dspy.InputField(desc="Retrieved document text")
    constraints = dspy.OutputField(desc="Extracted constraints as structured text")


# ============================================================================
# Modules (wrappers around signatures)
# ============================================================================

class Router(dspy.Module):
    """Route queries to appropriate processing path."""
    
    def __init__(self):
        super().__init__()
        self.classify = dspy.ChainOfThought(RouteQuery)
    
    def forward(self, question: str) -> str:
        result = self.classify(question=question)
        route = result.route.lower().strip()
        
        # Normalize output
        if route in ['rag', 'sql', 'hybrid']:
            return route
        
        # Fallback logic
        if any(word in question.lower() for word in ['policy', 'return', 'window', 'days', 'definition']):
            return 'rag'
        elif any(word in question.lower() for word in ['revenue', 'top', 'total', 'sum', 'count']):
            if any(word in question.lower() for word in ['during', 'campaign', 'marketing', 'calendar']):
                return 'hybrid'
            return 'sql'
        
        return 'hybrid'  # Default to hybrid when uncertain


class NL2SQL(dspy.Module):
    """Natural language to SQL converter."""
    
    def __init__(self):
        super().__init__()
        self.generate = dspy.ChainOfThought(GenerateSQL)
    
    def forward(self, question: str, schema: str, context: str = "") -> str:
        result = self.generate(
            question=question,
            schema=schema,
            context=context or "No additional context"
        )
        return result.sql_query.strip()


class SQLRefiner(dspy.Module):
    """Refine failed SQL queries."""
    
    def __init__(self):
        super().__init__()
        self.refine = dspy.ChainOfThought(RefineSQL)
    
    def forward(self, question: str, failed_sql: str, error: str, schema: str) -> str:
        result = self.refine(
            original_question=question,
            failed_sql=failed_sql,
            error_message=error,
            schema=schema
        )
        return result.refined_sql.strip()


class AnswerSynthesizer(dspy.Module):
    """Synthesize final typed answers with citations."""
    
    def __init__(self):
        super().__init__()
        self.synthesize = dspy.ChainOfThought(SynthesizeAnswer)
    
    def forward(self, question: str, format_hint: str, doc_context: str, sql_result: str) -> tuple[str, str]:
        """Returns (reasoning, answer)."""
        result = self.synthesize(
            question=question,
            format_hint=format_hint,
            doc_context=doc_context or "No document context",
            sql_result=sql_result or "No SQL results"
        )
        return result.reasoning, result.answer


class ConstraintExtractor(dspy.Module):
    """Extract constraints for SQL generation."""
    
    def __init__(self):
        super().__init__()
        self.extract = dspy.Predict(ExtractConstraints)
    
    def forward(self, question: str, doc_context: str) -> str:
        result = self.extract(question=question, doc_context=doc_context)
        return result.constraints


# ============================================================================
# DSPy Configuration Helper
# ============================================================================

def configure_dspy_ollama(model_name: str = "phi3.5:3.8b-mini-instruct-q4_K_M"):
    """Configure DSPy to use Ollama with Phi-3.5-mini, with fallback."""
    try:
        # Try to import OllamaLocal (might not exist in all dspy versions)
        from dspy.clients.ollama import Ollama as OllamaClient
        lm = OllamaClient(
            model=model_name,
            max_tokens=512,
            temperature=0.1,
            timeout_s=60
        )
        dspy.settings.configure(lm=lm)
        print("OK: Using Ollama with Phi-3.5-mini")
        return True
    except Exception as e:
        print(f"WARNING: Ollama not available: {e}")
        print("OK: Using rule-based fallback for testing...")
        
        # Use our custom fallback
        from agent.fallback_lm import get_fallback_lm
        
        class FallbackDspyLM(dspy.LM):
            """Wrapper to make fallback compatible with DSPy."""
            def __init__(self):
                super().__init__(model="fallback-rule-based")
                self.fallback = get_fallback_lm()
                self.history = []
            
            def __call__(self, prompt=None, messages=None, **kwargs):
                text = prompt if prompt else str(messages)
                response = self.fallback(text)
                self.history.append({"prompt": text, "response": response})
                return [response]
            
            def basic_request(self, prompt, **kwargs):
                """DSPy BaseLM compatibility."""
                response = self.fallback(str(prompt))
                self.history.append({"prompt": prompt, "response": response})
                return {"choices": [{"text": response}]}
        
        lm = FallbackDspyLM()
        dspy.settings.configure(lm=lm)
        return False


if __name__ == "__main__":
    # Test configuration
    print("Testing DSPy modules...")
    configure_dspy_ollama()
    
    # Test router
    router = Router()
    test_questions = [
        "What is the return policy for beverages?",
        "Top 3 products by revenue",
        "Total revenue during Summer Beverages 1997"
    ]
    
    for q in test_questions:
        try:
            route = router.forward(q)
            print(f"Q: {q}")
            print(f"Route: {route}\n")
        except Exception as e:
            print(f"Error routing: {e}\n")
