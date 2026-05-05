from __future__ import annotations


TABS = [
    ("overview", "1 오늘 순서"),
    ("data-check", "2 정보 확인"),
    ("candidate", "3 후보 고르기"),
    ("buy-review", "4 매수 전 점검"),
    ("portfolio", "5 내 계좌"),
    ("journal", "6 기록/복기"),
    ("settings", "설정"),
]


def render_tab_nav() -> str:
    buttons = []
    for idx, (tab_id, label) in enumerate(TABS):
        selected = "true" if idx == 0 else "false"
        active = " active" if idx == 0 else ""
        buttons.append(
            f'<button type="button" class="tab-button{active}" data-tab-target="{tab_id}" aria-selected="{selected}">{label}</button>'
        )
    return f'<nav class="tab-nav" aria-label="기능 탭">{"".join(buttons)}</nav>'


def render_tab_script() -> str:
    tab_ids = ", ".join(f'"{tab_id}"' for tab_id, _ in TABS)
    section_tabs = ", ".join(
        f'"{tab_id}"'
        for tab_id in [
            "overview",
            "overview",
            "overview",
            "data-check",
            "candidate",
            "data-check",
            "settings",
            "data-check",
            "portfolio",
            "buy-review",
            "buy-review",
            "portfolio",
            "journal",
            "journal",
        ]
    )
    return f"""<script>
(() => {{
  const knownTabs = new Set([{tab_ids}]);
  const sectionTabs = [{section_tabs}];
  const unassignedSections = Array.from(document.querySelectorAll("main > section")).filter((section) => !section.dataset.tabPanel);
  unassignedSections.forEach((section, index) => {{
    const tabId = sectionTabs[index] || "overview";
    section.dataset.tabPanel = tabId;
    section.classList.add("tab-panel");
    if (tabId !== "overview") {{
      section.hidden = true;
    }}
  }});
  const buttons = Array.from(document.querySelectorAll("[data-tab-target]"));
  const panels = Array.from(document.querySelectorAll("[data-tab-panel]"));
  const setActive = (tabId) => {{
    const safeTabId = knownTabs.has(tabId) ? tabId : "overview";
    buttons.forEach((button) => {{
      const active = button.dataset.tabTarget === safeTabId;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", active ? "true" : "false");
    }});
    panels.forEach((panel) => {{
      panel.hidden = panel.dataset.tabPanel !== safeTabId;
    }});
    window.localStorage.setItem("sef-active-tab", safeTabId);
  }};
  buttons.forEach((button) => button.addEventListener("click", () => setActive(button.dataset.tabTarget)));
  setActive(window.localStorage.getItem("sef-active-tab") || "overview");
}})();
</script>"""
