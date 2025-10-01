from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from .github_client import GitHubClient
from .devin_client import DevinClient

app = FastAPI()

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/api/repos/{owner}/{repo}/issues")
async def list_issues(owner: str, repo: str, state: str = 'open', limit: int = 10):
    try:
        github_client = GitHubClient()
        issues = github_client.list_issues(f"{owner}/{repo}", state=state, limit=limit)
        return {"issues": issues}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/repos/{owner}/{repo}/issues/{issue_number}")
async def get_issue(owner: str, repo: str, issue_number: int):
    try:
        github_client = GitHubClient()
        issue = github_client.get_issue(f"{owner}/{repo}", issue_number)
        return issue
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/repos/{owner}/{repo}/issues/{issue_number}/scope")
async def scope_issue(owner: str, repo: str, issue_number: int):
    try:
        github_client = GitHubClient()
        devin_client = DevinClient()
        
        issue = github_client.get_issue(f"{owner}/{repo}", issue_number)
        
        prompt = f"""Analyze this GitHub issue and provide a confidence assessment with scoping analysis.

Issue Title: {issue.get('title', '')}
Issue Body: {issue.get('body', '') or 'No description provided'}
Labels: {', '.join([label.get('name', '') for label in issue.get('labels', [])])}
Repository: {owner}/{repo}
Issue Number: #{issue_number}

Please provide:
1. Confidence Level (High/Medium/Low) for whether Devin can successfully complete this issue
2. Brief scope analysis (2-3 sentences on complexity and approach)
3. Detailed implementation plan if confidence is High or Medium

Do NOT create pull requests or implement solutions yet - just provide the scoping analysis."""
        
        session = devin_client.create_session(prompt)
        
        return {
            "session_id": session['session_id'],
            "session_url": session.get('url', f"https://app.devin.ai/sessions/{session['session_id']}")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/repos/{owner}/{repo}/issues/{issue_number}/complete")
async def complete_issue(owner: str, repo: str, issue_number: int):
    try:
        github_client = GitHubClient()
        devin_client = DevinClient()
        
        issue = github_client.get_issue(f"{owner}/{repo}", issue_number)
        
        prompt = f"""Complete this GitHub issue:

Title: {issue.get('title', '')}
Body: {issue.get('body', '') or 'No description provided'}
Repository: {owner}/{repo}
Issue Number: #{issue_number}

Please implement the requested changes, create a pull request, and ensure all tests pass."""
        
        session = devin_client.create_session(prompt)
        
        return {
            "session_id": session['session_id'],
            "session_url": session.get('url', f"https://app.devin.ai/sessions/{session['session_id']}")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
