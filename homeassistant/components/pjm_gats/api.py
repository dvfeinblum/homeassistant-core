"""PJM GATS API client."""

import json
from pathlib import Path
import re
from typing import Any

from bs4 import BeautifulSoup
import requests
from requests.utils import cookiejar_from_dict, dict_from_cookiejar


class PjmGatsApiError(Exception):
    """Exception for PJM GATS API errors."""


class PjmGatsAuthError(PjmGatsApiError):
    """Authentication error."""


class PjmGatsClient:
    """Client for PJM GATS web portal."""

    BASE = "https://gats.pjm-eis.com"
    LOGIN_URL = f"{BASE}/gats2/login/index"
    LOGIN_POST = f"{BASE}:443/gats2/Login/Save"
    # I'm not sure if this is the sorta thing we should be doing in a component but it's hella useful for local testing so I'll leave in place for now
    COOKIE_FILE = Path(".gats_cookies.json")

    def __init__(self, username: str, password: str) -> None:
        """Initialize the client."""
        self.username = username
        self.password = password
        self.session = requests.Session()
        self._load_cookies()

    def _load_cookies(self) -> None:
        if self.COOKIE_FILE.exists():
            try:
                data = json.loads(self.COOKIE_FILE.read_text(encoding="utf8"))
                self.session.cookies = cookiejar_from_dict(data)
            except json.JSONDecodeError, OSError:
                pass

    def _save_cookies(self) -> None:
        data = dict_from_cookiejar(self.session.cookies)
        self.COOKIE_FILE.write_text(json.dumps(data), encoding="utf8")

    def login(self) -> bool:
        """Authenticate with PJM GATS."""
        # Check if existing cookies still work
        if self._has_valid_session():
            return True

        # GET login page → scrape CSRF token
        resp = self.session.get(self.LOGIN_URL, timeout=30)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        token_input = soup.select_one('input[name="__RequestVerificationToken"]')
        if not token_input:
            raise PjmGatsApiError("CSRF token not found on login page")
        csrf = token_input["value"]

        # POST credentials
        payload = {
            "__RequestVerificationToken": csrf,
            "screenheight": "1080",
            "screenwidth": "1920",
            "loginName": self.username,
            "password": self.password,
        }
        headers = {"X-Request-Verification-Token": str(csrf)}
        resp = self.session.post(
            self.LOGIN_POST,
            data=payload,
            headers=headers,
            timeout=30,
            allow_redirects=False,
        )

        if resp.status_code != 302:
            raise PjmGatsAuthError("Invalid credentials")

        # Follow redirect
        redirect_url = resp.headers["Location"]
        if not redirect_url.startswith("http"):
            redirect_url = self.BASE + redirect_url
        resp = self.session.get(redirect_url, timeout=30, allow_redirects=True)

        # Verify session
        if not any("ASP.NET_SessionId" in c.name for c in self.session.cookies):
            raise PjmGatsAuthError("Session not established")

        # Persist cookies
        self._save_cookies()
        return True

    def _has_valid_session(self) -> bool:
        """Check if loaded cookies work for home page."""
        if not any("ASP.NET_SessionId" in c.name for c in self.session.cookies):
            return False
        try:
            resp = self.session.get(f"{self.BASE}/gats2/Home/Index", timeout=10)
            return resp.ok and "timed out" not in resp.text.lower()
        except requests.RequestException:
            return False

    def get_home_page_data(self) -> dict:
        """Fetch and parse home page for sensor data."""
        if not self._has_valid_session():
            self.login()

        resp = self.session.get(f"{self.BASE}/gats2/Home/Index", timeout=30)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        data: dict[str, Any] = {}

        for table in soup.find_all("table"):
            text = table.get_text(" ", strip=True)

            # Main account summary table
            if "Generation" in text and "MWh" in text and "Account Summary" in text:
                self._parse_account_text(text, data)

            # Asset management table
            if "Asset Management" in text and "Unit ID" in text:
                self._parse_asset_text(text, data)

        return data

    def _parse_account_text(self, text: str, data: dict) -> None:
        """Extract all values from account summary table text."""
        # Generation MWh
        m = re.search(r"Generation\s+(\d+\.\d+)", text)
        if m:
            data["generation_mwh"] = float(m.group(1))

        # Certificate counts
        for label, key in (
            (r"Active\s+(\d+)(?!\.\d)", "certificates_active"),
            (r"CEPS\s+(\d+)", "certificates_ceps"),
            (r"On Bulletin Board\s+(\d+)", "certificates_on_bb"),
            (r"Reserved\s+(\d+)(?!\.\d)", "certificates_reserved"),
            (r"Certificate Total\s+(\d+)", "certificates_total"),
            (r"Active Hourly\s+([\d.]+)", "certificates_active_hourly"),
            (r"CEPS Hourly\s+([\d.]+)", "certificates_ceps_hourly"),
            (r"Reserved Hourly\s+([\d.]+)", "certificates_reserved_hourly"),
        ):
            m = re.search(label, text)
            if m:
                val = m.group(1)
                data[key] = float(val) if "." in val else int(val)

        # Inbox/Outbox
        for prefix, box_key in (("Inbox", "inbox"), ("Outbox", "outbox")):
            if prefix in text:
                for label, key in (
                    (rf"{prefix}Certificates(\d+)", f"{box_key}_certificates"),
                    (rf"{prefix}Generator Transfers(\d+)", f"{box_key}_transfers"),
                ):
                    m = re.search(label, text)
                    if m:
                        data[key] = int(m.group(1))
                if prefix == "Outbox":
                    m = re.search(r"OutboxStanding Orders(\d+)", text)
                    if m:
                        data["outbox_standing_orders"] = int(m.group(1))

    def _parse_asset_text(self, text: str, data: dict) -> None:
        """Extract generator info from asset management table text."""
        m = re.search(r"(NON\d+)\s+(.+?)\s+(ACT|INACT|PEND|RET)", text)
        if m:
            data["generator_id"] = m.group(1)
            data["generator_plant"] = m.group(2).strip()
            data["generator_status"] = m.group(3)
