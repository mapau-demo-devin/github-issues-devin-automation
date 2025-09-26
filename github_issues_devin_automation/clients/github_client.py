"""
GitHub API client for fetching issues and repository information.
"""

import requests
from typing import List, Dict, Any
from ..config.settings import get_github_token

class GitHubClient:
    def __init__(self):
        self.token = get_github_token()
        self.base_url = "https://api.github.com"
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    
    def list_issues(self, repo: str, state: str = 'open', limit: int = 10) -> List[Dict[Any, Any]]:
        """
        List issues from a GitHub repository.
        
        Args:
            repo: Repository in format 'owner/repo'
            state: Issue state ('open', 'closed', 'all')
            limit: Maximum number of issues to return
        
        Returns:
            List of issue dictionaries
        """
        url = f"{self.base_url}/repos/{repo}/issues"
        params = {
            'state': state,
            'per_page': limit,
            'sort': 'updated',
            'direction': 'desc'
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def get_issue(self, repo: str, issue_number: int) -> Dict[Any, Any]:
        """
        Get a specific issue from a GitHub repository.
        
        Args:
            repo: Repository in format 'owner/repo'
            issue_number: Issue number
        
        Returns:
            Issue dictionary
        """
        url = f"{self.base_url}/repos/{repo}/issues/{issue_number}"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    def get_repository(self, repo: str) -> Dict[Any, Any]:
        """
        Get repository information.
        
        Args:
            repo: Repository in format 'owner/repo'
        
        Returns:
            Repository dictionary
        """
        url = f"{self.base_url}/repos/{repo}"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
