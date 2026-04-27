import re
import traceback
from ddgs import DDGS
import httpx
import wikipedia
import numexpr as ne
from src.simpleChatBot_chatgpt import SimpleChatBot as ChatBot

prompt="""
You run in a loop of Thought, Action, PAUSE, Observation.
At the end of the loop, you output an Answer.

Use Thought to describe your thoughts about the question you have been asked.
Use Action to run one of the actions available to you - then return PAUSE.
Observation will be the result of running those actions.

*Your available actions are:*
1. search:
e.g. search: <search query>
Searches the internet for information related to the query. Use this for general information retrieval.

2. wikisearch:
e.g. wikisearch: <search query>
Searches Wikipedia for the same query used in search. Use this for Wikipedia-specific information.

3. calculate:
e.g. calculate: <mathematical expression>
Runs a calculation and returns the number - uses Python, so be sure to use floating-point syntax if necessary.

4. ask_user:
e.g. ask_user: <clarification question>
Asks the user for clarification or additional input. Use this when the question is ambiguous or requires more details.

# Error Handling:
If an action fails or returns no relevant information, use Thought to describe the issue and choose an alternative action. For example:
- If `search` returns no results, use `wikisearch`.
- If a calculation is invalid, use Thought to explain the error and try a different approach.
- If the question is unclear, use `ask_user` to request clarification.

# Example Session:
Question: What year was the Eiffel Tower built?
Thought: I need to find the construction year of the Eiffel Tower. I can search the internet for this.
Action: search: construction year of Eiffel Tower
PAUSE

*While pausing, you will be called again with this:*

Observation: The Eiffel Tower was built in 1889.

*You then output:*

Answer: The Eiffel Tower was built in 1889.

# Additional Notes:
- Ensure the Answer strictly addresses the question asked, unless explicitly instructed otherwise.
- If the question requires multiple steps, use Thought to summarize previous steps and maintain context.
- Use `ask_user` when the question is ambiguous or requires clarification.
""".strip()

# Improved regex with flexibility for spacing and multi-word actions
ACTION_RE=re.compile(r"^Action:\s*([\w]+)\s*:\s*(.+)$", re.DOTALL)


def query(question, max_turns=5):
    i=0
    bot=ChatBot(prompt)
    next_prompt=question
    label="BOT RESPONSE:"
    while i<max_turns:
        i+=1
        try:
            result=bot(next_prompt)
            print(label, result)

            # Extract actions from result
            actions=[ACTION_RE.match(action.strip()) for action in result.split("\n") if
                     ACTION_RE.match(action.strip())]

            if actions:
                action, action_input=actions[0].groups()
                action_input=action_input.strip()

                if action not in known_actions:
                    raise ValueError(f"Unknown action: {action}: {action_input}")

                print(f" -- Running {action} {action_input}")
                observation=known_actions[action](action_input)
                print("Observation:", observation)

                next_prompt=f"Observation: {observation}"
            else:
                return  # No action found, exit loop

        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()
            return


def websearch(q, max_results=1):
    try:
        results=DDGS().text(q, max_results=max_results)
        # results[0]["body"] = "I don't know the answer, I am sorry."
        print("WEB SEARCH RESULTS>>>", results)
        if results:
            return results[0]["body"]
        else:
            return "No relevant information found."
    except Exception as e:
        print(f"Search error: {e}")
        return "Error: Could not retrieve search results."


def wikisearch(q):
    """Search Wikipedia for information using the wikipedia package."""
    try:
        result = wikipedia.summary(q, sentences=3)
        return result
    except wikipedia.exceptions.DisambiguationError as e:
        # Return first few disambiguation options
        options = e.options[:3]
        return f"Multiple results found. Did you mean: {', '.join(options)}?"
    except wikipedia.exceptions.PageError:
        return f"No Wikipedia page found for '{q}'."
    except Exception as e:
        return f"Error: {str(e)}"


def calculate(expression):
    try:
        result=ne.evaluate(expression)
        print("CALCULATED>>>", result)
        return result
    except Exception as e:  #Catches the broader set of Numexpr errors
        print(f"Calculation error: {e}")
        return "Error: Invalid calculation expression."


def ask_user(q):
    return input(f"Clarification needed, INPUT>>>: {q}")


known_actions={
    "search": websearch,
    "wikisearch": wikisearch,
    "calculate": calculate,
    "ask_user": ask_user
}

"""
# Potential Improvement: Expand the Action Set
Consider adding more actions to handle a wider range of tasks. For example:
4. ask_user: e.g. ask_user: <clarification question>
   Asks the user for clarification or additional input.
5. retrieve_document: e.g. retrieve_document: <document identifier>
   Retrieves a specific document or piece of information from a predefined source.
"""

# def wikisearch(query):
#     try:
#         results = wikipedia.summary(query, sentences=100)
#         print("WIKI RESULTS:", results)
#         return results  # Adjust sentences as needed
#     except wikipedia.exceptions.PageError:
#         return "Error: Wikipedia page not found."
#     except wikipedia.exceptions.DisambiguationError as e:
#         return f"Error: Disambiguation error.  Please be more specific.  Possible options: {e.options}"
#     except Exception as e:
#         return f"Error: Wikipedia search failed: {e}"

if __name__=="__main__":
    q="Find the population of the largest city in France and divide it by a number."
    # q="What is the population of Paris times 2 plus the population of London?"
    # q="what is (2+10)-2"
    query(q)

    # q = "what is the capital of England?"
    # q = "what is (2+10)-2"
    # query(q)
