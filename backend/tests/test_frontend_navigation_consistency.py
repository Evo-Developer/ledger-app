from pathlib import Path
import re


def _extract_quick_access_actions(html: str) -> list[str]:
    return re.findall(r'class="[^"]*quick-access-link[^"]*"[^\n>]*data-action="([^"]+)"', html)


def _extract_quick_access_tabs(html: str) -> list[str]:
    return re.findall(r'class="[^"]*quick-access-link[^"]*"[^\n>]*data-tab="([^"]+)"', html)


def _extract_quick_access_aria_labels(html: str) -> list[str]:
    return re.findall(r'<button class="[^"]*quick-access-link[^"]*"[^>]*aria-label="([^"]+)"', html)


def test_dashboard_action_shortcuts_exist_in_quick_access():
    app_html_path = Path(__file__).resolve().parents[2] / "frontend" / "app.html"
    html = app_html_path.read_text(encoding="utf-8")

    required_actions = [
        "health",
        "balance",
        "networth",
        "emergency",
        "creditCards",
        "tax",
        "forecast",
    ]

    quick_actions = _extract_quick_access_actions(html)

    for action in required_actions:
        assert action in quick_actions, f"Missing quick-access action: {action}"


def test_shared_tab_order_matches_expected_quick_access_order():
    app_html_path = Path(__file__).resolve().parents[2] / "frontend" / "app.html"
    html = app_html_path.read_text(encoding="utf-8")

    expected_shared_tab_order = [
        "expenses",
        "income",
        "budgets",
        "goals",
        "savings",
        "events",
        "investments",
        "retirement",
        "insurance",
        "assets",
        "liabilities",
        "insights",
    ]

    quick_tabs = _extract_quick_access_tabs(html)
    quick_filtered = [tab for tab in quick_tabs if tab in expected_shared_tab_order]

    assert quick_filtered == expected_shared_tab_order


def test_quick_access_collapse_toggle_and_labels_exist():
    app_html_path = Path(__file__).resolve().parents[2] / "frontend" / "app.html"
    html = app_html_path.read_text(encoding="utf-8")

    assert 'id="quickAccessToggleBtn"' in html

    labels = _extract_quick_access_aria_labels(html)
    total_links = len(_extract_quick_access_tabs(html)) + len(_extract_quick_access_actions(html))

    assert len(labels) == total_links


def test_quick_access_main_wraps_sections_and_menu_removed():
    app_html_path = Path(__file__).resolve().parents[2] / "frontend" / "app.html"
    html = app_html_path.read_text(encoding="utf-8")

    quick_access_main_idx = html.index('class="quick-access-main"')
    expenses_idx = html.index('id="expenses-section"')
    transaction_modal_idx = html.index('id="transactionModal"')

    assert quick_access_main_idx < expenses_idx < transaction_modal_idx
    assert 'id="tabMenu"' not in html
