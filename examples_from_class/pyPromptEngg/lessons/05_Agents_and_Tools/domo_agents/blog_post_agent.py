"""
Blog Post Agent Module

This module implements a specialized AI agent for generating long-form blog content.
The agent is optimized for creating comprehensive, detailed articles that provide
in-depth information about products, their features, and benefits.
"""

# demo_agents/blog_post_agent.py
import time
from .base_agent import BaseAgent


class BlogPostAgent(BaseAgent):
    """
    An AI agent specialized in writing long-form blog posts.
    
    This agent generates comprehensive, well-structured blog posts that provide
    detailed information about products. Content includes engaging titles,
    thorough explanations of features and benefits, and clear calls-to-action.
    
    Inherits from:
        BaseAgent: Provides OpenAI client and basic agent functionality
    """

    def __init__(self):
        """
        Initialize the Blog Post agent with its specialized role name.
        """
        super().__init__(name="Blog Post Writer")

    def execute(self, product_brief: dict, model_name: str = 'gpt-4o-mini') -> str:
        """
        Generate a detailed blog post for a product based on the provided brief.
        
        This method crafts a comprehensive 500-word blog post that explores the
        product in depth, explaining its features, benefits, and value proposition.
        The post includes an engaging title and a compelling call-to-action.
        
        Args:
            product_brief (dict): Product information containing:
                - name (str): Product name
                - description (str): Brief product description
                - features (list): List of key product features
            model_name (str): OpenAI model to use (default: 'gpt-4o-mini')
        
        Returns:
            str: A formatted string containing a complete blog post with title,
                body content, and call-to-action
        
        Note:
            Includes longest processing time among all agents to simulate
            the complexity of generating and refining long-form content
        """
        print(f"[{self.name}] Starting to draft a detailed blog post using OpenAI...")

        # Extract product information from the brief
        product_name = product_brief['name']
        description = product_brief['description']
        features = ", ".join(product_brief['features'])

        # Construct a detailed prompt for the OpenAI model
        # The prompt is tailored to generate comprehensive blog content
        prompt = (
            f"You are a seasoned content writer specializing in detailed blog posts. "
            f"Write a 500-word introductory blog post for a new product.\n\n"
            f"Product Name: {product_name}\n"
            f"Description: {description}\n"
            f"Key Features: {features}\n\n"
            f"The post should explain what the product is, its key benefits, and why it's a must-have. "
            f"Include an engaging title and a concluding call to action."
        )

        # Simulate thinking time before API call
        time.sleep(1)
        
        # Make API call to OpenAI using the chat completions endpoint
        response = self.openai_client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are an expert blog content writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,  # Balanced creativity for engaging yet informative content
            max_tokens=1500   # Higher limit for long-form content (500+ words)
        )

        # Extract the generated content from the API response
        llm_response = response.choices[0].message.content
        
        # Simulate longer processing time for blog post refinement
        # Long-form content typically requires more editing and validation
        time.sleep(4)

        print(f"[{self.name}] Finished drafting blog post.")
        
        # Return formatted response with clear section header
        return f"**Blog Post Content from OpenAI:**\n{llm_response.strip()}"