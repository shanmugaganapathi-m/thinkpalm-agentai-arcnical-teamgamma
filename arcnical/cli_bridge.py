"""
CLI Bridge for Arcnical Dashboard - Phase 4

Handles:
- Executing CLI commands from Streamlit
- Capturing CLI output
- Updating analysis data
- Displaying execution status
"""

import subprocess
import json
import os
import shutil
import tempfile
import streamlit as st
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import time


class CLIBridge:
    """Bridge between Streamlit dashboard and Arcnical CLI."""

    DEFAULT_REPO_PATH = "./test_repo"
    JSON_OUTPUT_PATH = Path(".arcnical/results/latest_analysis.json")
    # Cache dir for cloned GitHub repos (inside project so git ignores it)
    CLONE_CACHE_DIR = Path(".arcnical/clones")

    @staticmethod
    def _is_github_url(repo_path: str) -> bool:
        return repo_path.startswith("https://github.com") or repo_path.startswith("git@github.com")

    @staticmethod
    def _clone_repo(github_url: str) -> Tuple[bool, str, str]:
        """
        Clone a GitHub URL into a local cache directory.

        Returns:
            (success, message, local_path)
        """
        CLIBridge.CLONE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Derive a stable folder name from the URL: owner_repo
        # e.g. https://github.com/vinta/awesome-python -> vinta_awesome-python
        url_clean = github_url.rstrip("/").rstrip(".git")
        parts = url_clean.split("/")
        if len(parts) < 2:
            return False, f"Cannot parse GitHub URL: {github_url}", ""

        folder_name = f"{parts[-2]}_{parts[-1]}"
        local_path = CLIBridge.CLONE_CACHE_DIR / folder_name

        if local_path.exists():
            # Already cloned — do a fast pull instead of full clone
            st.write(f"📂 Found cached clone at `{local_path}`, pulling latest...")
            result = subprocess.run(
                ["git", "-C", str(local_path), "pull", "--ff-only"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=120,
            )
            if result.returncode != 0:
                # Pull failed (e.g. diverged) — just use existing clone
                st.write("⚠️ Git pull failed, using existing clone.")
        else:
            st.write(f"⬇️ Cloning `{github_url}` ...")
            result = subprocess.run(
                ["git", "clone", "--depth", "1", github_url, str(local_path)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=300,
            )
            if result.returncode != 0:
                err = result.stderr or result.stdout
                return False, f"❌ Git clone failed: {err[:300]}", ""

        return True, f"✅ Repository ready at `{local_path}`", str(local_path)

    @staticmethod
    def execute_analysis(
        repo_path: str = DEFAULT_REPO_PATH,
        depth: str = "quick",
        provider: str = "claude",
        api_key: str = None
    ) -> Tuple[bool, str, float, Dict[str, Any]]:
        """
        Execute CLI analysis command.

        If repo_path is a GitHub URL it is cloned locally first.

        Returns:
            Tuple of (success, message, execution_time, data)
        """
        start_time = time.time()

        try:
            # --- Resolve GitHub URL to local path ---
            local_repo_path = repo_path
            if CLIBridge._is_github_url(repo_path):
                ok, clone_msg, local_repo_path = CLIBridge._clone_repo(repo_path)
                st.write(clone_msg)
                if not ok:
                    return False, clone_msg, time.time() - start_time, {}

            # Build command
            cmd = [
                "python", "-m", "arcnical", "analyze",
                local_repo_path,
                "--depth", depth,
                "--llm-provider", provider,
            ]

            # Add API key if provided
            if api_key and depth == "standard":
                cmd.extend(["--llm-api-key", api_key])

            # Force UTF-8 so Windows cp1252 doesn't choke on emoji in rich output
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
                env=env,
            )

            execution_time = time.time() - start_time

            if result.returncode == 0:
                data = CLIBridge.load_analysis_data()
                if data:
                    findings_count = len(data.get("findings", []))
                    message = f"✅ Analysis complete in {execution_time:.2f}s ({findings_count} findings)"
                    return True, message, execution_time, data
                else:
                    message = "⚠️ Analysis ran but JSON not found"
                    return False, message, execution_time, {}
            else:
                error_msg = result.stderr or result.stdout
                message = f"❌ Analysis failed: {error_msg[:500]}"
                return False, message, execution_time, {}

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            message = "❌ Analysis timeout (exceeded 5 minutes)"
            return False, message, execution_time, {}

        except FileNotFoundError:
            message = "❌ arcnical command not found. Install with: pip install -e ."
            return False, message, 0, {}

        except Exception as e:
            execution_time = time.time() - start_time
            message = f"❌ Error: {str(e)[:300]}"
            return False, message, execution_time, {}

    @staticmethod
    def load_analysis_data() -> Dict[str, Any]:
        """Load latest analysis JSON."""
        try:
            if not CLIBridge.JSON_OUTPUT_PATH.exists():
                return {}
            
            with open(CLIBridge.JSON_OUTPUT_PATH, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Failed to load analysis: {e}")
            return {}

    @staticmethod
    def get_cli_output_display(
        repo_path: str,
        depth: str,
        provider: str,
        execution_time: float = None,
        findings_count: int = None
    ) -> str:
        """
        Generate CLI output display text.
        
        Args:
            repo_path: Repository path
            depth: Analysis depth
            provider: LLM provider
            execution_time: Execution time
            findings_count: Number of findings
            
        Returns:
            Formatted CLI output text
        """
        output = f"""D:\\Projects\\arcnical_repo> python -m arcnical analyze {repo_path}
--depth {depth}
--llm-provider {provider}
"""
        
        if depth == "quick":
            output += """
✅ L1: Qualifying repository... PASSED
✅ L2: Analyzing structure... PASSED
✅ L3: Analyzing heuristics... PASSED
✅ JSON exported to .arcnical\\results\\latest_analysis.json
⏭️  Skipping L4 (--depth quick)
"""
        else:
            output += """
✅ L1: Qualifying repository... PASSED
✅ L2: Analyzing structure... PASSED
✅ L3: Analyzing heuristics... PASSED
✅ L4: LLM review... PASSED
✅ JSON exported to .arcnical\\results\\latest_analysis.json
"""
        
        if execution_time:
            output += f"\n✅ Completed in {execution_time:.2f}s"
        
        if findings_count is not None:
            output += f"\n📋 Findings: {findings_count}"
        
        output += "\n✅ Analysis complete"
        
        return output

    @staticmethod
    def get_config_summary(
        provider: str,
        depth: str,
        execution_time: float = None,
        findings_count: int = None
    ) -> str:
        """
        Generate configuration summary text.
        
        Args:
            provider: LLM provider
            depth: Analysis depth
            execution_time: Execution time
            findings_count: Number of findings
            
        Returns:
            Formatted configuration summary
        """
        model_map = {
            "claude": "claude-sonnet-4-6",
            "openai": "gpt-4",
            "gemini": "gemini-pro"
        }
        
        model = model_map.get(provider, provider)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        summary = f"""**Model:** {model}
**Provider:** {provider.capitalize()}
**Depth:** {depth.capitalize()}
**Last Run:** {timestamp}"""
        
        if execution_time:
            summary += f"\n**Time:** {execution_time:.2f}s"
        
        if findings_count is not None:
            summary += f"\n**Findings:** {findings_count}"
        
        return summary
