# **The "README" File:** the written part of our final deliverable

This is David Scott and Senthil Vel's Final Project for Saint Joseph's University's Agentic AI & Prompt Engineering Course (*Spring 2026*) with Professor Eddie Amadie.

### **Comment about AI Use:**
Throughout this course and in this final project, we were permitted and encouraged to use AI to help us code (*Agentic AI & Prompt Engineering*). Therefore, we just wanted to make it abundantly clear that this AI Agent Prototype Project was coded with the help of AI.  It was a long and iterative process, and we incorporated ideas and code directly from our course whenever possible. The AI was also asked to help us organize and document parts of our project, especially on the main Juypter Notebook (`AI_Agent.ipynb`) (e.g., "Here is the "Problem", "Objective", and "Agentic Workflow" from my README, please document this Juypter Notebook like a Story using this information"). However, this README file is entirely and completely written by David Scott and Senthil Vel. AI was **not** used to write this README file. Additionally, the actual idea, design, and architecture of this project was developed entirely by David Scott and Senthil Vel, based on SJU's Agentic AI & Prompt Engineering course.

The `Help Documents` folder contains information that we worked with the AI to generate to assist in understanding how to set up and run this project in detail.

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

---
# **AI AGENT HONEYCOMB**
### You set it up once, come back again in the future, and harvest the ready-to-post content!
---

## **Objective & Design Brief**

**The Problem:**
Consistent, regular social media posts are vital for informing and engaging with a company’s customers and supporters. Unfortunately, the time it takes to plan, create, schedule, and post each one of these regular posts can often take much longer than someone might expect. This is especially the case for someone trying to maintain a consistent style and focus for a marketing campaign, which a simple ChatGPT prompt cannot do. The time taken for this regular post is also compounded for a marketing professional at a marketing agency who must balance posts for **multiple** clients (*companies*) with **multiple** products on **multiple** platforms. This takes away time from when these professionals could be utilizing their expertise and creativity to develop marketing strategies, analyze the results of a digital marketing campaign, or create more complex posts (e.g., videos). Additionally, as one of the creator of this project is (David), you could be volunteering as social media manager for an organization or club you are a part of and instead of being able to spend your limited time creating cool or interesting posts, you have to spend most of your time creating these "regular" frequent posts, that you even sometimes forget to post. Therefore, we developed this AI Agent Prototype to solve this issue by helping to create and schedule actual posts (*or at least strong inspirations*) that improve a company social media presence and free up the user to do the tasks that they enjoy more and require more of their expertise and creativity. 

**Objective**: To develop an interactive agent that will create and schedule social media post(s) for a specific organization’s product or event while also keeping a consistent style and focus over an extended period of time. A user should then be able to come back in the future and request the Agent create additional posts for that organization’s product or event. Those future posts should have a consistent focus and similar style to the first, while also allowing the User to update the existing style of the posts with new reference posts as well as images to use in the actual posts.

**Agent Workflow:**
![Agentic Solution Visual](Images/Agentic%20Solution%20Visual2.png)

**Agentic Patterns:**
Our project uses a few different Agentic Patterns to achieve its goals. The first, and most obvious, is Sequential Workflow, which is what the overall workflow of this process is. There is a clear step-by-step process where the output of one task is the input in the next (*see the Agent Workflow above*). Another pattern is Human-in-the-Loop, which is present throughout, such as when it asks the user to confirm the “receipt” or when it uses fuzzy search and asks, “Is Rita’s the same as ‘Rita’s Italian Ice’?” The next pattern is ReAct Loop (Reason + Act) with Tool Use. In this pattern, the Agent reasons what tool it should use to research the given company or product, such as search the web, fetch a specific URL, read a document, or ask a clarifying question. It then acts and continues the loop. Then, there is a Parallelization Agentic Pattern, which occurs when posts for two different social media platforms are being created at the same time. For example, `InstagramAgent` and `TwitterAgent` will work in parallel, or at the same time, creating captions for their respective posts. Finally, there is the Evaluator-Optimizer Pattern, which is similar to the Orchestrator Pattern from our class, and it is near the end where the image auditor evaluates an image and sends a correction prompt back if it fails the audit. The image generator then makes a new image with this correction prompt, and the image auditor evaluates it again. This loop continues until the image passes the image auditor or it reaches max iterations and the auditor fails the post.

