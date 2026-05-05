CSS = """
:root { color-scheme: light; font-family: Arial, sans-serif; background: #f4f6f8; color: #111827; }
* { box-sizing: border-box; }
body { margin: 0; }
header { background: #111827; color: white; padding: 24px; }
header h1 { margin: 0 0 8px; font-size: 28px; letter-spacing: 0; }
header h1 span { display: block; margin-top: 4px; color: #9ca3af; font-size: 14px; font-weight: 600; }
header p { margin: 0; color: #d1d5db; line-height: 1.55; max-width: 920px; }
main { padding: 20px; max-width: 1280px; margin: 0 auto; }
section, .grid > div { background: white; border: 1px solid #d9dee7; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
h2 { margin: 0 0 12px; font-size: 18px; }
.beginner-guide h2, .tab-intro h2 { margin-bottom: 10px; }
.beginner-guide ol { margin: 0; padding-left: 22px; display: grid; gap: 10px; }
.beginner-guide li { color: #111827; line-height: 1.45; }
.beginner-guide li span { display: block; color: #4b5563; font-size: 13px; margin-top: 2px; }
.tab-intro { border: 1px solid #bfdbfe; background: #eff6ff; color: #1e3a8a; border-radius: 8px; padding: 12px; margin-bottom: 14px; }
.tab-intro p { margin: 0 0 6px; line-height: 1.5; font-size: 13px; }
.tab-intro p:last-child { margin-bottom: 0; }
.tab-nav { position: sticky; top: 0; z-index: 20; display: flex; gap: 8px; overflow-x: auto; background: #f4f6f8; border-bottom: 1px solid #d9dee7; padding: 8px 0 12px; margin-bottom: 14px; }
.tab-button { flex: 0 0 auto; min-height: 36px; border: 1px solid #cbd5e1; border-radius: 999px; background: white; color: #374151; padding: 0 14px; font-weight: 700; cursor: pointer; }
.tab-button.active { border-color: #2563eb; background: #2563eb; color: white; }
.tab-panel[hidden] { display: none; }
.metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; background: transparent; border: 0; padding: 0; }
.metric { background: white; border: 1px solid #d9dee7; border-radius: 8px; padding: 14px; min-height: 80px; }
.metric span { display: block; color: #6b7280; font-size: 13px; margin-bottom: 8px; }
.metric strong { font-size: 20px; line-height: 1.25; overflow-wrap: anywhere; }
.grid { display: grid; gap: 16px; }
.grid.two { grid-template-columns: minmax(0, 1.15fr) minmax(360px, .85fr); }
.grid.three { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.score-layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(240px, .8fr); gap: 14px; align-items: start; }
.score-guide { border: 1px solid #d9dee7; background: #f9fafb; border-radius: 8px; padding: 12px; }
.score-guide.compact { margin-top: 12px; }
.score-guide h3 { margin: 0 0 10px; font-size: 15px; }
.guide-block { margin-bottom: 10px; }
.guide-block strong { display: block; margin-bottom: 5px; font-size: 13px; color: #1f2937; }
.score-guide ul { margin: 0; padding-left: 18px; color: #374151; font-size: 12px; line-height: 1.45; }
.score-guide p { margin: 10px 0 0; color: #4b5563; font-size: 12px; line-height: 1.45; }
.advanced-panel { border: 1px solid #d9dee7; border-radius: 8px; background: #f9fafb; padding: 12px; }
.advanced-panel summary { cursor: pointer; font-weight: 700; color: #1f2937; }
.advanced-panel .grid { margin-top: 12px; }
.rule-context { display: grid; grid-template-columns: 1fr 1fr 1.25fr; gap: 14px; }
.rule-context h3 { margin: 0 0 8px; font-size: 15px; }
.rule-context ol { margin: 0; padding-left: 20px; color: #374151; font-size: 13px; line-height: 1.55; }
.rule-reference table td:first-child { width: 190px; font-weight: 700; color: #1f2937; }
.recent-info { display: grid; grid-template-columns: .7fr .9fr 1.2fr 1.2fr; gap: 14px; }
.recent-info h3 { margin: 0 0 8px; font-size: 15px; }
.recent-info p { margin: 10px 0 0; color: #4b5563; font-size: 13px; line-height: 1.5; }
.data-status { display: grid; grid-template-columns: 1.15fr .85fr; gap: 14px; }
.data-status h3 { margin: 0 0 8px; font-size: 15px; }
.account-panel { display: grid; grid-template-columns: .75fr .9fr 1.35fr; gap: 14px; }
.account-panel p { margin: 10px 0 0; color: #4b5563; font-size: 13px; line-height: 1.5; }
.button-row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.news-list { margin: 0; padding-left: 18px; display: grid; gap: 8px; font-size: 13px; line-height: 1.45; }
.news-list a { color: #1d4ed8; text-decoration: none; }
.news-list span { display: block; color: #6b7280; font-size: 12px; margin-top: 2px; }
.news-list .news-flags { color: #92400e; font-weight: 700; }
.result-note { margin-top: 10px; border: 1px solid #bfdbfe; background: #eff6ff; color: #1e3a8a; border-radius: 8px; padding: 12px; line-height: 1.5; font-size: 13px; }
.candidate-details { margin-top: 16px; }
.candidate-group { margin-bottom: 16px; }
.candidate-group h4 { margin: 0 0 6px; color: #111827; font-size: 15px; }
.candidate-group h4 span { color: #6b7280; font-size: 12px; font-weight: 600; }
.candidate-card { border: 1px solid #d9dee7; border-radius: 8px; background: #f9fafb; padding: 12px; margin-top: 10px; }
.candidate-card summary { cursor: pointer; display: flex; gap: 10px; align-items: center; justify-content: space-between; }
.candidate-card summary span { color: #4b5563; font-size: 12px; }
.candidate-card-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }
.factor-box { border: 1px solid #e5e7eb; background: white; border-radius: 8px; padding: 10px; }
.factor-box > b { display: block; margin-bottom: 8px; color: #1f2937; font-size: 13px; }
.factor-box ul { margin: 0; padding-left: 18px; color: #374151; font-size: 13px; line-height: 1.45; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { text-align: left; border-bottom: 1px solid #e5e7eb; padding: 9px 8px; vertical-align: top; }
th { color: #4b5563; font-weight: 700; background: #f9fafb; }
tr.candidate-test td { background: #f3f4f6; color: #6b7280; }
.status-badge { display: inline-block; border-radius: 999px; padding: 2px 8px; background: #e0f2fe; color: #075985; font-size: 12px; font-weight: 700; }
.status-badge.test { background: #e5e7eb; color: #4b5563; }
form { display: grid; gap: 10px; }
label { display: grid; gap: 5px; color: #374151; font-size: 13px; }
input, select, textarea { width: 100%; min-height: 36px; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 9px; font: inherit; }
textarea { min-height: 72px; resize: vertical; }
button { min-height: 38px; border: 0; border-radius: 6px; background: #2563eb; color: white; font-weight: 700; cursor: pointer; }
.tab-button { flex: 0 0 auto; min-height: 36px; border: 1px solid #cbd5e1; border-radius: 999px; background: white; color: #374151; padding: 0 14px; font-weight: 700; cursor: pointer; }
.tab-button.active { border-color: #2563eb; background: #2563eb; color: white; }
.form-note { margin: -2px 0 0; color: #6b7280; font-size: 12px; line-height: 1.45; }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.notice { background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; border-radius: 8px; padding: 12px 14px; margin-bottom: 16px; }
.empty { color: #6b7280; margin: 0; }
pre { white-space: pre-wrap; background: #0f172a; color: #e5e7eb; padding: 14px; border-radius: 8px; overflow-x: auto; line-height: 1.5; }
@media (max-width: 900px) {
  main { padding: 12px; }
  .metrics, .grid.two, .grid.three, .score-layout, .rule-context, .recent-info, .data-status, .account-panel, .candidate-card-grid { grid-template-columns: 1fr; }
}
"""
