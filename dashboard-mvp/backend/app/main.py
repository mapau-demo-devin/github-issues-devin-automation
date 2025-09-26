from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from typing import List, Dict, Any, Optional

from .github_client import GitHubClient
from .devin_client import DevinClient

load_dotenv()

app = FastAPI(title="GitHub Issues Devin Automation Dashboard")

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class ScopeIssueRequest(BaseModel):
    repo: str
    issue_number: int

class CompleteIssueRequest(BaseModel):
    repo: str
    issue_number: int

class SessionResponse(BaseModel):
    session_id: str
    url: str

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/api/repos/{owner}/{repo}/issues")
async def list_issues(
    owner: str, 
    repo: str, 
    state: str = "open", 
    limit: int = 10
):
    """List GitHub issues from a repository"""
    try:
        github_client = GitHubClient()
        repo_path = f"{owner}/{repo}"
        issues = github_client.list_issues(repo_path, state=state, limit=limit)
        return {"issues": issues}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/repos/{owner}/{repo}/issues/{issue_number}")
async def get_issue(owner: str, repo: str, issue_number: int):
    """Get a specific GitHub issue"""
    try:
        github_client = GitHubClient()
        repo_path = f"{owner}/{repo}"
        issue = github_client.get_issue(repo_path, issue_number)
        return issue
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/repos/{owner}/{repo}/issues/{issue_number}/scope")
async def scope_issue(owner: str, repo: str, issue_number: int):
    """Scope an issue using Devin AI"""
    try:
        github_client = GitHubClient()
        devin_client = DevinClient()
        repo_path = f"{owner}/{repo}"
        
        issue = github_client.get_issue(repo_path, issue_number)
        
        prompt = f"""
        Please analyze this GitHub issue and provide:
        1. A detailed scope analysis
        2. A confidence score (1-10) for implementation difficulty
        3. Estimated time to complete
        4. Key technical considerations
        
        Issue: {issue['title']}
        Description: {issue['body']}
        Repository: {repo_path}
        """
        
        session = devin_client.create_session(prompt)
        
        return {
            "session_id": session['session_id'],
            "url": session['url'],
            "issue": issue
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/repos/{owner}/{repo}/issues/{issue_number}/complete")
async def complete_issue(owner: str, repo: str, issue_number: int):
    """Complete an issue using Devin AI"""
    try:
        github_client = GitHubClient()
        devin_client = DevinClient()
        repo_path = f"{owner}/{repo}"
        
        issue = github_client.get_issue(repo_path, issue_number)
        
        prompt = f"""
        Please implement a solution for this GitHub issue:
        
        Issue: {issue['title']}
        Description: {issue['body']}
        Repository: {repo_path}
        
        Steps:
        1. Clone the repository
        2. Analyze the codebase
        3. Implement the requested feature/fix
        4. Create tests if appropriate
        5. Create a pull request
        """
        
        session = devin_client.create_session(prompt)
        
        return {
            "session_id": session['session_id'],
            "url": session['url'],
            "issue": issue
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions")
async def list_sessions(limit: int = 10):
    """List recent Devin sessions"""
    try:
        devin_client = DevinClient()
        sessions = devin_client.list_sessions(limit=limit)
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get details about a specific Devin session"""
    try:
        devin_client = DevinClient()
        session = devin_client.get_session(session_id)
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
