"""
Devin API client for creating and managing Devin sessions.
"""

import os
import requests
from typing import Dict, Any

class DevinClient:
    def __init__(self):
        self.api_key = os.getenv('DEVIN_API_KEY')
        if not self.api_key:
            raise ValueError("DEVIN_API_KEY environment variable is required")
        
        self.base_url = os.getenv('DEVIN_API_BASE_URL', 'https://api.devin.ai/v1')
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def create_session(self, prompt: str, **kwargs) -> Dict[Any, Any]:
        """
        Create a new Devin session.
        
        Args:
            prompt: Task description for Devin
            **kwargs: Additional session parameters (snapshot_id, unlisted, etc.)
        
        Returns:
            Session creation response with session_id and url
        """
        url = f"{self.base_url}/sessions"
        
        data = {
            'prompt': prompt,
            **kwargs
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        
        return response.json()
    
    def send_message(self, session_id: str, message: str) -> None:
        """
        Send a message to an existing Devin session.
        
        Args:
            session_id: ID of the session to send message to
            message: Message to send to Devin
        """
        url = f"{self.base_url}/sessions/{session_id}/message"
        
        data = {
            'message': message
        }
        
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
    
    def get_session(self, session_id: str) -> Dict[Any, Any]:
        """
        Get details about an existing session.
        
        Args:
            session_id: ID of the session to retrieve
        
        Returns:
            Session details dictionary
        """
        url = f"{self.base_url}/sessions/{session_id}"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    def list_sessions(self, limit: int = 10) -> Dict[Any, Any]:
        """
        List recent Devin sessions.
        
        Args:
            limit: Maximum number of sessions to return
        
        Returns:
            Sessions list response
        """
        url = f"{self.base_url}/sessions"
        params = {'limit': limit}
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        return response.json()
