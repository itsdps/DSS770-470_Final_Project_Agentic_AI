"""
Base Agent Module

This module defines the abstract base class for all specialized AI agents.
Each agent inherits from this base class and must implement the execute method
to perform its specific task using the OpenAI API.
"""

# demo_agents/base_agent.py
from abc import ABC, abstractmethod
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents in the social media campaign system.
    
    This class provides common functionality for all agents, including:
    - Initialization of the OpenAI client
    - Storage of the agent's name/role
    - Abstract method definition that all subclasses must implement
    
    Attributes:
        name (str): The name/role of the agent (e.g., "Twitter Specialist")
        openai_client (OpenAI): The OpenAI client instance for making API calls
    
    Note:
        This is an abstract base class and cannot be instantiated directly.
        Subclasses must implement the execute() method.
    """
    
    def __init__(self, name: str):
        """
        Initialize the base agent with a name and OpenAI client.
        
        Args:
            name (str): The name or role identifier for this agent
        
        Raises:
            KeyError: If OPENAI_API_KEY environment variable is not set
        """
        self.name = name
        
        # Initialize OpenAI client with API key from environment
        try:
            api_key = os.environ["OPENAI_API_KEY"]
            self.openai_client = OpenAI(api_key=api_key)
        except KeyError:
            error_msg = "🔴 API Key Error: OPENAI_API_KEY environment variable not set."
            print(error_msg)
            raise

    @abstractmethod
    def execute(self, product_brief: dict, model_name: str) -> str:
        """
        Execute the agent's specific task.
        
        This is an abstract method that must be implemented by all subclasses.
        Each agent should use the OpenAI API to generate content specific to
        their platform or purpose.
        
        Args:
            product_brief (dict): A dictionary containing product information including:
                - name: Product name
                - description: Product description
                - audience: Target audience
                - features: List of key features
            model_name (str): The OpenAI model to use (e.g., 'gpt-4o-mini')
        
        Returns:
            str: The generated content from the agent
        
        Raises:
            NotImplementedError: If the subclass doesn't implement this method
        """
        pass