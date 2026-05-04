from __future__ import annotations


TABS = [
    ("overview", "대시보드"),
    ("research-funnel", "후보/정보"),
    ("buy-review", "매수검토"),
    ("portfolio", "포트폴리오"),
    ("research-notes", "리서치"),
    ("journal", "기록"),
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
            "research-funnel",
            "research-funnel",
            "research-funnel",
            "overview",
            "portfolio",
            "research-notes",
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
