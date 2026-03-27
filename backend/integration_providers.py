"""Integration provider abstraction.

This module defines a pluggable provider system for syncing transactions from
external services.

Each provider is responsible for fetching transactions from its service, and
returning a list of dicts containing transaction data.

For real integrations, implement the provider logic inside the matching class
(e.g. PhonePeProvider), or configure the integration record to point at a
real API endpoint.

The built-in implementation includes a minimal "HTTP URL" provider that treats
`integration.api_key` as an HTTP URL returning JSON in one of the following forms:
- An array of transaction objects
- An object containing a `transactions` array

If you want to integrate with a real service, implement the provider and/or
set the integration's api_key to the correct URL.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from models import Integration, User

logger = logging.getLogger("integration_providers")


class IntegrationProvider:
    """Base integration provider."""

    def __init__(self, integration: Integration, user: User):
        self.integration = integration
        self.user = user

    def fetch_transactions(self) -> List[Dict]:
        """Fetch transactions for this integration.

        Must return a list of dicts containing at least:
          - type ("income" or "expense")
          - description
          - amount
          - category
          - date (ISO string)

        The backend will map these fields into Transaction records.
        """
        raise NotImplementedError()


class HttpUrlProvider(IntegrationProvider):
    """Fetch transaction data from a configured HTTP URL.

    The integration.api_key is treated as the URL to fetch.

    Expected response formats:
      - JSON array of transaction objects
      - { "transactions": [...] }

    This is useful as a lightweight way to plug in real APIs without writing
    provider-specific code.
    """

    def fetch_transactions(self) -> List[Dict]:
        url = (self.integration.api_key or "").strip()
        if not url or not url.lower().startswith("http"):
            raise ValueError("Invalid URL configured for integration")

        req = Request(url, headers={"User-Agent": "FinApp/1.0"})
        try:
            with urlopen(req, timeout=15) as resp:
                body = resp.read().decode("utf-8")
                data = json.loads(body)
        except HTTPError as e:
            raise RuntimeError(f"HTTP error {e.code}: {e.reason}")
        except URLError as e:
            raise RuntimeError(f"URL error: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to fetch integration data: {e}")

        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "transactions" in data and isinstance(data["transactions"], list):
            return data["transactions"]

        raise RuntimeError("Unexpected response format from integration endpoint")


class SampleDataProvider(IntegrationProvider):
    """Fallback provider that returns sample transactions."""

    SAMPLE_DATA = {
        "phonepe": [
            {"description": "UPI to Swiggy", "amount": 450, "category": "Food", "type": "expense", "date": datetime.now(timezone.utc).isoformat()},
            {"description": "DTH Recharge", "amount": 299, "category": "Bills", "type": "expense", "date": datetime.now(timezone.utc).isoformat()},
        ],
        "groww": [
            {"description": "Mutual Fund SIP", "amount": 5000, "category": "Investment", "type": "expense", "date": datetime.now(timezone.utc).isoformat()},
        ],
        "paytm": [
            {"description": "Electricity Bill", "amount": 1200, "category": "Bills", "type": "expense", "date": datetime.now(timezone.utc).isoformat()},
        ],
        "gpay": [
            {"description": "Grocery UPI", "amount": 860, "category": "Food", "type": "expense", "date": datetime.now(timezone.utc).isoformat()},
        ],
        "cred": [
            {"description": "Credit card payment", "amount": 4500, "category": "Bills", "type": "expense", "date": datetime.now(timezone.utc).isoformat()},
        ],
        "zerodha": [
            {"description": "Stock purchase", "amount": 15000, "category": "Investment", "type": "expense", "date": datetime.now(timezone.utc).isoformat()},
        ],
        "hdfc": [
            {"description": "Salary Credit", "amount": 75000, "category": "Income", "type": "income", "date": datetime.now(timezone.utc).isoformat()},
            {"description": "Grocery Shopping", "amount": 4200, "category": "Food", "type": "expense", "date": datetime.now(timezone.utc).isoformat()},
        ],
        "sbi": [
            {"description": "Utility Bill", "amount": 2200, "category": "Bills", "type": "expense", "date": datetime.now(timezone.utc).isoformat()},
            {"description": "Interest Credit", "amount": 120, "category": "Income", "type": "income", "date": datetime.now(timezone.utc).isoformat()},
        ],
        "icici": [
            {"description": "Online Shopping", "amount": 3800, "category": "Shopping", "type": "expense", "date": datetime.now(timezone.utc).isoformat()},
            {"description": "Cashback", "amount": 250, "category": "Income", "type": "income", "date": datetime.now(timezone.utc).isoformat()},
        ],
    }

    def fetch_transactions(self) -> List[Dict]:
        return self.SAMPLE_DATA.get(self.integration.app_name, [])


# Provider registry
PROVIDERS = {
    "phonepe": HttpUrlProvider,
    "groww": HttpUrlProvider,
    "paytm": HttpUrlProvider,
    "gpay": HttpUrlProvider,
    "cred": HttpUrlProvider,
    "zerodha": HttpUrlProvider,
    "hdfc": HttpUrlProvider,
    "sbi": HttpUrlProvider,
    "icici": HttpUrlProvider,
}


def get_provider(integration: Integration, user: User) -> IntegrationProvider:
    """Return a provider instance for the given integration."""
    provider_cls = PROVIDERS.get(integration.app_name, SampleDataProvider)
    return provider_cls(integration, user)
