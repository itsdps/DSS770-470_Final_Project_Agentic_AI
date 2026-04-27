# Why Audit Reasoning? (The Audit Logic)

In traditional Business Intelligence (BI), we trust the **Output**. If a SQL query returns a margin of 12.5%, and the math checks out, the system is working. 

In **Agentic AI**, we must trust the **Trace**, not the output. This document explains the research-backed reasons why "Right Answers" can be dangerous.

---

### 1. The "Lucky Hallucination" Problem
A "Lucky Hallucination" occurs when an agent provides the correct final answer but reaches it through flawed, hallucinated, or non-existent logic.

*   **The Risk:** A system that is "correct by accident" today is guaranteed to be "catastrophically wrong" tomorrow.
*   **The Research:** Studies on the **"RAG Triad"** (Groundedness, Context, and Relevance) show that LLMs are often "improperly grounded." They use their training data to "guess" a plausible answer rather than calculating it from the retrieved data.

### 2. Why it Happens: Contextual Attractors
LLMs are probabilistic, not deterministic. They are trained to predict the most "plausible" next token in a sentence.

*   **Narrative over Math:** If an LLM retrieves messy data (like the string `"875k"` in our lab), its "prior" training steers it toward rounding or simplifying the number to make the "narrative" of the answer sound more professional.
*   **The "12.5%" Trap:** Because 12.5% is a very common, "plausible-sounding" financial figure, an agent may steer its math toward that result even if the intermediate steps (Revenue - Expenses) are based on hallucinations.

### 3. Data Formatting as a Vulnerability
In a reliable database, data types (Integer, Float, Boolean) are enforced. In an Agentic system, **everything is a string.**

*   **The Interpretation Gap:** When a reasoning engine encounters unstructured or "noisy" data, it doesn't throw a "Type Error" like a computer program. Instead, it **interprets** the data.
*   **Research Grounding:** Research into *Prompt Formatting and Accuracy* (arXiv, 2024) shows that presenting data as "noisy strings" instead of "clean integers" can degrade reasoning accuracy by up to 40%, even if the retrieved facts are correct.

---

### 4. The BI Mindset vs. The AI Governor Mindset

| Feature | BI Analyst View | AI Governor View |
| :--- | :--- | :--- |
| **Primary Metric** | Output Accuracy | **Trace Integrity** |
| **Data Trust** | Trust the Database | **Trust the Observation** |
| **Failure Mode** | The Query Crashes | **The Agent "Fakes it"** |
| **Success Criteria** | The Number is Correct | **The Logic is Auditable** |

---

###  Executive Summary for the Lab
In **Task A**, you will encounter a correct answer. **Do not stop there.** 

Open the **Audit Trail (the logs)**. Check if the agent's internal calculation matches the "Ground Truth" in `database.json`. If the agent "rounded" expenses or "guessed" a number to make the math work, you have found a **High-Risk Reasoning Failure.**

> *"A correct answer built on a lie is a liability, not an asset."*
