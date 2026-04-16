"""
Arcnical CLI commands module.

Provides:
- qualify: Classify repository architecture
- analyze: Perform multi-layer analysis
- eval: Evaluate analyzer performance
- config: Manage configuration
"""
from arcnical.cli.json_exporter import AnalysisExporter
import json
import logging
import os
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from arcnical.orchestrator.orchestrator import Orchestrator
from arcnical.schema import AnalysisDepth, Metadata, TargetClassification
from arcnical.review.llm.provider_factory import LLMProviderFactory
from arcnical.review.llm.base import ProviderError, ProviderConfigError
from arcnical.cli.config import ProviderConfigLoader
from arcnical.orchestrator.l4_integration import L4Integration

logger = logging.getLogger(__name__)
console = Console(legacy_windows=False)


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cli(debug: bool) -> None:
    """Arcnical: AI-powered GitHub repository architecture analyzer.
    
    Performs multi-layer analysis:
    - L1: Qualification (is this an application?)
    - L2: Structural heuristics (architecture patterns)
    - L3: Complexity heuristics (maintainability risks)
    - L4: LLM semantic review (high-level insights)
    
    Example:
        arcnical analyze ./myrepo
        arcnical analyze ./myrepo --depth quick
        arcnical analyze ./myrepo --llm-provider claude --json
    """
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True))
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output analysis as JSON only (no formatting)"
)
@click.option(
    "--depth",
    type=click.Choice(["quick", "standard"], case_sensitive=False),
    default="standard",
    help="Analysis depth: quick (no L4), standard (full)"
)
@click.option(
    "--force",
    is_flag=True,
    help="Force analysis even if qualification fails"
)
@click.option(
    "--llm-provider",
    type=click.Choice(["claude", "openai", "gemini"], case_sensitive=False),
    default="claude",
    envvar="ARCNICAL_LLM_PROVIDER",
    help="LLM provider for L4 analysis (default: claude) [env: ARCNICAL_LLM_PROVIDER]"
)
@click.option(
    "--llm-model",
    type=str,
    default=None,
    envvar="ARCNICAL_LLM_MODEL",
    help="Override default model for provider [env: ARCNICAL_LLM_MODEL]"
)
@click.option(
    "--llm-api-key",
    type=str,
    default=None,
    envvar="ARCNICAL_LLM_API_KEY",
    help="API key for LLM provider [env: ARCNICAL_LLM_API_KEY]"
)
def analyze(
    repo_path: str,
    output_json: bool,
    depth: str,
    force: bool,
    llm_provider: str,
    llm_model: Optional[str],
    llm_api_key: Optional[str],
) -> None:
    """Analyze a repository for architecture quality.
    
    Runs all 4 layers (L1-L4) unless --depth quick is specified.
    
    Examples:
        arcnical analyze ./myrepo
        arcnical analyze ./myrepo --depth quick  # Skip L4 (no LLM calls)
        arcnical analyze ./myrepo --llm-provider claude
        arcnical analyze ./myrepo --llm-provider openai --llm-api-key sk-...
        arcnical analyze ./myrepo --json
        arcnical analyze ./myrepo --force  # Bypass qualification failure
    """
    try:
        # Normalize input
        repo_path = str(Path(repo_path).resolve())
        depth = depth.lower()
        
        if not Path(repo_path).is_dir():
            raise click.ClickException(f"Repository not found: {repo_path}")
        
        console.print(f"📁 Repository: {repo_path}", style="cyan")
        console.print(f"⚙️  Depth: {depth}", style="cyan")
        
        # ============================================================
        # L1-L3: DETERMINISTIC ANALYSIS (no LLM)
        # ============================================================
        
        try:
            orchestrator = Orchestrator(repo_path=repo_path)
            
            # L1: Qualification
            console.print("🔍 L1: Qualifying repository...", style="yellow")
            report = orchestrator.run_l1_qualification()
            
            if report.qualification.classification not in (
                TargetClassification.APPLICATION, TargetClassification.LIBRARY
            ) and not force:
                console.print(
                    "❌ Repository does not qualify for analysis. "
                    "Use --force to override.",
                    style="red"
                )
                raise click.Abort()
            
            if report.qualification.classification not in (
                TargetClassification.APPLICATION, TargetClassification.LIBRARY
            ) and force:
                console.print(
                    "⚠️  Repository did not qualify, but --force specified. "
                    "Continuing...",
                    style="yellow"
                )
            
            # L2: Structure
            console.print("🔍 L2: Analyzing structure...", style="yellow")
            report = orchestrator.run_l2_structure(report)
            
            # L3: Heuristics
            console.print("🔍 L3: Analyzing heuristics...", style="yellow")
            report = orchestrator.run_l3_heuristics(report)

        except Exception as e:
            logger.error(f"Deterministic analysis failed: {e}", exc_info=True)
            raise click.ClickException(f"Analysis failed: {e}")
        
        # ============================================================
        # PHASE 1: JSON EXPORT
        # ============================================================
        
        try:
            exporter = AnalysisExporter()
            json_path = exporter.export(
                report,
                per_file_loc=orchestrator.file_loc,
                file_imports=orchestrator.build_file_imports(),
                repo_path=repo_path,
            )
            console.print(f"[green]✓[/green] Exported to {json_path}", style="green")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Export failed: {e}", style="yellow")
            

        
        # ============================================================
        # SESSION #7: LLM PROVIDER SETUP (L4 only)
        # ============================================================
        
        llm_provider_instance = None
        
        if depth == "standard":
            try:
                # Validate provider is available
                if not LLMProviderFactory.is_available(llm_provider):
                    available_providers = ", ".join(
                        LLMProviderFactory.list_providers()
                    )
                    raise click.BadParameter(
                        f"Provider '{llm_provider}' not available. "
                        f"Available providers: {available_providers}"
                    )
                
                console.print(
                    f"📋 LLM Provider: {llm_provider}",
                    style="cyan"
                )
                
                # Load provider configuration
                config_loader = ProviderConfigLoader()
                provider_config = config_loader.get_provider_config(
                    provider=llm_provider,
                    api_key=llm_api_key,
                    model=llm_model
                )
                
                # Validate provider configuration
                if not config_loader.validate_config(llm_provider, provider_config):
                    raise click.ClickException(
                        f"Invalid configuration for {llm_provider} provider.\n"
                        f"Please provide API key via:\n"
                        f"  1. --llm-api-key flag\n"
                        f"  2. Environment variable\n"
                        f"  3. l4.yaml config file"
                    )
                
                # Create provider instance
                try:
                    console.print(
                        f"🔧 Creating {llm_provider} provider...",
                        style="cyan"
                    )
                    llm_provider_instance = LLMProviderFactory.create(
                        llm_provider,
                        provider_config
                    )
                except (ProviderConfigError, ProviderError) as e:
                    raise click.ClickException(f"Provider error: {e}")
                except Exception as e:
                    raise click.ClickException(
                        f"Failed to create {llm_provider} provider: {e}"
                    )
                
                # Health check provider
                console.print(
                    "🏥 Checking provider health...",
                    style="cyan"
                )
                is_healthy = L4Integration.verify_provider_health(
                    llm_provider_instance
                )
                
                if is_healthy:
                    console.print(
                        f"✅ {llm_provider} provider healthy",
                        style="green"
                    )
                else:
                    console.print(
                        f"⚠️  Warning: {llm_provider} provider may be unavailable",
                        style="yellow"
                    )
            
            except click.ClickException:
                raise
            except Exception as e:
                raise click.ClickException(f"Provider setup failed: {e}")
        else:
            console.print("⏭️  Skipping L4 (--depth quick)", style="cyan")
        
        # ============================================================
        # SESSION #7: L4 REVIEW WITH SELECTED PROVIDER
        # ============================================================
        
        if depth == "standard" and llm_provider_instance:
            try:
                # Create L4 agent with selected provider
                l4_agent = L4Integration.create_l4_agent(llm_provider_instance)
                
                # Run L4 review
                console.print(
                    f"🔬 Running L4 semantic review with {llm_provider}...",
                    style="yellow"
                )
                report = L4Integration.run_l4_review(l4_agent, report)
                
                console.print(
                    "✅ L4 review complete",
                    style="green"
                )
            
            except Exception as e:
                logger.error(f"L4 review failed: {e}", exc_info=True)
                if force:
                    console.print(
                        f"⚠️  L4 review failed but --force specified, continuing",
                        style="yellow"
                    )
                else:
                    raise click.ClickException(f"L4 review failed: {e}")
        
        # ============================================================
        # OUTPUT
        # ============================================================
        
        if output_json:
            console.print(report.model_dump_json(indent=2))
        else:
            # Print summary
            console.print("\n" + "=" * 70, style="cyan")
            console.print("📊 Analysis Summary", style="cyan bold")
            console.print("=" * 70, style="cyan")
            
            # Show scores
            table = Table(title="Health Scores", show_header=True)
            table.add_column("Metric", style="cyan")
            table.add_column("Score", justify="right")
            
            if report.scores:
                table.add_row("Overall", str(report.scores.overall))
                table.add_row("Maintainability", str(report.scores.maintainability))
                table.add_row("Structure", str(report.scores.structure))
                table.add_row("Security", str(report.scores.security))
            
            console.print(table)
            
            # Count findings
            critical = sum(
                1 for f in report.recommendations 
                if f.severity.value == "Critical"
            )
            high = sum(
                1 for f in report.recommendations 
                if f.severity.value == "High"
            )
            medium = sum(
                1 for f in report.recommendations 
                if f.severity.value == "Medium"
            )
            low = sum(
                1 for f in report.recommendations 
                if f.severity.value == "Low"
            )
            
            console.print(f"\n📋 Findings:", style="cyan bold")
            console.print(f"  🔴 Critical: {critical}")
            console.print(f"  🟠 High: {high}")
            console.print(f"  🟡 Medium: {medium}")
            console.print(f"  🟢 Low: {low}")
            
            console.print("\n✅ Analysis complete", style="green")
    
    except click.ClickException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise click.ClickException(f"Analysis failed: {e}")


