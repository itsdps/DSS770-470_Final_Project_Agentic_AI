import json
from agency_core import (
    AgencyOrchestratorBase, 
    console, 
    log, 
    log_file, 
    Panel, 
    ConfigurationError, 
    OrchestrationError
)

class SequentialOrchestrator(AgencyOrchestratorBase):
    """
    Implements the 'Linear Handoff' pattern.
    Researcher -> Human Steering -> Copywriter -> Compliance Governor.
    """

    def run_launch_sequence(self):
        log.info(f"AUDIT LOG STARTED: {log_file}")
        
        banner = "[bold cyan]Multi-Agent Orchestrator v2.0 (SEQUENTIAL MODE)[/bold cyan]\n[dim]Pattern: Linear Handoff[/dim]"
        console.print(Panel.fit(banner, border_style="cyan"))
        log.info("Multi-Agent Orchestrator v2.0 (SEQUENTIAL MODE)\nPattern: Linear Handoff")

        # --- STAGE 1: RESEARCH ---
        # The researcher extracts the ground truth from database.json
        self._run_stage(
            role_name="researcher",
            stage_title="[blue]STAGE 1: Specialist Research[/blue]",
            status_message="[bold blue]Analyzing database...",
            context_builder=lambda: {
                "task": "Extract objective, fact-only market insights",
                "database_snapshot": self.db,
            },
        )
        self._panel_and_log(self.memo["market_facts"], title="Researcher Output", border_style="blue")

        # --- STAGE 2: CENTAUR INTERVENTION ---
        # The Human Manager provides the 'Intent' that overrides AI default behavior
        self._print_and_log("\n[bold gold1]STAGE 2: Human Steering (The Centaur Model)[/bold gold1]")
        user_input = console.input("[bold yellow]Manager Steering Prompt (Enter to skip | 'exit' to quit): [/bold yellow]")
        if user_input.strip().lower() == "exit":
            self._print_and_log("\n[bold yellow]Sequence exited by manager before draft generation.[/bold yellow]")
            log.info("FINAL DECISION: EXITED")
            log.info(f"AUDIT TRAIL SAVED TO: {log_file}")
            return
        
        self.memo["steering_mode"] = "manual" if user_input.strip() else "skip"
        self.memo["human_intent"] = user_input.strip() or "No manager steering provided. Follow your role instructions exactly."
        log.info("Manager Steering Prompt: %s", self.memo["human_intent"])

        # --- STAGE 3: CREATION ---
        # The Copywriter drafts based on Facts + Human Intent
        self._run_stage(
            role_name="copywriter",
            stage_title="[magenta]STAGE 3: Creative Writing[/magenta]",
            status_message="[bold magenta]Drafting campaign...",
            context_builder=lambda: {
                "task": "Draft campaign copy.",
                "steering_mode": self.memo["steering_mode"],
                "market_facts": self.memo["market_facts"],
                "human_intent": self.memo["human_intent"],
            },
        )
        self._panel_and_log(self.memo["marketing_draft"], title="Copywriter Draft", border_style="magenta")

        # --- STAGE 4: GOVERNANCE ---
        # The Compliance Governor audits the Copywriter against the Researcher's Facts
        self._run_stage(
            role_name="compliance_governor",
            stage_title="[red]STAGE 4: Compliance Audit[/red]",
            status_message="[bold red]Auditing for Hallucinations...",
            context_builder=lambda: {
                "task": "Audit claims and return verdict with evidence.",
                "market_facts": self.memo["market_facts"],
                "marketing_draft": self.memo["marketing_draft"],
            },
        )

        # Resolve Decision (Helper method from Base class)
        final_status = self._resolve_governance_decision()
        status_color = "green" if final_status == "APPROVED" else "red"
        self._panel_and_log(self.memo["audit_report"], title="Compliance Decision", border_style=status_color)

        if final_status == "APPROVED":
            self._print_and_log("\n✨ [bold green]SEQUENCE COMPLETE: Campaign is ready for deployment.[/bold green]")
        else:
            self._print_and_log("\n🛑 [bold red]SEQUENCE HALTED: Compliance issues detected. Review the Audit Report.[/bold red]")

        log.info(f"FINAL DECISION: {final_status}")
        log.info(f"AUDIT TRAIL SAVED TO: {log_file}")

if __name__ == "__main__":
    try:
        orchestrator = SequentialOrchestrator()
        orchestrator.run_launch_sequence()
    except ConfigurationError as e:
        console.print(f"[bold red]Startup Blocked:[/bold red] {e}")
    except OrchestrationError as e:
        console.print(f"[bold red]Run Failed:[/bold red] {e}")
    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}")