import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Callable
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.logging import RichHandler

# 1. Environment and Path Setup
load_dotenv(find_dotenv())
current_dir = Path(__file__).parent
DATA_PATH = current_dir / "database.json"
POLICY_PATH = current_dir / "agency_policy.json"
LOG_DIR = current_dir / "logs"
LOG_DIR.mkdir(exist_ok=True)

console = Console()

class ConfigurationError(Exception): """Raised when required startup files are missing or invalid."""
class OrchestrationError(Exception): """Raised when a stage fails during orchestration."""

def setup_logging() -> tuple[logging.Logger, Path]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"audit_trail_{timestamp}.log"
    logger = logging.getLogger("agency_orchestrator")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()
    logger.addHandler(RichHandler(rich_tracebacks=True, show_path=False))
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(file_handler)
    return logger, log_file

log, log_file = setup_logging()

class AgencyMember:
    REQUIRED_POLICY_KEYS = ("role", "instructions", "output_format")

    def __init__(self, role_name, policy_data, model, client=None):
        self.client = client or OpenAI()
        self.model = model
        self.role_name = role_name
        self.role_config = policy_data.get(role_name)
        if not self.role_config:
            raise ConfigurationError(f"Role '{role_name}' not found.")

        missing_keys = [key for key in self.REQUIRED_POLICY_KEYS if key not in self.role_config]
        if missing_keys:
            raise ConfigurationError(
                f"Role '{role_name}' is missing required policy keys: {', '.join(missing_keys)}"
            )
        
    def think_and_act(self, context_data):
        system_prompt = f"ROLE: {self.role_config['role']}\nINSTRUCTIONS: {self.role_config['instructions']}\nFORMAT: {self.role_config['output_format']}"
        user_prompt = self._build_user_prompt(context_data)
        
        log.info(f"... {self.role_name} is processing using {self.model} ...")
        try:
            response = self.client.chat.completions.create(
                model=self.model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], temperature=0
            )
            content = response.choices[0].message.content
            if not content:
                raise OrchestrationError(f"{self.role_name} returned an empty response.")
            return content
        except Exception as exc:
            raise OrchestrationError(f"{self.role_name} failed: {exc}") from exc

    def _build_user_prompt(self, context_data):
        payload = json.dumps(context_data, ensure_ascii=True, indent=2)
        prompt_template = self.role_config.get("user_prompt_template", "PROJECT_MEMO_PAYLOAD:\n{payload}")

        steering_mode = context_data.get("steering_mode", "manual")
        steering_rules = self.role_config.get("steering_rules", {})
        steering_rule = steering_rules.get(steering_mode, "")

        manual_preflight = self.role_config.get("manual_preflight", "")
        manual_preflight_block = f"{manual_preflight}\n" if steering_mode == "manual" and manual_preflight else ""

        previous_rejections = context_data.get("previous_rejections") or []
        revision_template = self.role_config.get("revision_template", "")
        if previous_rejections and revision_template:
            previous_rejections_lines = "\n".join(f"  - {r}" for r in previous_rejections)
            revision_block = revision_template.format(previous_rejections_lines=previous_rejections_lines) + "\n"
        else:
            revision_block = ""

        try:
            return prompt_template.format(
                payload=payload,
                steering_mode=steering_mode,
                steering_rule=steering_rule,
                manual_preflight_block=manual_preflight_block,
                revision_block=revision_block,
            )
        except KeyError as exc:
            raise ConfigurationError(
                f"Role '{self.role_name}' has invalid user_prompt_template placeholder: {exc}"
            ) from exc

class AgencyOrchestratorBase:
    """Shared base logic for all orchestrator variants."""
    AGENT_SPECS = {
        "researcher": {"model": "gpt-4o-mini", "memo_key": "market_facts"},
        "copywriter": {"model": "gpt-4o", "memo_key": "marketing_draft"},
        "compliance_governor": {"model": "gpt-4o", "memo_key": "audit_report"},
    }

    def __init__(self):
        self.db = self._load_json(DATA_PATH)
        self.policies = self._load_json(POLICY_PATH)
        self.members = {r: AgencyMember(r, self.policies, m["model"]) for r, m in self.AGENT_SPECS.items()}
        self.memo = {"market_facts": "", "human_intent": "", "steering_mode": "skip", "marketing_draft": "", "audit_report": "", "governance_findings": [], "rejected_claims_count": 0}

    def _load_json(self, path):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ConfigurationError(f"Missing required file: {path.name}") from exc
        except json.JSONDecodeError as exc:
            raise ConfigurationError(
                f"Malformed JSON in {path.name} at line {exc.lineno}, column {exc.colno}: {exc.msg}"
            ) from exc
        except OSError as exc:
            raise ConfigurationError(f"Unable to read {path.name}: {exc}") from exc

    @staticmethod
    def _strip_rich_markup(text):
        return re.sub(r"\[/?[^\]]+\]", "", text)

    def _print_and_log(self, message):
        console.print(message)
        if not isinstance(message, str):
            message = str(message)
        log.info(self._strip_rich_markup(message))

    def _panel_and_log(self, content, title, border_style):
        console.print(Panel(content, title=title, border_style=border_style))
        log.info("%s:\n%s", title, content)

    def _run_stage(self, role_name, stage_title, status_message, context_builder):
        role_spec = self.AGENT_SPECS[role_name]
        self._print_and_log(f"\n[bold]{stage_title} (Model: {role_spec['model']})[/bold]")
        with console.status(status_message):
            self.memo[role_spec["memo_key"]] = self.members[role_name].think_and_act(context_builder())

    @staticmethod
    def _parse_governor_json(audit_report):
        start = audit_report.find("{")
        end = audit_report.rfind("}")
        if start == -1 or end == -1 or end < start:
            return None

        try:
            parsed = json.loads(audit_report[start : end + 1])
        except json.JSONDecodeError:
            return None

        if not isinstance(parsed, dict):
            return None
        return parsed

    def _resolve_governance_decision(self):
        report = self.memo["audit_report"]
        parsed = self._parse_governor_json(report)

        if parsed:
            status = str(parsed.get("status", "REJECTED")).upper().strip()
            if status not in {"APPROVED", "REJECTED"}:
                status = "REJECTED"

            failed_claims = parsed.get("failed_claims")
            if not isinstance(failed_claims, list):
                failed_claims = []

            self.memo["governance_findings"] = failed_claims
            self.memo["rejected_claims_count"] = len(failed_claims)

            if self.memo["rejected_claims_count"] > 0:
                status = "REJECTED"
            return status

        self.memo["governance_findings"] = []
        self.memo["rejected_claims_count"] = 0
        return "APPROVED" if "APPROVED" in report.upper() else "REJECTED"