**Models:**
The main model used in this AI Agent Prototype was gpt-4o, a very capable model that we knew could handle the tasks we were planning to do. We also felt it properly balanced speed, quality, and token use, the three big considerations when choosing a model. Several other OpenAI models were also used because of the specific tasks they were tasked with performing. Initially, we used DALL-E 3 to create the images but later decided to switch to the newer gpt-image-2. Despite being slightly more expensive per photo generated, gpt-image-2 would actually likely save us money by needing to generate fewer images to be audited and they would be higher quality, which we found to be extremely important. Then, for analyzing the screenshots and auditing the images, we decided to upgrade from gpt-4o to gpt-4.1, because, for "vision" tasks, it is reportedly better at performing them and cheaper per token, while also being about the same speed, or faster, than gpt-4o.

The A/B Scorer and the Research ReAct Loop use gpt-4o-mini because it is faster and cheaper than gpt-4o and these tasks are much simpler. Initially, for A/B Scorer (rates captions on a scale from 0-10) we used gpt-3.5-turbo and while through prompt engineering we did have it get close to the results we wanted, there were too many technical limitations to this old model. Therefore, we ultimately decided it would be worth it to upgrade to a slightly stronger model, gpt-4o-mini, so its scoring would be more accurate. The Research ReAct Loop, using the call tools and gathering information, also uses gpt-4o-mini. However, once the observations are collected and the report (company or product) is ready to be made, the model switches back to gpt-4o, because we felt a stronger model for this more complex task would be more appropriate here.

**Not Simple ChatGPT Prompt:**
Hopefully that gave some insight on why this is useful and much more than a simple ChatGPT prompt. However, we also just wanted to outline a few key points of how this goes beyond a basic ChatGPT prompt:
1.	Brand Memory - Same Company Report, Product Report, and Style Guide used for Consistent Current and Future Post Creation
2.	A/B Testing / Auditor - Quality Checks & Guardrails
3.	Research Structure -> Web Search + URL Links + Files + Ask (can store very new or unreleased products/events information)
4.	Schedule to Google Calendar

---
## **The Prompt Iteration Log**

Our Prompt Engineering Journey had many twists and turns, and we wanted to highlight the two primary areas where we encountered some limitations/failures with our initial prompts but used different prompt engineering techniques to optimize our prompts. The two key areas where this was most notable were the Image Auditor and the Research ReAct Loop + Tool Use.

### **Prompt Engineer #1 - Image Auditor:**
For this AI Agent Prototype, the agent generates captions and images to be used for social media posts. While the A/B Scorer and the Caption Auditor can pretty easily evaluate text (e.g., the captions) for quality and ethical guidelines, images are much harder to do this for. However, we believe this is very important to do since the goal is for this image to be shared with the public, so no image is better than a bad image. Therefore, we implemented an Evaluator-Optimizer Agentic Pattern using gpt-4o (*later gpt-4.1*), where this “Image Auditor” would evaluate each image for whether it passed certain criteria, such as “no text clipping”, “no misspellings”, and “no incorrect logos”.


**(1).** The first stage of this implementation was without the image auditor, and, as mentioned in the model section, DALL-E 3 was used to create images. This initial iteration had no quality control and while the initial generated images themselves seemed decent, they had major issues that made them unusable, such as incorrect logos, factual lies, misspelled words, or cut off text, the latter of which was the most common.

**(2).** Therefore, for the second iteration, we implemented the image auditor using gpt-4o, but it did not detect any of the issues with the images. Our initial prompt was too vague and was basically “Is this image good for social media posting?” so the image auditor passed basically every image, regardless of if it had text that was significantly cutoff, misspelling, or wrong logos.

**(3).** The third iteration of our prompt sought to address this by implementing stricter criteria but ended up overcorrecting and failing to pass almost every image. Our prompt added examples of what to fail the images for and used terms like “ZERO TOLERANCE” and “NO exceptions”. This resulted in the auditor finally flagging the incorrect images, but unfortunately it was flagging basically every single image, and none were being passed. Therefore, after the max audit attempts, if it still failed, we added it so the user would get the option to use the image but just marked as “Failed Audit” so they wouldn’t accidentally use it but could still use it as reference.

