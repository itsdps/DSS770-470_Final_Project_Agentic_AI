"""
Parallel Workflow Module

This module implements a parallelization pattern for executing multiple AI agents 
simultaneously using Python's concurrent.futures ThreadPoolExecutor. This approach 
significantly reduces the total execution time when multiple independent tasks can 
be performed concurrently.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict


class ParallelWorkflow:
    """
    A workflow orchestrator that executes multiple agents in parallel.
    
    This class manages the concurrent execution of multiple AI agents, where each
    agent performs an independent task on the same input data. The workflow collects
    and aggregates results from all agents once they complete.
    
    Attributes:
        agents (List): A list of agent instances that will be executed in parallel.
                      Each agent must implement an `execute` method.
    
    Example:
        >>> agents = [TwitterAgent(), LinkedInAgent(), BlogPostAgent()]
        >>> workflow = ParallelWorkflow(agents=agents)
        >>> results = workflow.run(product_brief)
    """
    
    def __init__(self, agents: List):
        """
        Initialize the parallel workflow with a list of agents.
        
        Args:
            agents (List): A list of agent instances to be executed in parallel.
        """
        self.agents = agents
    
    def run(self, product_brief: dict, model_name: str = 'gpt-4o-mini') -> Dict[str, str]:
        """
        Execute all agents in parallel and aggregate their results.
        
        This method uses ThreadPoolExecutor to run all agents concurrently,
        allowing multiple API calls to execute simultaneously. This is particularly
        effective for I/O-bound operations like API calls to LLM services.
        
        Args:
            product_brief (dict): The input data containing product information
                                 to be passed to all agents.
            model_name (str): The OpenAI model to use (default: 'gpt-4o-mini').
        
        Returns:
            Dict[str, str]: A dictionary mapping agent names to their generated content.
                           Example: {'Twitter Specialist': '...', 'LinkedIn Professional': '...'}
        
        Note:
            - All agents receive the same product_brief as input
            - Execution order is not guaranteed
            - If any agent fails, the error is captured and returned in the results
        """
        results = {}
        
        # Use ThreadPoolExecutor for concurrent execution
        # max_workers=len(self.agents) ensures each agent gets its own thread
        with ThreadPoolExecutor(max_workers=len(self.agents)) as executor:
            # Submit all agent tasks to the thread pool
            # This creates a mapping between future objects and their corresponding agents
            future_to_agent = {
                executor.submit(agent.execute, product_brief, model_name): agent
                for agent in self.agents
            }
            
            # Process results as they complete (not necessarily in submission order)
            for future in as_completed(future_to_agent):
                agent = future_to_agent[future]
                try:
                    # Retrieve the result from the completed future
                    content = future.result()
                    results[agent.name] = content
                except Exception as exc:
                    # Capture any exceptions that occurred during agent execution
                    error_msg = f"Agent {agent.name} generated an exception: {exc}"
                    print(error_msg)
                    results[agent.name] = error_msg
        
        return results
