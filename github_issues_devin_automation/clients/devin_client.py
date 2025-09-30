"""
Devin API client for creating and managing Devin sessions.
"""

import requests
import time
import re
from typing import Dict, Any, Tuple, Optional
from ..config.settings import get_devin_api_key, get_devin_api_base_url, get_devin_api_timeout, get_devin_api_max_retries

class DevinClient:
    def __init__(self):
        self.api_key = get_devin_api_key()
        self.base_url = get_devin_api_base_url()
        self.timeout = get_devin_api_timeout()
        self.max_retries = get_devin_api_max_retries()
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

        return self._make_request_with_retry('POST', url, json=data)

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

        self._make_request_with_retry('POST', url, json=data)

    def get_session(self, session_id: str) -> Dict[Any, Any]:
        """
        Get details about an existing session.

        Args:
            session_id: ID of the session to retrieve

        Returns:
            Session details dictionary
        """
        url = f"{self.base_url}/sessions/{session_id}"

        return self._make_request_with_retry('GET', url)

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

        return self._make_request_with_retry('GET', url, params=params)

    def _make_request_with_retry(self, method: str, url: str, **kwargs) -> Dict[Any, Any]:
        """
        Make HTTP request with retry logic and proper timeout handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional request parameters

        Returns:
            Response JSON data

        Raises:
            requests.exceptions.RequestException: If all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    timeout=self.timeout,
                    **kwargs
                )
                response.raise_for_status()

                if method == 'POST' and 'message' in url:
                    return None

                return response.json()

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"Request failed (attempt {attempt + 1}/{self.max_retries}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise requests.exceptions.RequestException(
                        f"Request failed after {self.max_retries} attempts. Last error: {str(e)}"
                    ) from e
            except requests.exceptions.HTTPError as e:
                raise e

        if last_exception:
            raise last_exception

    def wait_for_session_completion(self, session_id: str, timeout: int = 600, poll_interval: int = 5) -> Dict[Any, Any]:
        """
        Poll a session until it completes or times out.

        Args:
            session_id: ID of the session to monitor
            timeout: Maximum time to wait in seconds (default: 5 minutes)
            poll_interval: Time between polls in seconds (default: 5 seconds)

        Returns:
            Final session details dictionary

        Raises:
            TimeoutError: If session doesn't complete within timeout
            requests.exceptions.RequestException: If API calls fail
        """
        from rich.console import Console
        from rich.live import Live
        from rich.spinner import Spinner

        console = Console()
        start_time = time.time()

        with Live(Spinner("dots", text="Waiting for Devin to complete analysis..."), console=console, refresh_per_second=4) as live:
            while time.time() - start_time < timeout:
                try:
                    session = self.get_session(session_id)
                    status = session.get('status_enum', session.get('status', 'unknown'))

                    if status in ['finished', 'blocked', 'expired']:
                        live.stop()
                        return session
                    elif status in ['working']:
                        live.update(Spinner("dots", text=f"Devin is {status}..."))

                    time.sleep(poll_interval)

                except Exception as e:
                    live.stop()
                    raise e

            live.stop()
            raise TimeoutError(f"Session {session_id} did not complete within {timeout} seconds")

    def calculate_confidence_score_with_ai(self, issue: Dict[Any, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Scope GitHub issue using Devin AI and extract confidence level.
        
        Args:
            issue: GitHub issue dictionary
            
        Returns:
            Tuple of (confidence_level, full_analysis, session_id) or (None, None, None) if failed
        """
        from rich.console import Console
        
        console = Console()
        console.print(f"[blue]Creating Devin session to scope issue...[/blue]")

        scoping_prompt = f"""Please provide a quick scoping assessment for this GitHub issue and update the structured output immediately with your findings.

Issue Title: {issue.get('title', '')}
Issue Body: {issue.get('body', '') or 'No description provided'}
Labels: {', '.join([label.get('name', '') for label in issue.get('labels', [])])}

Please update the structured output in this exact JSON format as soon as you determine your confidence:
{{
  "confidence": "High|Medium|Low",
  "analysis": "Brief 2-3 sentence analysis covering scope and complexity"
}}

Please respond with:
1. Confidence: [High/Medium/Low] - your confidence in implementing this
2. Brief analysis (2-3 sentences) covering scope and complexity

**IMPORTANT: Update the structured output immediately when you determine your confidence level.**

Keep your response concise and focused. Do NOT create pull requests or implement solutions."""

        try:
            session = self.create_session(scoping_prompt)
            session_id = session['session_id']

            console.print(f"[green]Created scoping session: {session_id}[/green]")
            console.print(f"[dim]Session URL: {session['url']}[/dim]")

            console.print(f"[blue]Waiting for Devin to assign a confidence score...[/blue]")
            confidence_level = self._extract_initial_confidence(session_id)
            if confidence_level:
                console.print(f"[yellow]Initial Assessment: {confidence_level}[/yellow]")
            
            console.print(f"[blue]Waiting for Devin to complete issue scoping...[/blue]")
            completed_session = self.wait_for_session_completion(session_id)
            full_analysis = self._extract_full_analysis(completed_session)

            return confidence_level, full_analysis, session_id

        except Exception as e:
            console.print(f"[red]Error during AI analysis: {e}[/red]")
            return None, None, None

    def _extract_initial_confidence(self, session_id: str) -> Optional[str]:
        """Extract confidence level from structured output (immediate) with fallback to session title"""
        try:
            import time
            max_attempts = 12  # 3 minutes with 15-second intervals (recommended by API docs)
            
            for attempt in range(max_attempts):
                session = self.get_session(session_id)
                status = session.get('status_enum', session.get('status', 'unknown'))
                
                structured_output = session.get('structured_output', {})
                if structured_output and 'confidence' in structured_output:
                    confidence = structured_output['confidence']
                    if confidence in ['High', 'Medium', 'Low']:
                        return confidence
                
                title = session.get('title', '')
                if title:
                    confidence_match = re.search(r'Confidence:\s*(High|Medium|Low)', title, re.IGNORECASE)
                    if confidence_match:
                        return confidence_match.group(1).capitalize()
                
                if status in ['finished', 'blocked', 'expired']:
                    break
                
                time.sleep(15)  # Use recommended 15-second intervals
            
            return None
            
        except Exception:
            return None

    def _extract_full_analysis(self, session: Dict[Any, Any]) -> str:
        """Extract the full analysis from structured output or completed Devin session"""
        structured_output = session.get('structured_output', {})
        if structured_output and 'analysis' in structured_output:
            analysis = structured_output['analysis']
            if analysis and analysis.strip():
                return analysis
        
        messages = session.get('messages', [])
        for message in reversed(messages):
            if message.get('type') == 'devin_message':
                content = message.get('message', '')
                if content.strip():
                    return content

        return "Unable to extract analysis from Devin's response"