**(4).** Therefore, for the fourth iteration of our prompt, we added a correction prompt from the auditor to try to have the image generator address these issues. However, while the image generator sometimes corrected for these issues, the vast majority of the time it just ignored them and even after multiple audits nothing was passed. We identified in this case that the long correction prompt was being cut off, with the first sentence, identifying the issue, being given, but the directions to change, the second sentence, was often cut off or the response was just too long.

**(5).** For the fifth iteration of our prompt, we changed our approach to the correction prompts. The prompts were changed to be more direct and concise while also focusing purely on what to change. Additionally, we implemented an escalating correction prompt approach. After the first failure, a direct, concise, and actionable correction prompt was given, “TEXT CUTOFF – KEEP ALL TEXT FAR FROM EVERY EDGE”. After the second failure, a more urgent and emotional correction prompt was given, “DON’T LET TEXT BE CUT OFF OR I WILL BE FIRED”. Finally, after the third failure, the “nuclear” option would be employed to hopefully get a decent image still, and included correction prompts like “NO TEXT IN THE IMAGE AT ALL. ZERO WORDS. ZERO LETTERS.” In the end, while this did see some images now pass the audit, most still had to go to the “nuclear” option, which was still not ideal.

**(6).** For the sixth iteration of our prompt, we decided to loosen the restriction on the auditor because we found it was oversensitive and failing images for “cut off text” which clearly did not have “cut off text.” We achieved this by changing aspects of our prompt like removing “ZERO TOLERANCE” and changing it to “Only fail if letters are visibly cut off.” Additionally, we adjusted the examples of when to fail and added examples of when not to fail. As a result of these changes, the images almost always eventually passed and rarely had to go to the “nuclear” option, while still almost no images were passed that should have failed the audit.

**(7).** Finally, the seventh and final iteration of our prompt involved updating the OpenAI models we used for image generation, gpt-image-2 instead of DALL-E 3, and for image auditing, gpt-4.1 instead of gpt-4o. This change improved the quality of images generated and the effectiveness of the image auditor, while overall decreasing the cost due to less evaluator-optimizer loops needing to be conducted and the image generator being more responsive to the correction prompts. Therefore, while there are still some aspects where we could continue to adjust, through these various prompt engineering techniques, this process has clearly become more effective and efficient at producing good quality images that don’t violate important guardrails.


**BEFORE / First Image Auditor Prompt (Step 2):**  
```python
"""
You are a strict brand compliance auditor reviewing a social media image.
Carefully examine the image and check it against these criteria:

1. LOGO / BRANDING: If a company logo or brand name appears, it must look correct
   and professional. Text must not be distorted, cut off, or misspelled.

2. FACTUAL ACCURACY: The image must not contain false or misleading claims.
   Examples of what to reject: promising free products, exaggerated discounts
   (e.g. "100% off", "everyone gets $1000"), or health claims not supported
   by the product context provided below.

3. TEXT LEGIBILITY: Any text overlaid on the image must be fully visible and
   not cut off at the edges. Every word must be complete and readable.

Product context: {context}

Respond ONLY with a JSON object — no markdown fences:
{{"passed": true or false, "reason": "brief explanation if failed, else empty string"}}
"""
```

