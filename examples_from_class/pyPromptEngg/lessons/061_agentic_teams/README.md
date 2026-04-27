# Lab 061: The Agentic Marketing Agency (Capstone)

## 1. Objective
Welcome to the finale. In this lab, you move from managing a single agent to orchestrating a **Multi-Agent Workforce**. You will act as the **Agency Director**, overseeing a "Centaur" workflow where human strategic intent combined with specialized AI agents produces high-velocity, high-integrity marketing campaigns.

**The Course Thesis:** *Orchestration is the new Management.*

## 2. Directory Structure
This lab simulates a professional agency environment with specialized roles and automated observability.

```text
061_agentic_teams/
├── orchestrator.py        # The Agency Manager (The "Pipeline")
├── database.json          # The "Ground Truth" (Competitor & Product facts)
├── agency_policy.json     # The "Employee Manual" (Unique prompts for 3 agents)
├── logs/                  # Automated Audit Trails (Created on run)
└── README.md              # This file
```

## 3. The Agency Team
You are managing three specialized agents, each using a model optimized for their specific task:

1.  **The Researcher (GPT-4o-mini):** Optimized for fast, low-cost data extraction.
2.  **The Copywriter (GPT-4o):** Optimized for high-quality creative prose.
3.  **The Compliance Governor (GPT-4o):** Optimized for high-reasoning audit and "Trace Integrity."

## 4. Lab Instructions

### Task 1: The Autonomous Failure (10 min)
Run the agency without human intervention to see how "Raw AI" handles competitive pressure.
1.  Run the orchestrator: `python lessons/061_agentic_teams/orchestrator.py`
2.  When prompted for **Stage 2 (Human Steering)**, simply **press Enter** to skip.
3.  **Observe the Logs:** Watch the interaction between the Copywriter and the Compliance Governor.
4.  **The Result:** The agent will likely be **REJECTED**. The Copywriter will "over-promise" or "hallucinate" to win, and the Governor will catch it.

### Task 2: The Centaur Model (10 min)
Now, apply the **Centaur Model** (Human + AI) to steer the agency toward an "Approved" launch.
1.  Run `orchestrator.py` again.
2.  At **Stage 2**, provide a **Strategic Steering Prompt**. 
    *   *Example:* "Focus on our security certification as a strength, but be strictly factual about RivalSoft. Do not make claims that aren't in the research."
3.  **Observe the Difference:** Does your intervention result in an **APPROVED** status?

### Task 3: Observability & Audit (5 min)
1.  Open the `logs/` folder.
2.  Open the latest `.log` file.
3.  **The Reflection:** Notice how the log captures the entire "Reasoning Handoff." This is your **Legal Shield**. In the enterprise, this log proves that your marketing is grounded in data.

### Task 4: Iterative Governance Loop (15 min)
Run the loop-mode orchestrator to practice human-in-the-loop revision under compliance pressure.
1. Run the loop orchestrator: `python lessons/061_agentic_teams/orchestrator_loop.py`
2. At the first **Manager Steering Prompt**, enter a focused strategic instruction (or press Enter to skip).
3. Review **Attempt 1** output:
    *   You will see a draft, then an audit decision (**APPROVED** or **REJECTED**).
4. If rejected, use the **Manager Correction Prompt**:
    *   Enter a correction that addresses flagged claims directly, or press Enter to let the system self-correct.
    *   Enter `exit` at any manager prompt to stop the run.
5. Continue until one of these outcomes occurs:
    *   **Approved:** Draft passes audit within the revision limit.
    *   **Escalation:** Max revisions reached and human intervention is required.

**What to expect**
*   This mode enforces a revision loop (`MAX_REVISIONS = 2`), so you get up to 3 draft attempts total.
*   The audit panel will list failed claims when rejected.
*   Your steering and correction prompts are logged as part of the audit trail.

**Deliverables**
1. A screenshot of a successful run showing the final **GREEN [APPROVED]** decision (or the max-revision escalation state if approval was not reached).
2. The log file name from the `logs/` folder for that run.
3. The exact steering prompt and at least one correction prompt you used.
4. A 3-5 sentence reflection on what changed between attempts and why the final decision was reached.


## 5. Final Reflection
You have moved from asking "What is an agent?" in Session 1 to "How do I govern an agentic workforce?" in Session 5. 

As you finish this lab, review how the **Compliance Governor** and your steering prompts interacted across attempts in loop mode. In practice, this is the core management skill: converting policy intent into measurable revisions until risk is controlled.

This is how AI scales in real teams: **not by one perfect draft, but by governed iteration with clear audit evidence.**

---

### 🏁 Final Course Deliverable
Submit the following for your final checkoff:
1. Terminal screenshot showing either a **GREEN [APPROVED]** outcome or the explicit max-revision escalation message.
2. The exact `.log` file name from `logs/` for that run.
3. The steering prompt and at least one correction prompt you used during the loop.
4. A short reflection (3-5 sentences) describing why the final decision was APPROVED or why escalation was required.
