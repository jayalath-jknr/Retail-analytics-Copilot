"""Setup script to verify environment and create database views."""
from agent.tools.sqlite_tool import create_lowercase_views, NorthwindDB
from agent.rag.retrieval import SimpleRetriever
from agent.dspy_signatures import configure_dspy_ollama
from rich.console import Console

console = Console()


def main():
    """Run setup checks."""
    console.print("[bold cyan]Retail Analytics Copilot - Setup[/bold cyan]\n")
    
    # Check 1: Database
    console.print("[yellow]1. Checking database...[/yellow]")
    try:
        db = NorthwindDB()
        if db.test_connection():
            console.print(f"   [green]✓[/green] Database loaded: {len(db.schema_cache)} tables")
        else:
            console.print("   [red]✗[/red] Database connection failed")
            return False
    except Exception as e:
        console.print(f"   [red]✗[/red] Database error: {e}")
        return False
    
    # Check 2: Create views
    console.print("\n[yellow]2. Creating lowercase views...[/yellow]")
    try:
        create_lowercase_views()
        console.print("   [green]✓[/green] Views created")
    except Exception as e:
        console.print(f"   [red]✗[/red] View creation failed: {e}")
    
    # Check 3: Documents
    console.print("\n[yellow]3. Checking document corpus...[/yellow]")
    try:
        retriever = SimpleRetriever()
        console.print(f"   [green]✓[/green] Loaded {len(retriever.chunks)} document chunks")
        
        # Show chunk distribution
        from collections import Counter
        sources = Counter(chunk.source for chunk in retriever.chunks)
        for source, count in sources.items():
            console.print(f"      - {source}: {count} chunks")
    except Exception as e:
        console.print(f"   [red]✗[/red] Document loading failed: {e}")
        return False
    
    # Check 4: DSPy/Ollama
    console.print("\n[yellow]4. Checking DSPy & Ollama...[/yellow]")
    try:
        success = configure_dspy_ollama()
        if success:
            console.print("   [green]✓[/green] DSPy configured with Ollama")
        else:
            console.print("   [yellow]⚠[/yellow] DSPy using fallback (Ollama not available)")
            console.print("   Install Ollama and run: ollama pull phi3.5:3.8b-mini-instruct-q4_K_M")
    except Exception as e:
        console.print(f"   [red]✗[/red] DSPy configuration failed: {e}")
    
    # Summary
    console.print("\n[bold green]Setup complete![/bold green]")
    console.print("\nNext steps:")
    console.print("  1. Ensure Ollama is running: ollama serve")
    console.print("  2. Run evaluation: python run_agent_hybrid.py --batch sample_questions_hybrid_eval.jsonl --out outputs_hybrid.jsonl")
    
    return True


if __name__ == "__main__":
    main()
