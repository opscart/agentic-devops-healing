"""
OpenAI Client for Azure OpenAI Service or OpenAI API
"""

import os
import logging
from openai import OpenAI


class OpenAIClient:
    """Client for OpenAI operations"""
    
    def __init__(self):
        self.endpoint = os.getenv("OPENAI_ENDPOINT")
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_DEPLOYMENT_NAME", "gpt-4o")
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY must be set")
        
        # Check if using Azure OpenAI or standard OpenAI
        if self.endpoint and "azure" in self.endpoint.lower():
            # Azure OpenAI
            from openai import AzureOpenAI
            self.api_version = os.getenv("OPENAI_API_VERSION", "2024-08-01-preview")
            
            self.client = AzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                api_version=self.api_version
            )
        else:
            # Standard OpenAI API (openai.com)
            self.client = OpenAI(
                api_key=self.api_key
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
            
            # Check if using reasoning models (o1, o3, gpt-5.x series)
            model = self.model.lower()
            is_reasoning_model = (
                model.startswith('o1') or 
                model.startswith('o3') or 
                'gpt-5' in model or
                'gpt5' in model
            )
            
            logging.info(f"Using model: {self.model}, is_reasoning_model: {is_reasoning_model}")
            
            # Build request parameters
            request_params = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.3,
            }
            
            # Use appropriate token parameter
            if is_reasoning_model:
                request_params["max_completion_tokens"] = 2000
                logging.info("Using max_completion_tokens for reasoning model")
            else:
                request_params["max_tokens"] = 2000
                logging.info("Using max_tokens for standard model")
            
            response = self.client.chat.completions.create(**request_params)
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Error calling OpenAI: {str(e)}")
            raise