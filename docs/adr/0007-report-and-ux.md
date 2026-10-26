# ADR 0007: Report and UX

**Status:** Accepted (2026-10-26)

## Context
The report is what residents, HOA boards, inspectors and insurers see. Organizers list "simple image analyzers" and "dashboards as the main feature" as projects to avoid, so the report must read as the **output of a pipeline** (tracking, measurement, rules, agent), not a dashboard or an image description. It must be honest about uncertainty and never read as a certification.

## Decision
- **One canonical JSON report** per scan; the web report and PDF render from it.
- **Every screen shows evidence of the pipeline:** tracked hazards across frames, measured distance ranges, rule citations, or the agent's plan and tool calls. The scan screen shows the stages running; the report opens with the score *and* the evidence behind it.
- **Report order:** score with a plain-language label → "Start here" (top 3 fixes and the projected score after them) → zone map → evidence (annotated frames with masks and distance) → agent trace ("How EmberScan got here") → since last scan → all fixes → findings by rule → full disclaimer in the footer.
- **Disclaimer:** one line under the title plus full text in the footer: flags likely hazards, not an inspection, does not certify safety or compliance.
- **Plain language:** "About 6–9 ft from the chimney · fairly sure, measured with the marker" instead of codes; fix tags "Required / Recommended", "Quick job / Half day / Project", cost bands.
- **Fix tracking:** status (Open, In progress, Fixed – needs rescan, Verified by rescan, Won't fix with a reason), owner, dated notes. Only a rescan sets Verified and changes the score.
- **Visual system:** light theme by default (filming is outdoors; the report doubles as a document), dark optional. Color roles never overlap: one warm-charcoal brand color for actions and navigation; red/amber/green for status only; neutral gray zone bands; an ember-orange flame for the logo only. Mobile: bottom tab bar docked to the edge; community switcher in the top bar.
- **Score:** starts at 100; each failed adopted rule subtracts 10 (all zones), 8 (Zone 1) or 4 (Zone 2); needs-review subtracts half; unfilmed sides cap the score at 80. Labels: ≥90 "In good shape", 75–89 "A few fixes needed", <75 "Needs work".

## Consequences
- The demo and every screenshot carry the "not an image analyzer" message by construction.
- Report and PDF can't drift apart.