**AFTER / Final Image Auditor Prompt (Step 7):**
```python
"""
You are a strict brand compliance auditor reviewing a social media image.
Examine the image carefully against ALL three criteria below.

CRITERIA 1 — LOGO & BRANDING
{logo_section}

If a logo or brand name is visible in the image:
- It must clearly match the description above (if provided).
- Text in the logo must not be distorted, misspelled, or invented.
- If the logo looks clearly WRONG (different colors, wrong name, made-up design),
  FAIL the image. If you are simply unsure, PASS — do not fail on uncertainty alone.

CRITERIA 2 — FACTUAL ACCURACY
The image must not display outright false or impossible claims. FAIL if you see:
- Promises of free money or unrealistic cash rewards (e.g. "Win $1000!")
- "100% off" or similar impossible discounts
- Medical or health claims not supported by the product context
- Pricing that clearly contradicts the product context below
Creative phrasing and marketing enthusiasm are fine — only fail on clear lies.

Product context: {context}

CRITERIA 3 — TEXT LEGIBILITY (HIGH PRIORITY)
Look at every piece of text in the image, especially near the TOP and BOTTOM edges.
FAIL only if text is CLEARLY and VISIBLY cut off — meaning letters are actually missing
their tops, bottoms, or sides. Ask yourself: "Is part of a letter actually gone?"

FAIL if:
- A letter is visibly truncated — the top, bottom, or side of the letter is cut away
- A word is partially outside the frame and letters are missing
- Ascenders (like the top of 'h', 'd', 'f') or descenders (like the bottom of 'g', 'p')
  are visibly cut off

DO NOT FAIL if:
- Text is near the edge but all letters are fully visible and complete
- There is a colored banner or block near the edge with text inside it that is fully readable
- Text simply starts close to the top — close is NOT the same as clipped

If you are not 100% certain that letters are actually cut off, PASS the image.
Only fail on clear, obvious, undeniable text clipping. Do not fail on suspicion.

NOTE ON SPELLING: Do NOT flag hashtags (e.g. #SummerTreats, #KiwiMelonMagic) as
misspellings — combining words in hashtags is intentional and correct. Do NOT flag
stylized or creative marketing text (e.g. "Summerzz", "Kiwi-licious") as misspellings.
Only flag obvious real misspellings of the product or brand name itself
(e.g. "Frozzen Custerd" instead of "Frozen Custard").

IMPORTANT: Be lenient. The goal is to catch genuinely bad images, not to be
a perfectionist. A good-enough image that serves its marketing purpose should
PASS. Only fail if something is clearly, obviously wrong.

If you FAIL, return:
  "reason" — 1-2 plain English sentences describing what is wrong, for a human to read
  "fix"    — ONE short UPPERCASE command for the image generator, max 8 words
             e.g. KEEP ALL TEXT FAR FROM EDGES / NO LOGO DISTORTION

If you PASS, return empty strings for both.

Respond ONLY with a JSON object — no markdown fences:
{{"passed": true or false, "reason": "plain English description if failed, else empty", "fix": "UPPERCASE COMMAND if failed, else empty"}}
"""
```

### **Prompt Engineer #2 - Research ReAct Loop + Tool Use**
Another example of prompt engineering that we did in this AI Agent Prototype was around the Research ReAct Loop and Tool Use. The initial Research `ReAct` Loop allowed given URLs, uploaded Files, or Web Searches to be used to gather information. However, this Researching loop had a few different issues that ranged from different spellings of the same company creating entire new folders, ruining the quick creation and consistent style of posts, to the research agent returning mostly missing, or "null", for the information it was trying to find about a company or product. Therefore, we used prompt engineering techniques to identify and address these issues.

**(1).** The first iteration of this Research ReAct Prompt addressed the first problem we identified, which was that the Agent could only handle exact name matches for a company. We often found that "Rita's" was not matching to "Rita's Italian Ice.” Therefore, using all lowercase, we made it so the Agent would check using `SequenceMatcher`, which compares the two strings and returns a similarity score (we used a 0.6 threshold), and `Substring Containment`, which would be true or false depending if the company name is contained in any of the company folder names (e.g., "*Rita's*" in "*Rita's* Italian Ice"). Finally, we included an Agentic Pattern, `Human-in-the-Loop`, to not just assume fuzzy match was correct or two companies might have similar names, so the AI Agent asks the user is this the right company, "Is Rita's the same company as Rita's Italian Ice?" This results in the agent being able to appropriately handle different spellings of the same company more effectively. Additionally, if it does not find an exact or fuzzy matches, it will look up the official name of the company and ask to confirm with User (e.g., so the folder would be labeled "Rita's Italian Ice" instead of just "Rita's"). *This was also probably more of a coding change than a prompting change, but it directly affected our prompt, so we felt it was useful to include it here.*

**BEFORE for Product Code:**
```python
if self.storage.product_exists(company_name, product_name):
    return product_name
# else: falls through to research from scratch
```

