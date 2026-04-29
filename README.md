# **The "README" File:** the writing part of our final delivariable

This David Scott and Senthil Vel's Final Project for SJU's Agentic AI & Prompt Engineering Course (*Spring 2026*) with Professor Eddie Amadie.

### **Comment about AI Use:**
Throughout this course and in this final project, we were permitted and encouraged to use AI to help us code (*Agentic AI & Prompt Engineering*). Therefore, we just wanted to make it abundantly clear that this AI Prototype Project was coded with the help of AI. It was a long and iteractive process, and we incorporated ideas and code directly from our course whenever possible. The AI was also asked to help us organizate and document parts of our project, especially on the main Juypter Notebook (`AI_Agent.ipynb`). However, this README file is entirely and completely written by David Scott and Senthil Vel. AI was **not** used to write this README file.

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

**Objective**: To develop an interactive agent that will create and schedule social media post(s) for a specific organization’s product or event while also keeping a consistent style and focus over an extended period of time. A user should also be able to come back in the future and request the Agent create additional posts for that organization’s product or event. Those future posts should have a consistent focus and similar style to have an effective marketing campaign or presence.

**The Problem:**
Most of social media posting is frequent, but relatively mundane small to moderate importance posting. However, these posts are very important to keeping customers or supporters engaged and informed. Unfortunuately, the time it takes to do these posts can really add up, which is compounded if you are doing this for multiple clients and/or for multiple platforms. Additionally, as one of the creator of this project is (*David*), you could be volunteering as marketing manager for an organization you are apart of but instead being able to spend your limited time creating cool or interesting posts, you have to spend most of your time creating these "regular" frequent posts. Therefore, we will developed this AI Agent Prototype to solve this issue by helping to create actual posts, or at least inspirations, that improve a company social media presence and also free up the user to spend more time working on the more complex and/or important, less-frequent posts.

**General Workflow:**
User Input -> Create Receipt -> Research Company/Product -> Create Company/Product Report -> Confirm Receipt -> Add References -> Create Style Guide -> Add Imagines to Use -> Create Posts -> A/B Testings -> Auditor Evaluation Loop -> Schedule Post on Google Calendar -> Save Posts & Logs

**Agentic Patterns:**
Our project uses a few different Agentic Patterns to achieve its goals. The first, and most obvious, is Sequential Workflow, which is what the overall workflow of this process is. There is a clear step-by-step process where the output of one task is the input in the next (*see the General Workflow above*). Another pattern is Human-in-the-Loop, which is present throughout, such as when it asks the user to confirm the “receipt” or when it uses fuzzy search and ask is “Rita’s” the same as “Rita’s Italian Ice"? The next pattern is ReAct (Reason + Act) and is used explicitly by the Research Agent as it reasons whether it should search the web, fetch a specific URL, read a document, or ask a clarifying question. It then acts and continues the loop. Then, there is a Parallelization Agentic Pattern, which occurs when posts for two different social media are being created and both create captions have them scored at the same time. `InstagramAgent` and `TwitterAgent` will work in parallel or at the same time creating captions for their posts. Finally, there is an Evaluator Pattern (some call it Evaluator-Optimizer Pattern), which is similar to the Orchestrator Pattern from our class, and it is at the end where an auditor evaluates an image, sends correction prompts, evaluates it again, sends another correction prompt, and repeats until the post passes the auditor, or evaluator, or it reaches max iterations and the auditor fails the post.

**Models:**
The main model used in this AI Agent Prototype was gpt-4o, a very capable model that we knew could handle the tasks we were planning to do. We also felt it properly balanced speed, quality, and token use, the three big considerations when choosing a model. Two other ChatGPT models were also used because of the specific tasks they could preform. DALL-E 3 was used to create the images and gpt-4o Vision to analyze the screenshots to use and audit the generated images by DALL-E 3. The Scorer uses a different model so it judge the main model’s outputs, and it uses the gpt-3.5-turbo because its faster and its tasks are much simpler.

**Not Simple ChatGPT Prompt:**
Hopefully that gave some insight on why this useful and much more than a simple ChatGPT prompt. However, we also just wanted to outline a few key points of how this goes beyond a basic ChatGPT prompt:
   1. 

## **The Prompt Iteration Log**

Our Prompt Engineering Journey had many twists and turns and we wanted to highlight the three primary area where we encountered some limitation/failures with our initial prompts but used different techniques to optimize our prompts. The four key areas where this was most notable (*and that we recorded our progress*) was implimenting the Image Auditor, Researching the Company/Product Report, A/B Scorer, and Fuzzy Searching. We will go into more detail with the first two will the last two we will more just discuss about.
1. Consistent Posts Focus & Style (Company Report, Product Report, Style Guide)
2. A/B Testing - Quality Checks & Guardrails
3. Research Structure -> Web Search + URL Links + Files (can do very new or unreleased products/events)
4. Schedule to Google Calendar

