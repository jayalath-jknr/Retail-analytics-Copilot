"""LangGraph-based hybrid agent with repair loop."""
import json
from typing import TypedDict, Annotated, Literal
from pathlib import Path
import operator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agent.dspy_signatures import (
    Router, NL2SQL, SQLRefiner, AnswerSynthesizer,
    ConstraintExtractor, configure_dspy_ollama
)
from agent.rag.retrieval import SimpleRetriever, DocumentChunk
from agent.tools.sqlite_tool import NorthwindDB, QueryResult


# ============================================================================
# State Definition
# ============================================================================

class AgentState(TypedDict):
    """State tracked through the agent graph."""
    # Input
    question: str
    format_hint: str
    
    # Routing
    route: str  # rag, sql, or hybrid
    
    # RAG
    retrieved_chunks: list[DocumentChunk]
    doc_context: str
    
    # Planning
    constraints: str
    
    # SQL
    sql_query: str
    sql_result: QueryResult
    sql_attempts: int
    
    # Synthesis
    final_answer: any
    reasoning: str
    confidence: float
    citations: list[str]
    
    # Repair
    repair_count: int
    errors: Annotated[list[str], operator.add]
    
    # Trace
    trace_events: Annotated[list[dict], operator.add]


# ============================================================================
# Agent Implementation
# ============================================================================