@cli.command()
@click.argument("repo_path", type=click.Path(exists=True))
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def eval(repo_path: str, output_json: bool) -> None:
    """Evaluate analyzer performance on a repository.
    
    Compares findings against expected defects (if available).
    Useful for measuring recall and precision.
    
    Examples:
        arcnical eval ./myrepo
        arcnical eval ./myrepo --json
    """
    try:
        repo_path = str(Path(repo_path).resolve())
        
        if not Path(repo_path).is_dir():
            raise click.ClickException(f"Repository not found: {repo_path}")
        
        console.print(f"📁 Repository: {repo_path}", style="cyan")
        console.print("🧪 Running evaluation...", style="yellow")
        
        orchestrator = Orchestrator(repo_path=repo_path)
        report = orchestrator.run_full_analysis()
        
        # TODO: Implement evaluation logic
        # For now, just show analysis results
        
        if output_json:
            console.print(report.model_dump_json(indent=2))
        else:
            console.print("✅ Evaluation complete", style="green")
    
    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        raise click.ClickException(f"Evaluation failed: {e}")


@cli.command()
@click.option(
    "--provider",
    type=click.Choice(["claude", "openai", "gemini"], case_sensitive=False),
    default="claude",
    help="Configure specific LLM provider"
)
@click.option("--api-key", type=str, help="Set API key for provider")
@click.option("--model", type=str, help="Set default model for provider")
@click.option("--show", is_flag=True, help="Show current configuration")
def config(provider: str, api_key: Optional[str], model: Optional[str], show: bool) -> None:
    """Manage Arcnical configuration.
    
    Set API keys, models, and provider preferences.
    
    Examples:
        arcnical config --show
        arcnical config --provider claude --api-key sk-...
        arcnical config --provider openai --model gpt-4-turbo
    """
    try:
        config_loader = ProviderConfigLoader()
        
        if show:
            # Display current configuration
            console.print("⚙️  Configuration", style="cyan bold")
            
            for prov in ["claude", "openai", "gemini"]:
                config_dict = config_loader.get_provider_config(prov)
                console.print(f"\n{prov.upper()}:")
                console.print(f"  API Key: {'set' if config_dict.get('api_key') else 'not set'}")
                console.print(f"  Model: {config_dict.get('model', 'default')}")
        
        elif api_key or model:
            # Update configuration
            # TODO: Implement config file updates
            console.print(
                "✅ Configuration updated (file storage not yet implemented)",
                style="green"
            )
        else:
            console.print("Use --show to view config or provide --api-key/--model")
    
    except Exception as e:
        logger.error(f"Config operation failed: {e}", exc_info=True)
        raise click.ClickException(f"Config operation failed: {e}")


@cli.command()
def version() -> None:
    """Show Arcnical version."""
    from arcnical import __version__
    console.print(f"Arcnical {__version__}", style="cyan")


if __name__ == "__main__":
    cli()