**Prompt Engineer #1 - Image Auditor:**


**Prompt Engineer #2 - Research Agent**


**Prompt Engineer #3 & #4 - A/B Score & Fuzzy Searching:**


## **Functional Code (The Logic)**

Explore our Agent's Juypter Notebook (`AI_Agent.ipynb`) which helps to tell the "story" of our Agent. There also is a live demo using Rich's UI at the bottom of this notebook or you can just run `demo.py`. Comments on this notebook were made with the help of AI, but do give a good reflection of our joruney developing this AI Agent Prototype.

Here is also a link to walkthrough of this project: {insert link} - if there is no link here, we unfortunately didn't get a chance to record this



## **Evaluation & Ethics**

**Testing and Evluating the Agent:**
The Agent was evaluated by a number of different crtieria. The first and most obvious was the A/B Score and Caption and Image Auditor were used to judge the quality of the Agent's output. In particular, the auditors would fail the Agent's output if it did not pass a minimum crtieria. Therefore, the Auditor's pass or fail was one of the key idicators for the Agent's success. The Scorer would just take the highest rated posts and if the Agent's output achieved 9.0/10 it would be considered excellent caption while anything between 7.5 to 8.5 is considered good. However, earlier in the process, one way the Agent was evaluated was how many "null" fields it hand in the Company Report and the Product Report. More than one normally showcased a problem and early on in this processes company and/or product would have mostly none and would be determintal to the later half when it came time to create the posts. Therefore, whether the Auditors passed or failed posts, what the score of those posts were, and the number of null values in the company or product reports were some of the main ways we tested and evaluated our Agent.

The Agent was also evaluated on how flexible or adaptable it was, or in other words, how was it able to adapt to the unique reuests or human errors of individuals. We tested out what if a company did not have an online presence, it got no information, so we added an option to add a file on a company, and now it was flexible. What if someone wanted 1 Post on Instagram and 2 Posts on Twitter? What if they spelled Rita's Italian Ice as "Rita's", would the agent create a duplicate company? What if the user added an additional guiding question to their request, can it adapt to do that request or is it too rigid? If someone added a new reference and only slightly wanted to update their style guide, would the model be able to understand what they say if it not word for word what an option is (*sentiment analysis*) and is that even an option? 

Finally, we also used humans, ours self as well as others (e.g., family members), to evaluated the output posts of the Agents. Were they good, bad, weird, offensive, etc.? Then, in addition, we also tested our Agent and showcased it to others, eveluating how the UI looks and how easy it is to navigate. The Steps were added to the Demo UI and set to match the Juypter Notebook so that new users can follow along easier.


**Guardrails & Ethics:**

In this project, we have a number of guardrials to help ensure the code works as intended, the output is of a certain quality, and the output does not violate our ethical standards. For the first of these, we build in restrictions to what platforms to accept, since we only can work with Instagram, Twitter/X, and Blogs right now, restriction to what type of files can be uploaded, `.png`, `jpg`, or `jpeg`, which will help prevent errors or not get any information when analyzing the photos, and resitrictions to whether the user can modify the number of posts after they request if the agent is creating post for multiple platforms, beause this actually broke the code since it no longer new how many posts needed to be made for each platform. In each of these cases, we added explaination and guidance to help the user navigate them. 

Next, A/B Scorers and Auditors (Caption and Image) are used as guardrails to help ensure a certain quality and certain criteria are met. The A/B Scorer uses another model, gpt-3.5-turbo, since it is fast and the task is not very complex, and the scorer scores the posts on its quality of the posts, using criteria like originality and brand voice. If it scores 9 or more it passes, if not it keeps going a total of three times and then the highest score is taken. The next guardrail is the Image Auditor, which helps to ensure a certain quality of image, such as no misspellings, no cut off words, and no wrong logos. The Image Auditor fails the posts that do violate these crtieria and sends a correction prompt back to the imagine creator (DALL-E 3) and the cycle repeats until  the post meets the criteria and pass or it reaches the maximum cycles and the post is rejected. Finally, the Caption Auditor doesn't evaluate quality, that is the A/B Scorer, it instead checks that there are no blatantly lies or hateful/harmful comments in the captions. However, it is only checking against the context it has been provided by the Research Agent, so it more like a last double check rather than a 100% fact checker.

For future expansion of this project, especailly if this expands in the cloud and accross a company, permissions will  need to be put into place to restrict who can see and modify what folders. You don't want just anyone modifiying what your company report, product reports, or style guides are without your permission because that would ruin the whole "consistent" focus and style that this AI Agent is meant to produce. Additionally, if someone is using this AI Agent to create posts for an upcoming product that isn't announced that suppose to be secret, this does send this information to OpenAI. However, its likely fine, but even then you will likely want to set permission so that not everyone can access that company folder in the `AI Storage`.