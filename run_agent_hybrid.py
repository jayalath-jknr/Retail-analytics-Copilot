"""CLI entrypoint for the hybrid retail analytics agent."""
import json
import click
from pathlib import Path
from rich.console import Console
from rich.progress import track

from agent.graph_hybrid import HybridAgent

console = Console()


@click.command()
@click.option(
    '--batch',
    type=click.Path(exists=True),
    required=True,
    help='Path to JSONL file with questions'
)
@click.option(
    '--out',
    type=click.Path(),
    required=True,
    help='Path to output JSONL file'
)
def main(batch: str, out: str):
    """Run the hybrid retail analytics agent on a batch of questions.
    
    Input format (JSONL):
        {"id": "q1", "question": "...", "format_hint": "int"}
    
    Output format (JSONL):
        {"id": "q1", "final_answer": 14, "sql": "...", "confidence": 0.85, 
         "explanation": "...", "citations": [...]}
    """
    console.print("[bold blue]Retail Analytics Copilot - Hybrid Agent[/bold blue]")
    console.print(f"Input: {batch}")
    console.print(f"Output: {out}\n")
    
    # Load questions
    questions = []
    with open(batch, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))
    
    console.print(f"Loaded {len(questions)} questions\n")
    
    # Initialize agent
    console.print("[yellow]Initializing agent...[/yellow]")
    try:
        agent = HybridAgent()
        console.print("[green]✓ Agent initialized[/green]\n")
    except Exception as e:
        console.print(f"[red]✗ Failed to initialize agent: {e}[/red]")
        return
    
    # Process questions
    results = []
    
    for q_data in track(questions, description="Processing questions"):
        question_id = q_data["id"]
        question = q_data["question"]
        format_hint = q_data.get("format_hint", "str")
        
        try:
            result = agent.answer_question(question, format_hint, question_id)
            results.append(result)
            
            console.print(f"\n[cyan]Q ({question_id}):[/cyan] {question[:80]}...")
            console.print(f"[green]Answer:[/green] {result['final_answer']}")
            console.print(f"[yellow]Confidence:[/yellow] {result['confidence']}")
            
        except Exception as e:
            console.print(f"\n[red]Error on {question_id}: {e}[/red]")
            # Create error result
            results.append({
                "id": question_id,
                "final_answer": None,
                "sql": "",
                "confidence": 0.0,
                "explanation": f"Error: {str(e)}",
                "citations": []
            })
    
    # Write results
    console.print(f"\n[yellow]Writing results to {out}...[/yellow]")
    with open(out, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result) + '\n')
    
    console.print(f"[green]✓ Done! Processed {len(results)} questions[/green]")
    
    # Summary statistics
    console.print("\n[bold]Summary:[/bold]")
    avg_confidence = sum(r["confidence"] for r in results) / len(results) if results else 0
    console.print(f"  Average confidence: {avg_confidence:.2f}")
    
    sql_queries = sum(1 for r in results if r.get("sql"))
    console.print(f"  Questions with SQL: {sql_queries}/{len(results)}")


if __name__ == "__main__":
    main()
