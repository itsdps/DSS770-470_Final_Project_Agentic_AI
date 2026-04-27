"""
agent_parallel.py

Parallel workflow orchestrator — mirrors the ParallelWorkflow class from
the class notebook (workflows/parallel_workflow.py) almost exactly.

The only addition is that we spawn one agent PER POST (not just one per
platform), so if the user asks for 3 Instagram posts, 3 InstagramAgent
threads run simultaneously.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict


class ParallelWorkflow:
    """
    Executes multiple platform agents simultaneously using ThreadPoolExecutor.

    Each agent receives a product_brief dict and calls execute() independently.
    Results are collected as each thread finishes (not necessarily in order).

    This is identical to the class ParallelWorkflow, with one change:
    agent names include a post number so we can tell posts apart in results.

    Example:
        >>> agents = [InstagramAgent(key), TwitterAgent(key)]
        >>> workflow = ParallelWorkflow(agents=agents)
        >>> results = workflow.run(product_brief)
    """

    def __init__(self, agents: List):
        self.agents = agents

    def run(self, product_brief: dict, model_name: str = "gpt-4o") -> Dict[str, dict]:
        """
        Execute all agents in parallel and return aggregated results.

        Args:
            product_brief (dict): Passed to every agent's execute() method.
                Must include: context, post_num, total_posts.
            model_name (str): Passed through to execute() (agents may ignore it
                if they have their own model set — matches class signature).

        Returns:
            Dict[str, dict]: Maps "{agent.name} #{post_num}" -> post result dict.
        """
        results = {}

        # One thread per agent — identical to class implementation
        with ThreadPoolExecutor(max_workers=len(self.agents)) as executor:
            future_to_agent = {
                executor.submit(agent.execute, product_brief, model_name): agent
                for agent in self.agents
            }

            for future in as_completed(future_to_agent):
                agent = future_to_agent[future]
                try:
                    content = future.result()
                    # Key includes post number so multiple posts don't overwrite each other
                    key = f"{agent.name} (Post {product_brief.get('post_num', '?')})"
                    results[key] = content
                except Exception as exc:
                    error_msg = f"Agent {agent.name} raised an exception: {exc}"
                    print(error_msg)
                    key = f"{agent.name} (Post {product_brief.get('post_num', '?')})"
                    results[key] = {"caption": error_msg, "score": 0, "platform": "error"}

        return results


def run_all_posts(agents_per_post: List[List], product_brief_base: dict,
                  model_name: str = "gpt-4o") -> List[dict]:
    """
    Convenience wrapper: runs parallel workflows for each post number.

    In the class notebook, all agents shared ONE product_brief.
    Here we need N posts, so we run the workflow N times with post_num set,
    but still in parallel across platforms within each post.

    Args:
        agents_per_post: List of agent lists, one list per post number.
            e.g. [[InstagramAgent, TwitterAgent], [InstagramAgent, TwitterAgent]]
        product_brief_base: Base brief (context, total_posts, etc.)
        model_name: Passed to workflow.run()

    Returns:
        Flat list of all post result dicts across all posts and platforms.
    """
    all_results = []

    for post_num, agents in enumerate(agents_per_post, 1):
        brief = {**product_brief_base, "post_num": post_num}
        workflow = ParallelWorkflow(agents=agents)

        print(f"\n  ⏱️  Starting parallel execution for post {post_num}/{len(agents_per_post)}...")
        start = time.time()

        results = workflow.run(brief, model_name)

        elapsed = time.time() - start
        print(f"  ✨ Post {post_num} done in {elapsed:.1f}s")

        all_results.extend(results.values())

    return all_results
