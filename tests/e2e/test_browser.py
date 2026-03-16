"""
End-to-end browser tests using Playwright.
Run: pytest tests/e2e -v
Optional: BASE_URL=http://localhost:5000 pytest tests/e2e  (use existing server)
"""

import pytest


def test_homepage_loads(page, base_url):
    """Homepage loads and shows expected content."""
    page.goto("/")
    assert base_url in page.url and (page.url == base_url or page.url == base_url + "/")
    assert page.title() == "Turnieje brydżowe"


def test_tournaments_list_empty(page, base_url):
    """With empty data, tournaments list is empty or shows empty state."""
    page.goto("/")
    # If there's a link to list or the list is on homepage
    page.goto("/api/tournaments")
    # API returns JSON; in a real UI you might check for "[]" in body or a table
    content = page.content()
    assert "[]" in content or "tournament" in content.lower()


def test_create_tournament_flow(page, base_url):
    """Create tournament via UI if there is a form, or via API then open page."""
    # Go to homepage and look for "new tournament" or similar
    page.goto("/")
    # Create via API (simplest for E2E: ensure one tournament exists)
    from urllib.request import Request, urlopen
    import json
    payload = {
        "name": "E2E Test Cup",
        "date": "2025-06-01",
        "teams": [
            {"name": "Team A", "member1": "A1", "member2": "A2"},
            {"name": "Team B", "member1": "B1", "member2": "B2"},
        ],
        "num_rounds": 1,
    }
    req = Request(
        f"{base_url}/api/tournaments",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req) as r:
        data = json.loads(r.read().decode())
    tour_id = data["id"]
    # Open tournament page in browser
    page.goto(f"/tournament/{tour_id}")
    assert tour_id in page.url
    # Page should show tournament name or rounds
    content = page.content()
    assert "E2E Test Cup" in content or "Test Cup" in content or tour_id in content
