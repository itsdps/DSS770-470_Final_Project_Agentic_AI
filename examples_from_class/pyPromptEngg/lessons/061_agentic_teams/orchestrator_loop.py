# root/lessons/061_agentic_teams/orchestrator_loop.py
from agency_core import AgencyOrchestratorBase, console, log, log_file, Panel, OrchestrationError, ConfigurationError

class IterativeOrchestrator(AgencyOrchestratorBase):
    MAX_REVISIONS = 2  # The Loop Limit

    def run_launch_sequence(self):
        log.info(f"AUDIT LOG STARTED: {log_file}")
        banner = "[bold cyan]Multi-Agent Orchestrator v2.0 (LOOP MODE)[/bold cyan]\n[dim]Pattern: Iterative Revision[/dim]"
        console.print(Panel.fit(banner, border_style="cyan"))
        log.info("Multi-Agent Orchestrator v2.0 (LOOP MODE)\nPattern: Iterative Revision")

        # --- STAGE 1: RESEARCH ---
        self._run_stage(
            "researcher",
            "[blue]STAGE 1: Specialist Research[/blue]",
            "[bold blue]Analyzing database...",
            lambda: {"task": "Extract objective, fact-only market insights", "database_snapshot": self.db},
        )
        self._panel_and_log(self.memo["market_facts"], title="Researcher Output", border_style="blue")

        # --- STAGE 2: CENTAUR INTERVENTION ---
        self._print_and_log("\n[bold gold1]STAGE 2: Human Steering (The Centaur Model)[/bold gold1]")
        user_input = console.input("[bold yellow]Manager Steering Prompt (Enter to skip | 'exit' to quit): [/bold yellow]")
        if user_input.strip().lower() == "exit":
            self._print_and_log("\n[bold yellow]Loop exited by manager before draft generation.[/bold yellow]")
            log.info("FINAL DECISION: EXITED")
            log.info(f"AUDIT TRAIL SAVED TO: {log_file}")
            return
        self.memo["steering_mode"] = "manual" if user_input.strip() else "skip"
        self.memo["human_intent"] = user_input.strip() or "No manager steering provided. Follow your role instructions exactly."
        log.info("Manager Steering Prompt: %s", self.memo["human_intent"])

        # --- THE REVISION LOOP (Stages 3 & 4) ---
        for attempt in range(1, self.MAX_REVISIONS + 2):
            # STAGE 3: WRITER — steering_mode is passed so _build_user_prompt applies correct framing
            title = f"[magenta]STAGE 3: Creative Writing (Attempt {attempt})[/magenta]"
            self._run_stage("copywriter", title, "[bold magenta]Drafting campaign...", lambda: {
                "task": "Draft campaign copy.",
                "steering_mode": self.memo["steering_mode"],
                "market_facts": self.memo["market_facts"],
                "human_intent": self.memo["human_intent"],
                # Only inject previous_rejections when there is real feedback to act on.
                # Passing an empty list on attempt 1 changes model behaviour even at temperature=0.
                **({"previous_rejections": self.memo["governance_findings"]} if self.memo["governance_findings"] else {}),
            })
            self._panel_and_log(self.memo["marketing_draft"], title=f"Draft {attempt}", border_style="magenta")

            # STAGE 4: GOVERNOR
            self._run_stage("compliance_governor", "[red]STAGE 4: Compliance Audit[/red]", "[bold red]Auditing for Hallucinations...", lambda: {
                "task": "Audit claims and return verdict with evidence.",
                "market_facts": self.memo["market_facts"],
                "marketing_draft": self.memo["marketing_draft"],
            })

            final_status = self._resolve_governance_decision()
            status_color = "green" if final_status == "APPROVED" else "red"
            self._panel_and_log(self.memo["audit_report"], title=f"Audit Decision {attempt}", border_style=status_color)

            if final_status == "APPROVED":
                self._print_and_log(f"\n✨ [bold green]Final draft approved on Attempt {attempt}.[/bold green]")
                break
            elif attempt <= self.MAX_REVISIONS:
                log.warning("Draft %s rejected. rejected_claims=%s", attempt, self.memo["rejected_claims_count"])
                console.print(f"\n[bold red]Draft {attempt} REJECTED.[/bold red] The following claims were flagged:")
                for claim in self.memo["governance_findings"]:
                    console.print(f"  [red]✗[/red] {claim}")
                    log.info("  FAILED CLAIM: %s", claim)
                console.print()
                correction = console.input(
                    "[bold yellow]Manager Correction Prompt (Enter to let AI self-correct using the feedback above | 'exit' to quit): [/bold yellow]"
                )
                if correction.strip().lower() == "exit":
                    self._print_and_log("\n[bold yellow]Loop exited by manager during revision cycle.[/bold yellow]")
                    log.info("FINAL DECISION: EXITED")
                    log.info(f"AUDIT TRAIL SAVED TO: {log_file}")
                    return
                if correction.strip():
                    self.memo["steering_mode"] = "manual"
                    self.memo["human_intent"] = correction.strip()
                    log.info("Manager correction applied for attempt %s: %s", attempt + 1, self.memo["human_intent"])
                else:
                    log.info("No manager correction for attempt %s. AI self-correcting from governance feedback.", attempt + 1)
            else:
                self._print_and_log("\n🛑 [bold red]Max revisions reached. Human intervention required.[/bold red]")

        log.info(f"FINAL DECISION: {final_status}")
        log.info(f"AUDIT TRAIL SAVED TO: {log_file}")

if __name__ == "__main__":
    try:
        IterativeOrchestrator().run_launch_sequence()
    except ConfigurationError as e:
        console.print(f"[bold red]Startup Blocked:[/bold red] {e}")
        log.exception("Configuration failure")
    except OrchestrationError as e:
        console.print(f"[bold red]Run Failed:[/bold red] {e}")
        log.exception("Stage execution failure")
    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        log.exception("Unexpected failure")