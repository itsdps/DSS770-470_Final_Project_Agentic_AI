"""
agent_parallel.py

Parallel workflow orchestrator — mirrors the ParallelWorkflow class from
the class notebook (workflows/parallel_workflow.py) almost exactly.

The only additions vs the class version:
  - One agent per post (not just one per platform) so N posts run in parallel
  - product_brief carries image_mode, selected_images, and style_vibe so each
    agent knows what to do with images after generating its caption
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict


class ParallelWorkflow:
    """
    Executes multiple platform agents simultaneously using ThreadPoolExecutor.

    Each agent receives a product_brief dict and calls execute() independently.
    Results are collected as each thread finishes (not necessarily in order).

    Identical to the class ParallelWorkflow — agent names include a post number
    so multiple posts don't overwrite each other in the results dict.

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
                Must include: context, post_num, total_posts,
                image_mode, selected_images, style_vibe.
            model_name (str): Passed through to execute() — matches class signature.

        Returns:
            Dict[str, dict]: Maps "{agent.name} (Post {n})" -> post result dict.
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
                key   = f"{agent.name} (Post {product_brief.get('post_num', '?')})"
                try:
                    results[key] = future.result()
                except Exception as exc:
                    print(f"  ❌ Agent {agent.name} raised an exception: {exc}")
                    results[key] = {
                        "caption":       f"Error: {exc}",
                        "image_context": "",
                        "image_bytes":   None,   # keeps save_posts() safe
                        "score":         0,
                        "platform":      "error",
                    }

        return results


def run_all_posts(agents_per_post: List[List], product_brief_base: dict,
                  model_name: str = "gpt-4o") -> List[dict]:
    """
    Convenience wrapper: runs one parallel workflow per post number.

    In the class notebook all agents shared one product_brief.
    Here we need N posts, so we run the workflow N times (one per post),
    but still in parallel across platforms within each post.

    Args:
        agents_per_post:    List of agent lists, one per post number.
                            e.g. [[InstagramAgent, TwitterAgent], [...]]
        product_brief_base: Base brief containing:
                              context, total_posts, image_mode,
                              selected_images, style_vibe
        model_name:         Passed to workflow.run()

    Returns:
        Flat list of all post result dicts across all posts and platforms.
    """
    all_results = []

    for post_num, agents in enumerate(agents_per_post, 1):
        # Merge post_num into the base brief for this batch
        # All image fields from the base brief pass through automatically
        # because we spread product_brief_base — nothing gets lost
        brief = {**product_brief_base, "post_num": post_num}

        workflow = ParallelWorkflow(agents=agents)

        print(f"\n  ⏱️  Starting parallel execution for post {post_num}/{len(agents_per_post)}...")
        start = time.time()

        results  = workflow.run(brief, model_name)
        elapsed  = time.time() - start

        print(f"  ✨ Post {post_num} done in {elapsed:.1f}s")
        all_results.extend(results.values())

    return all_results
