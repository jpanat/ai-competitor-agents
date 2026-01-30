#!/usr/bin/env python3
"""
Command-line interface for AI Competitor Intelligence
"""

import argparse
import sys
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from main import run_competitor_intelligence, display_results

console = Console()


def main():
    parser = argparse.ArgumentParser(
        description="AI Competitor Intelligence Multi-Agent System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze by description
  python cli.py "AI project management tool for remote teams"
  
  # Analyze by URL
  python cli.py --url https://yourcompany.com
  
  # Save output to file
  python cli.py "SaaS CRM platform" --output report.json
        """
    )
    
    parser.add_argument(
        "input",
        nargs="?",
        help="Business description or company URL"
    )
    
    parser.add_argument(
        "--url",
        action="store_true",
        help="Treat input as URL instead of description"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Save results to JSON file"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimal output (no progress bars)"
    )
    
    args = parser.parse_args()
    
    # Check if input provided
    if not args.input:
        console.print("[red]Error: Please provide business description or URL[/red]")
        parser.print_help()
        sys.exit(1)
    
    # Display header
    if not args.quiet:
        console.print(Panel.fit(
            "[bold cyan]🤖 AI Competitor Intelligence System[/bold cyan]\n"
            "[dim]Multi-Agent Analysis with LangChain & LangGraph[/dim]",
            border_style="cyan"
        ))
        console.print()
    
    # Determine input mode
    input_mode = "url" if args.url else "description"
    
    console.print(f"[bold]Input:[/bold] {args.input}")
    console.print(f"[bold]Mode:[/bold] {input_mode}")
    console.print()
    
    try:
        # Run analysis
        if args.quiet:
            final_state = run_competitor_intelligence(args.input, input_mode)
        else:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Running multi-agent analysis...", total=None)
                final_state = run_competitor_intelligence(args.input, input_mode)
                progress.update(task, completed=True)
        
        # Display results
        display_results(final_state)
        
        # Save to file if requested
        if args.output:
            import json
            with open(args.output, 'w') as f:
                json.dump({
                    "input": final_state["user_input"],
                    "mode": input_mode,
                    "competitors": final_state["competitors"],
                    "analysis": final_state["competitive_analysis"],
                    "comparison": final_state["feature_comparison"],
                    "recommendations": final_state["strategic_recommendations"]
                }, f, indent=2)
            
            console.print(f"\n[green]✓[/green] Results saved to: {args.output}")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Analysis interrupted by user[/yellow]")
        sys.exit(1)
    
    except Exception as e:
        console.print(f"\n[red]✗ Error:[/red] {str(e)}")
        if not args.quiet:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    main()
