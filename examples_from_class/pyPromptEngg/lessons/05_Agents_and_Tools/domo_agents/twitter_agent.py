"""
Twitter Agent Module

This module implements a specialized AI agent for generating Twitter/X content.
The agent is optimized for creating short-form, engaging social media posts
that fit within Twitter's character constraints and best practices.
"""

# demo_agents/twitter_agent.py
import time
from .base_agent import BaseAgent


class TwitterAgent(BaseAgent):
    """
    An AI agent specialized in creating Twitter/X content.
    
    This agent generates concise, engaging tweets with emojis and hashtags
    optimized for Twitter's platform. It follows best practices for Twitter
    content including character limits and engagement-focused language.
    
    Inherits from:
        BaseAgent: Provides OpenAI client and basic agent functionality
    """

    def __init__(self):
        """
        Initialize the Twitter agent with its specialized role name.
        """
        super().__init__(name="Twitter Specialist")

    def execute(self, product_brief: dict, model_name: str = 'gpt-4o-mini') -> str:
        """
        Generate Twitter content for a product based on the provided brief.
        
        This method crafts 3 short, catchy tweets suitable for Twitter/X platform.
        Each tweet is designed to be under 280 characters and includes relevant
        emojis and hashtags to maximize engagement.
        
        Args:
            product_brief (dict): Product information containing:
                - name (str): Product name
                - description (str): Brief product description
                - audience (str): Target audience description
            model_name (str): OpenAI model to use (default: 'gpt-4o-mini')
        
        Returns:
            str: A formatted string containing 3 Twitter-optimized tweets
                with emojis and hashtags
        
        Note:
            Includes simulated processing time to demonstrate parallel execution benefits
        """
        print(f"[{self.name}] Starting to craft tweets using OpenAI...")

        # Extract product information from the brief
        product_name = product_brief['name']
        description = product_brief['description']
        target_audience = product_brief['audience']

        # Construct a detailed prompt for the OpenAI model
        # The prompt is tailored to generate Twitter-specific content
        prompt = (
            f"You are a concise and engaging social media expert for Twitter/X. "
            f"Create 3 short, catchy tweets (under 280 characters each) for a new product.\n\n"
            f"Product Name: {product_name}\n"
            f"Description: {description}\n"
            f"Target Audience: {target_audience}\n\n"
            f"Include relevant emojis and hashtags. Focus on excitement and brevity."
        )

        # Simulate thinking time before API call
        # In parallel execution, multiple agents can think simultaneously
        time.sleep(1)

        # Make API call to OpenAI using the chat completions endpoint
        response = self.openai_client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a Twitter/X content specialist."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,  # Higher temperature for more creative, varied output
            max_tokens=500    # Sufficient for multiple short tweets
        )

        # Extract the generated content from the API response
        llm_response = response.choices[0].message.content

        # Simulate post-processing time (e.g., validation, formatting)
        time.sleep(1)

        print(f"[{self.name}] Finished crafting tweets.")

        # Return formatted response with clear section header
        return f"**Twitter Content from OpenAI:**\n{llm_response.strip()}"
