# Accessibility testing

ADME Dialog Agent combines automated checks with a short manual review. The
automation is a regression guard, not an accessibility certification.

## Automated checks

Run the focused suite with:

```bash
cd frontend
npm run test:a11y
```

The Playwright suite runs on desktop and mobile Chromium. It scans `/single`,
`/batch`, and `/about`, then exercises the Assistant evidence/source card,
stream completion status, structure confirmation, and provider-error state.
It uses axe rules tagged for WCAG 2 A/AA and WCAG 2.1 A/AA and fails on
`serious` or `critical` violations. Full axe results are attached to the
Playwright test result for diagnosis; no selectors or rules are excluded.

The suite also checks a bounded keyboard path, explicit text alongside visual
status colors, named dynamic regions, and focus restoration after closing the
Assistant. Reduced-motion mode is used so scans measure the settled interface
rather than an intermediate animation frame.

CI runs this suite in the keyless Review App job, without provider credentials.

## Manual release checklist

Automation cannot determine whether the overall experience is understandable
with a screen reader. Before a release that changes a core workflow, record the
browser, operating system, screen reader, date, and result for these checks:

- Use only Tab, Shift+Tab, Enter, Space, and Escape to reach and operate every
  visible control in the three core pages.
- Activate the skip link and confirm that navigation reaches the main content.
- Open and close the Assistant and confirm focus enters the panel at its first
  control and returns to the launcher.
- With VoiceOver or NVDA, confirm that stream progress is announced as a short
  status update rather than re-reading the entire conversation for every token.
- Confirm that confirmation titles, source names and links, Mock/real labels,
  and error recovery actions have understandable names and reading order.
- Check confirmation, evidence, warning, success, and error states without
  relying on color alone.
- At 200% zoom and a narrow viewport, confirm controls remain reachable and no
  meaningful text or focus indicator is clipped.

The 2026-08-08 automated baseline passed eight checks: four scenarios on each
of the desktop and mobile projects. Manual assistive-technology review remains
a human release activity and must not be inferred from an axe result.
