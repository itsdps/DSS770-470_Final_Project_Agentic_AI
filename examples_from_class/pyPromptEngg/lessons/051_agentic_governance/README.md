
# Lab 051: Agentic Governance & Red Teaming

## 1. Objective
Transition from an AI Builder to an **AI Governor**. In this lab, you will audit an agent's reasoning, execute adversarial attacks to find security holes, and implement business guardrails to mitigate risks.

## 2. Directory Structure
This lab leverages the shared environment at the project root.

```text
root/
├── .env                   # Shared API Key (Ensure your key is here)
├── .venv/                 # Shared Virtual Environment
└── lessons/
    └── 051_agentic_governance/
        ├── main.py                # Interactive Agent (for Task B)
        ├── evaluator.py           # Automated Script (for Task A)
        ├── database.json          # The "Ground Truth" company data
        ├── marketbot_policy.txt   # The Agent's Business Rules
        └── audit_report.md        # YOUR DELIVERABLE
```

## 3. Setup
1. **API Key:** Ensure your `OPENAI_API_KEY` is defined in the `.env` file at the **root** of the repository.
2. **Environment:** Ensure your terminal is in the project root and your `.venv` is activated.
3. **Data Inspection:** Open `lessons/051_agentic_governance/database.json` to see the "Ground Truth" and `marketbot_policy.txt` to read the Agent's current instructions.

## 4. Lab Tasks

### Task A: The Auditor’s Deep-Dive (20 min)
Run the automated evaluation script:
```bash
python lessons/051_agentic_governance/evaluator.py
```
**Goal:** Analyze the **Audit Trail** in the terminal. Look for the **"Lucky Hallucination"**—a case where the agent provides a correct final answer but reached it through flawed reasoning.

### Task B: The Red Team Challenge (30 min)
Launch the interactive agent:
```bash
python lessons/051_agentic_governance/main.py
```
**Goal:** Use adversarial techniques (Goal Hijacking, Prompt Injection, Social Engineering) to trick the agent into violating company policy. 

## 5. Deliverable
Complete the `audit_report.md` file. You must document:
1. **One Reasoning Failure** found in Task A.
2. **One Successful Breach** found in Task B.
3. **One Mitigation Policy** (a 1-sentence rule) you added to `marketbot_policy.txt` to fix the breach.
