Hello! This is David Scott and Senthil Vel's Spring 2026 SJU Agentic AI & Machine Learning Final Project.

Look at flow chart we created. This information is outdate. Still updating.

**Objective:**
Develop an agent(s) that will create and schedule social media post(s) for a specific organization’s product or event. A user should also be able to come back in the future and request the Agent create additional posts for that organization’s product or event. Those future posts should have a consistent focus and similar style based on a marketing guide (product/event guide and brand style guide) that the agent will create or had already created.

**All Local Files will be stored like this:**

[Marketing Post Creation and Scheduling] - Main Folder
--- [Company/Organization Folders]
    --- Company/Organization Report
    --- [Product/Event Information Guide]
        --- Product/Event Information Guide
    --- [Brand Style Guides]
        --- Brand Style Guides
--- [Marketing Guidelines]
   --- [[Date_Created] [Company/Organization_Name] [Product/Event_Name] Marketing Guideline]
      --- Marketing Guideline
      --- [Ouputs]
         --- Outputs [from this project]

   Marketing Guidelines are the Marketing Guideline itself plus the Outputs, as they both are a pair, to create one the other must of been created.

   On the other side, in order to have a product/event information guide or a brand style guide, a company must be identified first. 

    Brand Style Guides will be labeled as "[company_name]_[product/event_name]_[last_updated_date]_Brand_Style_Guideline". 
        This will allow the agent to ask the user for a new product if they want to use the style guideline of any of the previous style guides from that company/organization
   


**Agents:**

1. **Agent 1 - ReAct Agent and Manager** (Determine what inputs the User has provided and reacts appropriately - communicating with other Agents and User as needed)
   **First Half**
2. *Agent 2 - Report Creator and Local Storage Manager* (Creates and Updates Company/Organization Reports, Product/Event Information Guides, and Style Guides. Manages Local Storage of Folders)
3. *Agent 3 - Marketing Guideline Creator* (Takes the three background elements, and combines it with the input instructions and any reference examples, with langchain to create a Marketing Guideline that will be easy for the Agents in the second half of the project ot use to create the actual posts + schedule)
   **Second Half**
1. *Agent 4 - Post Creator (use Marketing Guideline from Agent 3 to develop posts)
2. **Agent 5** - A/B Tester (Uses Different Model to Score Agent 4's Output based on Agent 3's Marketing Guideline)
3. **Agent 6 - Scheduler** (only activates if schedule is requested. Function Call to Google Calendar to Schedule when the approved posts from Agent 4 should be posted.)



**Process:**

*First Type*:
1. *Input:*
   1. Primary instruction (string) "I would like to create and schedule three instagram ads for Rita's new Kiwi Melon Italian Ice in June"
   2. (optional) References (string - description or URL) "Please use this use https://www.instagram.com/p/DWzPcfGE1bb/?img_index=1, https://www.instagram.com/p/DWcL6F7D0aS/, and https://www.instagram.com/p/DWhQXSmEz78/ as references"
   3. (Alternative) "Update" or "View": "I would like to view what information you have

2. *ReAct takes User Input and figures out what processes need to be taken place:*
   1. *Step 1:* Are they asking to "View" something? 
      1. Yes -> Is it Company Report, Company's Product, Company's or Product's Style Guideline(s), or a Marketing Report? Return to them all that they ask for.
      2. No -> Go to Step 2

   2. *Step 2:* What Company/Organization are they talking about? Do I have Information stored about the company (e.g., Rita's)? 
      1. Yes -> Pull Company Report from Local Storage. Did they ask to update?
         1. Yes -> Send to Agent 2 to Update. 
         2. No ->  Tell "Last Updated Information" and Continue to Step 3.
      2. Maybe -> If no company matches but there is a similar name (Rita vs Rita's), ask if they are talking about X company?
         1. Yes -> Pull Company Report from Local Storage. Did they ask to update?
            1. Yes -> Send to Agent 2 to Update. 
            2. No ->  Tell "Last Updated Information" and Continue to Step 3.
         2. No -> Search for Another Company. 
            1. If no other similar company names are found start process of creating Company Information Report (Talk to Agent 2)
      3. No -> "New Company" Start process of creating Company Information Report, Product/Event Report, and Brand Guideline (Talk to Agent 2)

   3. *Step 3:* What product/event are they talking about? Under that company, do I have a product/event that? 
      1. Yes -> Pull Product/Event Report from Local Storage. Did they ask to update?
         1. Yes -> Send to Agent 2 to Update. 
         2. No ->  Tell "Last Updated Information" and Continue to Step 4.
      2. Maybe -> Ask if they are talking about X company 
      3. No -> Start process of creating Company Information (Talk to Agent 2)
   
   4. *Step 4*: Is there a brand style guide that matches that company/organization?
       1. Yes -> Is there a brand style guide that matches the specific product/event?
          1. Yes -> Pull the specific style guide from Local Storage. Did they ask to update or provide references (e.g., a social media link)?
            1. Yes -> Send to Agent 2 to Update. 
            2. No ->  Tell "Last Updated Information" and Continue to Step 5.
         1. No -> Tell then the product/events of other style guides and ask if they want to use them entirely, as a reference, or not at all?
            1. Enitrely ->
            2. As Reference ->
            3. No at All ->
      1. No -> 


