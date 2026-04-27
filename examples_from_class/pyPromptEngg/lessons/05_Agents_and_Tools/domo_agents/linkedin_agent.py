"""
LinkedIn Agent Module

This module implements a specialized AI agent for generating LinkedIn content.
The agent is optimized for creating professional, business-focused posts that
resonate with a B2B audience and follow LinkedIn's best practices.
"""

# demo_agents/linkedin_agent.py
import time
from .base_agent import BaseAgent


class LinkedInAgent(BaseAgent):
    """
    An AI agent specialized in creating LinkedIn content.
    
    This agent generates professional, business-oriented posts suitable for
    LinkedIn's platform. Content emphasizes business value, innovation, and
    includes appropriate professional hashtags and calls-to-action.
    
    Inherits from:
        BaseAgent: Provides OpenAI client and basic agent functionality
    """

    def __init__(self):
        """
        Initialize the LinkedIn agent with its specialized role name.
        """
        super().__init__(name="LinkedIn Professional")

    def execute(self, product_brief: dict, model_name: str = 'gpt-4o-mini') -> str:
        """
        Generate LinkedIn content for a product based on the provided brief.
        
        This method crafts a professional, business-focused LinkedIn post that
        highlights product value, innovation, and business benefits. The content
        is designed to engage a professional B2B audience.
        
        Args:
            product_brief (dict): Product information containing:
                - name (str): Product name
                - description (str): Brief product description
                - features (list): List of key product features
            model_name (str): OpenAI model to use (default: 'gpt-4o-mini')
        
        Returns:
            str: A formatted string containing a professional LinkedIn post
                with business value proposition and call-to-action
        
        Note:
            Includes longer processing time than Twitter agent to simulate
            more detailed content generation
        """
        print(f"[{self.name}] Starting to write a professional post using OpenAI...")

        # Extract product information from the brief
        product_name = product_brief['name']
        description = product_brief['description']
        features = ", ".join(product_brief['features'])

        # Construct a detailed prompt for the OpenAI model
        # The prompt is tailored to generate LinkedIn-specific professional content
        prompt = (
            f"You are a professional B2B marketing specialist for LinkedIn. "
            f"Write a compelling LinkedIn post introducing a new product.\n\n"
            f"Product Name: {product_name}\n"
            f"Description: {description}\n"
            f"Key Features: {features}\n\n"
            f"Focus on business value, innovation, and include a call to action. "
            f"Use relevant professional hashtags."
        )

        # Simulate thinking time before API call
        time.sleep(1)
        
        # Make API call to OpenAI using the chat completions endpoint
        response = self.openai_client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a LinkedIn B2B marketing specialist."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,  # Balanced creativity while maintaining professionalism
            max_tokens=800    # More tokens for longer, detailed LinkedIn content
        )

        # Extract the generated content from the API response
        llm_response = response.choices[0].message.content
        
        # Simulate longer processing for more detailed content
        # LinkedIn posts typically require more refinement than tweets
        time.sleep(2)

        print(f"[{self.name}] Finished writing professional post.")
        
        # Return formatted response with clear section header
        return f"**LinkedIn Content from OpenAI:**\n{llm_response.strip()}"