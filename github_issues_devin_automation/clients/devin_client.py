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

    def wait_for_session_completion(self, session_id: str, timeout: int = 300, poll_interval: int = 5) -> Dict[Any, Any]:
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

    def calculate_confidence_score_with_ai(self, issue: Dict[Any, Any]) -> Tuple[Optional[float], Optional[list], Optional[str], Optional[str]]:
        """
        Calculate confidence score for issue implementation using Devin AI (1-10 scale).
        Higher score = higher confidence (easier to implement)
        
        Args:
            issue: GitHub issue dictionary
            
        Returns:
            Tuple of (score, factors, reasoning, session_id) or (None, None, None, None) if failed
        """
        from rich.console import Console
        
        console = Console()
        console.print(f"[blue]Creating Devin session to analyze issue complexity...[/blue]")

        scoping_prompt = f"""Please analyze and scope this GitHub issue and provide a confidence score for implementation difficulty.

Issue Title: {issue.get('title', '')}
Issue Body: {issue.get('body', '') or 'No description provided'}
Labels: {', '.join([label.get('name', '') for label in issue.get('labels', [])])}

Please provide your analysis in this exact format:

CONFIDENCE SCORE: [number from 1-10]
CONFIDENCE LEVEL: [Very Low/Low/Medium/High/Very High]

ANALYSIS FACTORS:
- [Factor 1 explanation]
- [Factor 2 explanation]
- [Factor 3 explanation]

REASONING:
[Brief explanation of the score]

Note:
- Score 1-2: Very complex, architectural changes, poorly defined
- Score 3-4: Complex, requires significant investigation
- Score 5-6: Moderate complexity, some unknowns
- Score 7-8: Well-defined, straightforward implementation
- Score 9-10: Simple fixes, documentation changes

Do NOT create any pull requests or implement solutions. This is only for scoping and analysis."""

        try:
            session = self.create_session(scoping_prompt)
            session_id = session['session_id']

            console.print(f"[green]Created scoping session: {session_id}[/green]")
            console.print(f"[dim]Session URL: {session['url']}[/dim]")

            completed_session = self.wait_for_session_completion(session_id)

            score, factors, reasoning = self._extract_confidence_from_session(completed_session)

            return score, factors, reasoning, session_id

        except Exception as e:
            console.print(f"[red]Error during AI analysis: {e}[/red]")
            return None, None, None, None

    def _extract_confidence_from_session(self, session: Dict[Any, Any]) -> Tuple[Optional[float], list, str]:
        """Extract confidence score and analysis from completed Devin session"""
        messages = session.get('messages', [])

        for message in reversed(messages):
            if message.get('type') == 'devin_message':
                content = message.get('message', '')

                score = self._parse_confidence_score(content)
                factors = self._parse_analysis_factors(content)
                reasoning = self._parse_reasoning(content)

                if score is not None:
                    return score, factors, reasoning

        return None, ["AI analysis completed but score parsing failed"], "Unable to parse Devin's response"

    def _parse_confidence_score(self, content: str) -> Optional[float]:
        """Parse confidence score from Devin's response"""
        score_match = re.search(r'CONFIDENCE SCORE:\s*(\d+(?:\.\d+)?)', content, re.IGNORECASE)
        if score_match:
            try:
                score = float(score_match.group(1))
                return max(1.0, min(10.0, score))
            except ValueError:
                pass

        return None

    def _parse_analysis_factors(self, content: str) -> list:
        """Parse analysis factors from Devin's response"""
        factors = []

        factors_match = re.search(r'ANALYSIS FACTORS:(.*?)(?:REASONING:|$)', content, re.IGNORECASE | re.DOTALL)
        if factors_match:
            factors_text = factors_match.group(1)
            factor_lines = re.findall(r'-\s*(.+)', factors_text)
            factors = [factor.strip() for factor in factor_lines if factor.strip()]

        return factors if factors else ["AI analysis factors not parsed"]

    def _parse_reasoning(self, content: str) -> str:
        """Parse reasoning from Devin's response"""
        reasoning_match = re.search(r'REASONING:\s*(.*?)$', content, re.IGNORECASE | re.DOTALL)
        if reasoning_match:
            return reasoning_match.group(1).strip()

        return "AI reasoning not parsed"
