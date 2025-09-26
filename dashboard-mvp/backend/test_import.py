import sys
import os
sys.path.append('.')
sys.path.append('./app')

try:
    from app.github_client import GitHubClient
    print("GitHubClient import successful")
except ImportError as e:
    print(f"GitHubClient import failed: {e}")

try:
    from app.devin_client import DevinClient
    print("DevinClient import successful")
except ImportError as e:
    print(f"DevinClient import failed: {e}")
