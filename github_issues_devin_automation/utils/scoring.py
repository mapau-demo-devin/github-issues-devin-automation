"""
Confidence scoring utilities for issue implementation assessment.
"""

import re


def calculate_confidence_score(issue, repo_info=None):
    """
    Calculate confidence score for issue implementation (1-10 scale).
    Higher score = higher confidence (easier to implement)
    """
    score = 5.0
    factors = []
    
    title = issue.get('title', '').lower()
    body = issue.get('body', '') or ''
    body_lower = body.lower()
    
    if any(word in title for word in ['fix', 'bug', 'error', 'broken']):
        score += 1.5
        factors.append("Bug fix (typically well-defined)")
    elif any(word in title for word in ['add', 'implement', 'create']):
        score += 0.5
        factors.append("Feature addition")
    elif any(word in title for word in ['refactor', 'improve', 'optimize']):
        score -= 0.5
        factors.append("Refactoring (may require broader changes)")
    
    complex_keywords = ['architecture', 'design', 'framework', 'migration', 'breaking change']
    if any(keyword in title or keyword in body_lower for keyword in complex_keywords):
        score -= 2.0
        factors.append("Complex architectural changes detected")
    
    simple_keywords = ['typo', 'spelling', 'documentation', 'readme', 'comment']
    if any(keyword in title or keyword in body_lower for keyword in simple_keywords):
        score += 2.0
        factors.append("Simple documentation/text changes")
    
    if 'magic number' in title or 'constant' in title:
        score += 1.5
        factors.append("Code cleanup - extracting constants")
    
    if len(body) > 500:
        score += 1.0
        factors.append("Detailed description provided")
    elif len(body) < 100:
        score -= 1.0
        factors.append("Limited description - may need clarification")
    
    if '```' in body or 'code' in body_lower:
        score += 0.5
        factors.append("Code examples provided")
    
    if re.search(r'\d+\.|\-\s|\*\s', body):
        score += 0.5
        factors.append("Clear steps or requirements listed")
    
    labels = issue.get('labels', [])
    label_names = [label.get('name', '').lower() for label in labels]
    
    if 'good first issue' in label_names or 'beginner' in label_names:
        score += 1.5
        factors.append("Marked as beginner-friendly")
    elif 'help wanted' in label_names:
        score += 0.5
        factors.append("Community contribution welcome")
    
    if 'bug' in label_names:
        score += 1.0
        factors.append("Confirmed bug report")
    elif 'enhancement' in label_names:
        score += 0.5
        factors.append("Feature enhancement")
    
    score = max(1.0, min(10.0, score))
    
    return round(score, 1), factors


def explain_confidence_score(score, factors):
    """Generate explanation for the confidence score"""
    if score >= 8.0:
        level = "Very High"
        color = "bright_green"
        description = "This issue appears straightforward to implement with clear requirements."
    elif score >= 6.0:
        level = "High"
        color = "green"
        description = "This issue has good clarity and should be manageable to implement."
    elif score >= 4.0:
        level = "Medium"
        color = "yellow"
        description = "This issue may require some investigation or have moderate complexity."
    elif score >= 2.0:
        level = "Low"
        color = "orange"
        description = "This issue appears complex or lacks sufficient detail."
    else:
        level = "Very Low"
        color = "red"
        description = "This issue is likely very complex or poorly defined."
    
    return level, color, description
