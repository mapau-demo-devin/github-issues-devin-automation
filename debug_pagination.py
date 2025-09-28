#!/usr/bin/env python3
"""
Debug script to investigate GitHub API pagination issue.
"""

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from github_issues_devin_automation.clients.github_client import GitHubClient

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_pagination_issue():
    """Test the pagination issue with a repository that has few issues."""
    client = GitHubClient()
    
    test_repo = "mapau-demo-devin/running-buddy"
    
    print(f"\n=== Testing pagination with repository: {test_repo} ===")
    
    try:
        print(f"\n--- Test 1: Requesting 11 issues ---")
        issues = client.list_issues(test_repo, limit=11)
        print(f"Requested 11 issues, got {len(issues)} issues")
        
        print(f"\n--- Test 2: Testing has_many_issues with threshold=10 ---")
        has_many = client.has_many_issues(test_repo, threshold=10)
        print(f"has_many_issues(threshold=10) returned: {has_many}")
        
        print(f"\n--- Test 3: Getting actual issue count ---")
        all_issues = client.list_issues(test_repo, limit=100)
        print(f"Total issues in repository: {len(all_issues)}")
        
        print(f"\n--- Test 4: Analyzing returned items ---")
        for i, issue in enumerate(issues[:5]):
            is_pr = 'pull_request' in issue
            print(f"Issue #{issue.get('number')}: Title='{issue.get('title', '')[:50]}...', Is PR: {is_pr}")
        
        return len(issues), has_many, len(all_issues)
        
    except Exception as e:
        print(f"Error testing with {test_repo}: {e}")
        print("Trying with a public repository that likely has issues...")
        
        test_repo = "octocat/Hello-World"
        print(f"Switching to repository: {test_repo}")
        
        try:
            print(f"\n--- Test 1: Requesting 11 issues ---")
            issues = client.list_issues(test_repo, limit=11)
            print(f"Requested 11 issues, got {len(issues)} issues")
            
            print(f"\n--- Test 2: Testing has_many_issues with threshold=10 ---")
            has_many = client.has_many_issues(test_repo, threshold=10)
            print(f"has_many_issues(threshold=10) returned: {has_many}")
            
            print(f"\n--- Test 3: Getting actual issue count ---")
            all_issues = client.list_issues(test_repo, limit=100)
            print(f"Total issues in repository: {len(all_issues)}")
            
            print(f"\n--- Test 4: Analyzing returned items ---")
            for i, issue in enumerate(issues[:5]):
                is_pr = 'pull_request' in issue
                print(f"Issue #{issue.get('number')}: Title='{issue.get('title', '')[:50]}...', Is PR: {is_pr}")
            
            return len(issues), has_many, len(all_issues)
            
        except Exception as e2:
            print(f"Error with public repository: {e2}")
            return None, None, None

if __name__ == "__main__":
    test_pagination_issue()
