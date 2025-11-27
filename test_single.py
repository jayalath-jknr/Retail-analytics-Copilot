"""Quick test script to verify the agent works on a single question."""
import json
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from agent.graph_hybrid import HybridAgent

console = Console()


def test_single_question():
    """Test the agent with a simple question."""
    console.print(Panel.fit(
        "[bold cyan]Retail Analytics Copilot - Quick Test[/bold cyan]",
        border_style="cyan"
    ))
    
    # Initialize agent
    console.print("\n[yellow]Initializing agent...[/yellow]")
    try:
        agent = HybridAgent()
        console.print("[green]✓ Agent ready[/green]")
    except Exception as e:
        console.print(f"[red]✗ Failed: {e}[/red]")
        console.print("\nMake sure:")
        console.print("  1. Ollama is running: ollama serve")
        console.print("  2. Model is downloaded: ollama pull phi3.5:3.8b-mini-instruct-q4_K_M")
        return
    
    # Test question
    question = "According to the product policy, what is the return window (days) for unopened Beverages? Return an integer."
    format_hint = "int"
    
    console.print(f"\n[bold]Question:[/bold] {question}")
    console.print(f"[bold]Expected format:[/bold] {format_hint}\n")
    
    # Run agent
    console.print("[yellow]Processing...[/yellow]")
    try:
        result = agent.answer_question(
            question=question,
            format_hint=format_hint,
            question_id="test_policy"
        )
        
        # Display results
        console.print("\n" + "="*60)
        console.print("[bold green]Result:[/bold green]\n")
        
        console.print(f"[cyan]Final Answer:[/cyan] {result['final_answer']}")
        console.print(f"[cyan]Type:[/cyan] {type(result['final_answer']).__name__}")
        console.print(f"[cyan]Confidence:[/cyan] {result['confidence']}")
        console.print(f"[cyan]Explanation:[/cyan] {result['explanation']}")
        
        console.print(f"\n[cyan]Citations:[/cyan]")
        for citation in result['citations']:
            console.print(f"  - {citation}")
        
        if result.get('sql'):
            console.print(f"\n[cyan]SQL Query:[/cyan]")
            syntax = Syntax(result['sql'], "sql", theme="monokai", line_numbers=False)
            console.print(syntax)
        
        # JSON output
        console.print("\n[bold]Full JSON Output:[/bold]")
        json_output = json.dumps(result, indent=2)
        syntax = Syntax(json_output, "json", theme="monokai", line_numbers=False)
        console.print(syntax)
        
        # Validation
        console.print("\n" + "="*60)
        console.print("[bold]Validation:[/bold]")
        
        if isinstance(result['final_answer'], int):
            console.print("[green]✓[/green] Answer type matches format_hint (int)")
        else:
            console.print(f"[yellow]⚠[/yellow] Answer type is {type(result['final_answer']).__name__}, expected int")
        
        if result['citations']:
            console.print(f"[green]✓[/green] Citations present ({len(result['citations'])} items)")
        else:
            console.print("[yellow]⚠[/yellow] No citations")
        
        if result['confidence'] > 0:
            console.print(f"[green]✓[/green] Confidence score: {result['confidence']}")
        
        console.print("\n[bold green]Test completed successfully![/bold green]")
        
    except Exception as e:
        console.print(f"\n[red]✗ Error during processing: {e}[/red]")
        import traceback
        console.print(f"\n[dim]{traceback.format_exc()}[/dim]")


if __name__ == "__main__":
    test_single_question()
