"""
OpenAI Client for Azure OpenAI Service
"""

import os
import logging
from openai import AzureOpenAI


class OpenAIClient:
    """Client for Azure OpenAI operations"""
    
    def __init__(self):
        self.endpoint = os.getenv("OPENAI_ENDPOINT")
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.deployment_name = os.getenv("OPENAI_DEPLOYMENT_NAME", "gpt-4o-analyzer")
        self.api_version = os.getenv("OPENAI_API_VERSION", "2024-08-01-preview")
        
        if not self.endpoint or not self.api_key:
            raise ValueError("OPENAI_ENDPOINT and OPENAI_API_KEY must be set")
        
        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version
        )
    
    async def analyze(self, prompt: str, system_message: str = None) -> str:
        """Send a prompt to OpenAI and get response"""
        try:
            messages = []
            
            if system_message:
                messages.append({
                    "role": "system",
                    "content": system_message
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                temperature=0.3,  # Lower temperature for more deterministic results
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Error calling OpenAI: {str(e)}")
            raise