**AFTER for Product Code:**
```python
if self.storage.product_exists(company_name, input_name):
   return input_name

products_dir = self.storage.products_dir(company_name)
if products_dir.exists():
   existing_products = [
      f.stem.replace(" Product Report", "")
      for f in products_dir.glob("*.json")
   ]
   input_lower = input_name.lower()
   fuzzy_matches = [
      p for p in existing_products
      if (
         SequenceMatcher(None, input_lower, p.lower()).ratio() > 0.6
         or
         input_lower in p.lower() or p.lower() in input_lower
      )
   ]
   if fuzzy_matches:
      for match in fuzzy_matches:
         print(f"\n\U0001f50d I found an existing product that looks similar: [{match}]")
         answer = confirm(
            f'Is "{input_name}" the same product as [{match}]? (Y/n)'
         )
         if answer:
            print(f"  ✅ Using existing product [{match}]")
            return match
return input_name
```
**(2).** The second iteration of this Research ReAct Prompt focused on the problem that the Research Agent wasn't gathering enough information to fill out the necessary information. Initially, we found the agent was not gathering much information and in turn was leaving most information fields (JSON) of the company report and product report blank (or "null"). First of all, we found the Agent sometimes did zero searches before writing the report, so we clarified it had to do at least one `tool call` before writing the report. Next, we increased the `MAX_STEPS` from 3 to 6, which is the number of times the Agent can use `tool calls`. Too few calls could leave the Agent without needed information, like what we had, but too many could cause it to cost more and take longer. Finally, to address this issue, we discovered that we cut off the information from each observation at 300 characters, which was far too few to gather enough information. This first change was mostly a code change, but it did directly affect the prompt's results. Therefore, we increased the character limit per observation from 300 to 2000. As a result, the Research ReAct Loop now was able to fill in most of the company and product reports. However, there were still often more "null" fields than we would like, which will lead us to our next iteration.

**(3).** The third iteration of this Research ReAct Prompt focused on the problem that the Research Agent was still often leaving too many "null" fields in the company and product reports. We initially considered increasing the `MAX_STEP` again, but when we looked at the Agent's actions, it was never reaching those `MAX_STEPS`. Instead, it often only did one search, or `tool call`. Therefore, we added two things within the ReAct loop and one after. The first addition within the ReAct Loop was in the "IMPORTANT" section and was basically that, "If search returns thin results, do another search". This resulted in the Agent doing more searches when it did not have a lot of information or "thin" results. For the second addition to the ReAct Loop, we added a fourth tool, the `ask` tool. This `ask` tool would allow the Agent to ask the user a clarifying question (e.g. "What is the price range for Kiwi Melon?"). However, to make sure the Agent did not default to ask the user a question, we engineered a hierarchy of what `tool calls` the Agent would use first. The first tool it would use is `read_document`, then `fetch_URL`, then `web_search`, and finally `ask`. In addition to these changes in the ReAct Loop, we also added a "null" value check after the loop (greater than 1 "null"). If this check fails, it will then prompt the user to provide a URL or File, because too many nulls can really hurt the Agent's ability to create effective posts. However, we also set it to allow the User to advance if they choose to regardless. This is another use of `Human-in-the-Loop` Agentic Pattern. As a result of these changes, the Agent was able to more effectively complete the company and products reports and provided a stronger factual foundation for the post creation later in the process.

**(4).** The fourth, and final, iteration of this Research ReAct Prompt focused on improving the final check after the ReAct Loop. While having only one missing piece of information is generally okay, after more testing, we decided that it would be useful to also add a way to address this last remaining “null.” Therefore, while there is more than one "null" value, the Agent will still ask for a specific URL/File for more information, but, if there is only one "null" value, it will just directly ask the User about it. This adds some flexibility and nuance to this prompt and the final check while also not just leaving a bit of information unknown when it does not have to be.

