# **The "README" File:** the writing part of our final delivariable

This David Scott and Senthil Vel's Final Project for SJU's Agentic AI & Prompt Engineering Course (*Spring 2026*) with Professor Eddie Amadie 

### **Comment about AI Use:**
Throughout this course and in this final project, we were permitted and encouraged to use AI to help us code (*Agentic AI & Prompt Engineering*). Therefore, we just wanted to make it abundantly clear that this AI Prototype Project was coded with help of AI, as well as AI helped us organizate and document parts of our project, especially on the main Juypter Notebook (`AI_Agent.ipynb`). However, this README file is entirely and completely written by David Scott and Senthil Vel. AI was **not** used to write this README file.

The `Help Documents` folder contains information that we worked with the AI to generated to assisst in understanding how to setup and run this project in detail.

### **This README will cover the 4 Core Minimum Deliverables:**
1. **Objective & Design Brief:**
   - A clear statement of the problem your AI agent solves.
   - A description of the Agentic Pattern used (e.g., Tool Use, RAG, Sequential Workflow, or Manager-Worker pattern).

2. **The Prompt Iteration Log:**
   - Documentation of your "Prompt Engineering" journey. Show the initial prompt, the failure/limitation encountered, and the final optimized version (using techniques like Chain-of-Thought or Structured Output).

3. **Functional Code (The Logic):**
   - A Jupyter Notebook or Python script that demonstrates the agent in action.
   - The code must demonstrate interaction (e.g., the agent calling a function, querying a document, or processing a multi-step task).
  
4. **Evaluation & Ethics:**
   - A brief summary of how you tested the agent and a "Safety Note" on potential biases or risks associated with your specific use case.


## **Objective & Design Brief**

**Object**: Develop an agent that will create and schedule social media post(s) for a specific organization’s product or event while allowing maintaining a consistent style. 

TAfter a user creates a post for a product the first time, they should be able to come back in the future and request the Agent create additional posts for that same product. Those future posts should have a consistent focus and similar style based on a marketing guide (product/event guide and brand style guide) that the agent will create or had already created.

