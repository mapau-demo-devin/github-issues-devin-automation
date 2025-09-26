"""
Configuration settings for GitHub Issues Devin Automation.
"""

import os
from dotenv import load_dotenv

load_dotenv()

def get_github_token():
    """Get GitHub token from environment."""
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required")
    return token

def get_devin_api_key():
    """Get Devin API key from environment."""
    api_key = os.getenv('DEVIN_API_KEY')
    if not api_key:
        raise ValueError("DEVIN_API_KEY environment variable is required")
    return api_key

def get_devin_api_base_url():
    """Get Devin API base URL from environment."""
    return os.getenv('DEVIN_API_BASE_URL', 'https://api.devin.ai/v1')

def get_devin_api_timeout():
    """Get Devin API timeout from environment."""
    return int(os.getenv('DEVIN_API_TIMEOUT', '120'))

def get_devin_api_max_retries():
    """Get Devin API max retries from environment."""
    return int(os.getenv('DEVIN_API_MAX_RETRIES', '3'))