**BEFORE / First Research ReAct Prompt:**
```python
MAX_STEPS = 3

REACT_PROMPT = """
You are a market research agent. You run in a loop of Thought, Action, PAUSE, Observation.
At the end of the loop you output a final JSON report.

Use Thought to describe your reasoning about what information you need.
Use Action to call one of your available tools — then stop and wait.
Observation will be the result of that tool call.

IMPORTANT:
- Always base your final report on Observations, not on assumptions.
- Do NOT invent facts that are not present in your search results.
- If the user provides a URL, use fetch_url rather than web_search.
- If a document was uploaded, use read_document before searching the web.

Your available actions are:

1. web_search: <query>
   Search the web for publicly available information about a company or product.
   Example: web_search: Rita's Water Ice brand overview history products

2. fetch_url: <url>
   Fetch the content of a specific URL provided by the user.
   Example: fetch_url: https://www.ritaswaterice.com/about

3. read_document: <filename>
   Read an uploaded document (PDF, txt, docx) for product or event info.
   Example: read_document: kiwi_melon_launch_brief.pdf

Example session:
Thought: I need to find information about Rita's Water Ice to write a company report.
Action: web_search: Rita's Water Ice company overview history
PAUSE

Observation: [Rita's Italian Ice] Founded in 1984 by Bob Tumolo in Philadelphia...

Thought: I have enough information to write the company report.
Answer: { ... json report ... }
"""
```

**AFTER / Final Research ReAct Prompt:**
```python
MAX_STEPS = 6

REACT_PROMPT = """
You are a market research agent. You run in a loop of Thought, Action, PAUSE, Observation.
At the end of the loop you output a final JSON report.

Use Thought to describe your reasoning about what information you need.
Use Action to call one of your available tools — then stop and wait.
Observation will be the result of that tool call.

IMPORTANT:
- You MUST perform at least one tool call before producing a final answer.
- Always base your final report on Observations, not on assumptions.
- If the first search returns thin results (very little specific information),
  do a SECOND search with a different, more specific query before answering.
- For product research: search for the product name + company name together,
  then search for the product name + 'price' or 'flavors' or 'description' separately.
- Do NOT stop after one search if the results are vague or generic.
- If a search returns nothing and no document is provided, use the ask tool.
- If the user provides a URL, use fetch_url rather than web_search.
- If a document was uploaded, use read_document before searching the web.

Your available actions are:

1. web_search: <query>
   Search the web for publicly available information about a company or product.
   Example: web_search: Rita's Water Ice brand overview history products

2. fetch_url: <url>
   Fetch the content of a specific URL provided by the user.
   Example: fetch_url: https://www.ritaswaterice.com/about

3. read_document: <filename>
   Read an uploaded document (PDF, txt, docx) for product or event info.
   Example: read_document: kiwi_melon_launch_brief.pdf

4. ask: <question>
   Ask the user a clarifying question when you need more information.
   Example: ask: Could you provide a website or document for this product?

Example session:
Thought: I need to find information about Rita's Water Ice to write a company report.
Action: web_search: Rita's Water Ice company overview history
PAUSE

Observation: [Rita's Italian Ice] Founded in 1984 by Bob Tumolo in Philadelphia...

Thought: I have enough information to write the company report.
Answer: { ... json report ... }
"""
```

---
## **Functional Code (The Logic)**

Explore our Agent's Jupyter Notebook (`AI_Agent.ipynb`) which helps to tell the "story" of our Agent. There also is a live demo using Rich's UI at the bottom of this notebook or you can just run `demo.py`. Comments on this Jupyter Notebook were made with the help of AI and give a good reflection of our journey developing this AI Agent Prototype, HoneyComb.

