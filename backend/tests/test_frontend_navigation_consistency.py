from pathlib import Path
import re


def _extract_marked_items(block: str, marker: str) -> list[str]:
    items = []
    for line in block.splitlines():
        if marker not in line:
            continue
        token = line.split(marker, 1)[1].split('"', 1)[0]
        items.append(token)
    return items


def _extract_quick_actions(html: str) -> list[str]:
    return re.findall(r'class="[^"]*quick-tab[^"]*"[^\n>]*data-action="([^"]+)"', html)


def _extract_menu_actions(html: str) -> list[str]:
    return re.findall(r'class="[^"]*tab-menu-item[^"]*"[^\n>]*data-action="([^"]+)"', html)


def _extract_quick_tabs(html: str) -> list[str]:
    return re.findall(r'class="[^"]*quick-tab[^"]*"[^\n>]*data-tab="([^"]+)"', html)


def _extract_menu_tabs(html: str) -> list[str]:
    return re.findall(r'class="[^"]*tab-menu-item[^"]*"[^\n>]*data-tab="([^"]+)"', html)


def test_dashboard_action_shortcuts_exist_in_quick_tabs_and_menu():
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

    quick_actions = _extract_quick_actions(html)
    menu_actions = _extract_menu_actions(html)

    for action in required_actions:
        assert action in quick_actions, f"Missing quick-tab action: {action}"
        assert action in menu_actions, f"Missing dropdown action: {action}"


def test_shared_tab_order_matches_between_quick_tabs_and_dropdown():
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

    quick_tabs = _extract_quick_tabs(html)
    menu_tabs = _extract_menu_tabs(html)

    quick_filtered = [tab for tab in quick_tabs if tab in expected_shared_tab_order]
    menu_filtered = [tab for tab in menu_tabs if tab in expected_shared_tab_order]

    assert quick_filtered == expected_shared_tab_order
    assert menu_filtered == expected_shared_tab_order