class HybridAgent:
    """Hybrid RAG + SQL agent with repair loop."""
    
    def __init__(self, docs_path: str = "docs", db_path: str = "data/northwind.sqlite"):
        # Initialize components
        self.retriever = SimpleRetriever(docs_path)
        self.db = NorthwindDB(db_path)
        
        # Configure DSPy
        configure_dspy_ollama()
        
        # Initialize DSPy modules
        self.router = Router()
        self.nl2sql = NL2SQL()
        self.sql_refiner = SQLRefiner()
        self.synthesizer = AnswerSynthesizer()
        self.constraint_extractor = ConstraintExtractor()
        
        # Build graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("route", self._route_node)
        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("plan", self._plan_node)
        workflow.add_node("generate_sql", self._generate_sql_node)
        workflow.add_node("execute_sql", self._execute_sql_node)
        workflow.add_node("synthesize", self._synthesize_node)
        workflow.add_node("validate", self._validate_node)
        workflow.add_node("repair_sql", self._repair_sql_node)
        
        # Set entry point
        workflow.set_entry_point("route")
        
        # Routing logic
        workflow.add_conditional_edges(
            "route",
            self._route_decision,
            {
                "rag": "retrieve",
                "sql": "plan",
                "hybrid": "retrieve"
            }
        )
        
        # RAG path
        workflow.add_edge("retrieve", "plan")
        
        # Planning to SQL
        workflow.add_conditional_edges(
            "plan",
            self._needs_sql,
            {
                "yes": "generate_sql",
                "no": "synthesize"
            }
        )
        
        # SQL execution flow
        workflow.add_edge("generate_sql", "execute_sql")
        
        workflow.add_conditional_edges(
            "execute_sql",
            self._check_sql_success,
            {
                "success": "synthesize",
                "retry": "repair_sql",
                "fail": "synthesize"
            }
        )
        
        # Repair loop
        workflow.add_edge("repair_sql", "execute_sql")
        
        # Validation and completion
        workflow.add_conditional_edges(
            "synthesize",
            self._check_synthesis,
            {
                "valid": "validate",
                "retry": "synthesize",
                "done": "validate"
            }
        )
        
        workflow.add_edge("validate", END)
        
        return workflow.compile(checkpointer=MemorySaver())
    
    # ========================================================================
    # Node Implementations
    # ========================================================================
    
    def _route_node(self, state: AgentState) -> AgentState:
        """Node 1: Route the query."""
        route = self.router.forward(state["question"])
        
        state["route"] = route
        state["trace_events"] = [{"node": "route", "route": route}]
        state["repair_count"] = 0
        state["sql_attempts"] = 0
        state["errors"] = []
        
        return state
    
    def _retrieve_node(self, state: AgentState) -> AgentState:
        """Node 2: Retrieve relevant document chunks."""
        chunks = self.retriever.retrieve(state["question"], top_k=3)
        
        doc_context = "\n\n".join([
            f"[{chunk.id}] {chunk.content}"
            for chunk in chunks
        ])
        
        state["retrieved_chunks"] = chunks
        state["doc_context"] = doc_context
        state["trace_events"] = [{"node": "retrieve", "chunks": len(chunks)}]
        
        return state
    
    def _plan_node(self, state: AgentState) -> AgentState:
        """Node 3: Extract constraints and plan query."""
        doc_ctx = state.get("doc_context", "")
        
        if doc_ctx:
            constraints = self.constraint_extractor.forward(
                state["question"], 
                doc_ctx
            )
        else:
            constraints = "No document context available."
        
        state["constraints"] = constraints
        state["trace_events"] = [{"node": "plan", "constraints": constraints[:100]}]
        
        return state
    
    def _generate_sql_node(self, state: AgentState) -> AgentState:
        """Node 4: Generate SQL query."""
        schema = self.db.get_compact_schema()
        context = state.get("constraints", "") or state.get("doc_context", "")
        
        sql = self.nl2sql.forward(
            question=state["question"],
            schema=schema,
            context=context
        )
        
        state["sql_query"] = sql
        state["sql_attempts"] += 1
        state["trace_events"] = [{"node": "generate_sql", "sql": sql}]
        
        return state
    
    def _execute_sql_node(self, state: AgentState) -> AgentState:
        """Node 5: Execute SQL query."""
        result = self.db.execute_query(state["sql_query"])
        
        state["sql_result"] = result
        state["trace_events"] = [{
            "node": "execute_sql",
            "success": result.success,
            "rows": len(result.rows) if result.rows else 0
        }]
        
        if not result.success:
            state["errors"] = [result.error]
        
        return state
    
    def _repair_sql_node(self, state: AgentState) -> AgentState:
        """Node 8: Repair failed SQL."""
        schema = self.db.get_compact_schema()
        error = state["sql_result"].error or "Query returned no results"
        
        refined_sql = self.sql_refiner.forward(
            question=state["question"],
            failed_sql=state["sql_query"],
            error=error,
            schema=schema
        )
        
        state["sql_query"] = refined_sql
        state["sql_attempts"] += 1
        state["repair_count"] += 1
        state["trace_events"] = [{"node": "repair_sql", "attempt": state["repair_count"]}]
        
        return state
    
    def _synthesize_node(self, state: AgentState) -> AgentState:
        """Node 6: Synthesize final answer."""
        doc_ctx = state.get("doc_context", "")
        
        # Format SQL result
        sql_result_str = ""
        if state.get("sql_result"):
            result = state["sql_result"]
            if result.success and result.rows:
                sql_result_str = f"Columns: {result.columns}\nRows: {result.rows[:10]}"
        
        reasoning, answer_str = self.synthesizer.forward(
            question=state["question"],
            format_hint=state["format_hint"],
            doc_context=doc_ctx,
            sql_result=sql_result_str
        )
        
        # Parse answer based on format_hint
        final_answer = self._parse_answer(answer_str, state["format_hint"])
        
        # Collect citations
        citations = []
        
        # Add document citations
        for chunk in state.get("retrieved_chunks", []):
            if chunk.score > 0.01:  # Only significant matches
                citations.append(chunk.id)
        
        # Add SQL table citations
        if state.get("sql_result") and state["sql_result"].success:
            citations.extend(state["sql_result"].tables_used or [])
        
        # Calculate confidence
        confidence = self._calculate_confidence(state)
        
        state["final_answer"] = final_answer
        state["reasoning"] = reasoning
        state["confidence"] = confidence
        state["citations"] = list(set(citations))  # Deduplicate
        state["trace_events"] = [{"node": "synthesize", "confidence": confidence}]
        
        return state
    
    def _validate_node(self, state: AgentState) -> AgentState:
        """Node 7: Final validation."""
        state["trace_events"] = [{
            "node": "validate",
            "answer_type": type(state["final_answer"]).__name__
        }]
        return state
    
    # ========================================================================
    # Edge Conditions
    # ========================================================================
    
    def _route_decision(self, state: AgentState) -> Literal["rag", "sql", "hybrid"]:
        """Decide routing based on classification."""
        return state["route"]
    
    def _needs_sql(self, state: AgentState) -> Literal["yes", "no"]:
        """Check if SQL is needed."""
        route = state["route"]
        return "yes" if route in ["sql", "hybrid"] else "no"
    
    def _check_sql_success(self, state: AgentState) -> Literal["success", "retry", "fail"]:
        """Check SQL execution result."""
        result = state.get("sql_result")
        
        if not result:
            return "fail"
        
        if result.success and result.rows:
            return "success"
        
        # Retry if we haven't exceeded max attempts
        if state["repair_count"] < 2:
            return "retry"
        
        return "fail"
    
    def _check_synthesis(self, state: AgentState) -> Literal["valid", "retry", "done"]:
        """Check if synthesis is valid."""
        # For now, accept first synthesis
        # In production, could validate format_hint matching
        return "done"
    
    # ========================================================================
    # Helpers
    # ========================================================================
    
    def _parse_answer(self, answer_str: str, format_hint: str) -> any:
        """Parse answer string into typed output."""
        answer_str = answer_str.strip()
        
        try:
            if format_hint == "int":
                # Extract first number
                import re
                match = re.search(r'\d+', answer_str)
                return int(match.group()) if match else 0
            
            elif format_hint == "float":
                # Extract first float
                import re
                match = re.search(r'\d+\.?\d*', answer_str)
                return round(float(match.group()), 2) if match else 0.0
            
            elif format_hint.startswith("{") or format_hint.startswith("list["):
                # Try to parse as JSON
                # Clean up answer_str
                if "```" in answer_str:
                    # Extract from code block
                    match = re.search(r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```', answer_str, re.DOTALL)
                    if match:
                        answer_str = match.group(1)
                
                try:
                    return json.loads(answer_str)
                except:
                    # Try to extract JSON-like structure
                    import re
                    match = re.search(r'(\{.*?\}|\[.*?\])', answer_str, re.DOTALL)
                    if match:
                        return json.loads(match.group(1))
                    return {}
            
            return answer_str
        
        except Exception as e:
            print(f"Warning: Failed to parse answer: {e}")
            return answer_str
    
    def _calculate_confidence(self, state: AgentState) -> float:
        """Calculate confidence score."""
        # New calibrated confidence formula
        # Start with a modest base and increase/decrease based on signals.
        base = 0.55  # increased baseline for higher calibrated confidence

        # Document retrieval quality (0-0.4)
        chunks = state.get("retrieved_chunks", [])
        doc_score = 0.0
        if chunks:
            avg_score = sum(c.score for c in chunks) / max(1, len(chunks))
            # scale avg_score (~0-1) into 0-0.3 with a small boost
            doc_score = min(0.35, 0.2 + 0.5 * avg_score * 0.35)

        # SQL quality (0-0.35)
        sql_score = 0.0
        if state.get("sql_result"):
            sql_res = state["sql_result"]
            if sql_res.success and sql_res.rows:
                # successful and non-empty -> strong signal
                sql_score = 0.35
            elif sql_res.success and not sql_res.rows:
                # successful but empty -> lower confidence
                sql_score = 0.15
            else:
                # failed SQL -> small penalty (no addition)
                sql_score = 0.0

        # Citation coverage (0-0.12)
        citations = state.get("citations", []) or []
        cit_score = 0.0
        if citations:
            # more citations and mix of doc+tables -> higher
            has_table = any(not ("::" in c) for c in citations)
            cit_score = 0.06 + min(0.06, 0.03 * len(citations))
            if has_table:
                cit_score += 0.02

        # Repair penalty (multiply factor)
        repair_penalty = 1.0
        if state.get("repair_count", 0) > 0:
            repair_penalty = 0.9 ** state.get("repair_count", 0)

        confidence = (base + doc_score + sql_score + cit_score) * repair_penalty
        # Clamp and round
        confidence = max(0.0, min(1.0, confidence))
        return round(confidence, 2)
    
    # ========================================================================
    # Public Interface
    # ========================================================================
    
    def answer_question(self, question: str, format_hint: str, question_id: str = "test") -> dict:
        """Answer a single question and return structured result."""
        initial_state = {
            "question": question,
            "format_hint": format_hint,
            "route": "",
            "retrieved_chunks": [],
            "doc_context": "",
            "constraints": "",
            "sql_query": "",
            "sql_result": None,
            "sql_attempts": 0,
            "final_answer": None,
            "reasoning": "",
            "confidence": 0.0,
            "citations": [],
            "repair_count": 0,
            "errors": [],
            "trace_events": []
        }
        
        # Run the graph
        config = {"configurable": {"thread_id": question_id}}
        result = self.graph.invoke(initial_state, config)
        
        # Format output
        output = {
            "id": question_id,
            "final_answer": result["final_answer"],
            "sql": result.get("sql_query", ""),
            "confidence": result["confidence"],
            "explanation": result.get("reasoning", "")[:200],  # Limit length
            "citations": result["citations"]
        }
        
        return output


if __name__ == "__main__":
    # Quick test
    agent = HybridAgent()
    
    test_q = "According to the product policy, what is the return window (days) for unopened Beverages?"
    result = agent.answer_question(test_q, "int", "test1")
    
    print(json.dumps(result, indent=2))