Here is also a link to the Recorded Demo: [Demo](https://youtu.be/875siZ7Ic-4)

---
## **Evaluation & Ethics**

**Testing and Evaluating the Agent:**
We tested and evaluated our Agent in a number of different ways.

The first way we evaluated our Agent was to look at how good the actual posts created were. This was done by using the A/B Scorer to evaluate the quality of each caption created, the Image Auditor to evaluate the quality of each image created, and the Caption Auditor to evaluate each caption created based on ethical guardrails. The A/B Scorer pushes through the highest rated caption (from 0 to 10) or the first to achieve a score of 9 or higher. Therefore, we evaluated the Agent by both what the final post caption’s score was as well as how many tests it normally had to go through. Additionally, whether the Agent’s output passed the Auditor, as well as how many times it took to pass, was another way we evaluated the quality of the Agent. Finally, for quality evaluation of the Agent, we also just looked at the output posts, especially images, and evaluated it ourselves whether they looked good, okay, or bad.

Another way we tested and evaluated the Agent was how well it created the Research Reports, Product Reports, and Style Guides, the backbone of this process. One indicator we looked at was how many missing, or “null”, fields each one of these had (*mainly company and product reports*). Additionally, how many “steps” did it take to gather the information it needed and whether it needed to ask a question or for more information from the User. The more it left missing and the more it needed to ask the User would help us evaluate how well it is gathering information to be able to write these reports.

Next, we tested our Agent by trying to break it to see how flexible or adaptable it was, or, in other words, how it was able to adapt to the unique requests or human errors. Could it handle different spellings of the same company? No, so we added fuzzy search. Could it handle additional details in the request like “Make it a giveaway.” No, so we made it so the Agent could understand and use that. Could it handle the user asking for 1 Instagram post and 2 Twitter posts? Yes, but what if they tried to modify the total number of posts later on? It fails, so we added a new guardrail to prevent the user from doing this. We went through tests like this to evaluate how flexible and adaptable our Agent is so we could evaluate how well it would perform in a real-world scenario. 

Finally, we also evaluated the frontend of our Agent, which was mainly how clean and non-technically friendly the user interface (UI) was. Since the goal is for this to be adopted by marketing professional, a target market who likely values aesthetic and ease of use, we implemented a UI, specifically Rich UI, to help try to overcome this technical barrier. We tested this UI with ourselves as well as others (*mainly family members*) to see how well they could navigate it. For most of these tests, the people were generally able to understand how to use it, but also often still needed explanations for certain parts from us. Therefore, we believe there is still room for significant improvement in this area for our Agent in the future. 

**Guardrails, Ethics, and Risks:**

In this project, we have a number of guardrails to help ensure the code works as intended, the output is of a certain quality, and the output does not violate our ethical standards and avoid bias whenever possible. 

For the first guardrail, we built restrictions into our Agent to only accept the platforms it can work with, since we only can work with Instagram, Twitter/X, and Blogs right now. Additionally, we added restrictions to what type of files can be uploaded, `.png`, `jpg`, or `jpeg`, which will help to prevent errors that are caused by the Agent trying to analyze a photo when that photo is in a format that it cannot read. Then finally we implemented guardrails to restrict whether the user can modify the total number of posts after they request if the User requests posts from multiple platforms because this broke the Agent since the Agent no longer knew how many of each type of post it needed to make for each platform, so it guessed. In each of these cases, we added explanation and guidance to help the user navigate them. 

For the other main type of guardrail present, the A/B Scorer and Auditors (*Caption and Image*) are used as quality and ethics checks. The A/B Scorer uses another model, gpt-4o-mini, since it is fast and the task is not very complex, to score each post’s caption on its quality, using criteria like originality and brand voice. If it scores 9 or more, the caption passes, but if not, it keeps going a total of five times and then chooses the highest scoring caption across all five tests. The next guardrail is the Image Auditor, which helps to ensure a certain quality of image, such as no misspellings, no cut off words, and no wrong logos. The Image Auditor fails the posts that do violate these criteria and sends a correction prompt back to the imagine creator (gpt-image-2) and the cycle repeats until the post meets the criteria to pass or it reaches the maximum cycles and the post officially fails the audit (*and is rejected*). Finally, the Caption Auditor doesn't evaluate quality, that is the A/B Scorer, it instead checks that there are no blatant lies or hate speech in the captions. However, it is only checking against the context it has been provided by the Research Agent, so, for checking for lies, it is more like a last double check rather than a 100% accurate fact checker.

For future expansion of this project, especially if this expands in the cloud and across a company, permissions will need to be put into place to restrict who can see and modify what folders. You don't want everyone to modify what your company reports, product reports, or style guides are without your permission because that would ruin the whole "consistent" focus and style that this AI Agent is meant to produce. Therefore, you will likely want to set permission depending on who you want to be able to access which folders, which will help improve collaboration too. However, if someone is using this AI Agent to create posts for an upcoming product that isn't announced that is supposed to be secret, this Agent does send this information to OpenAI, which could cause security problems too.

