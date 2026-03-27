---
name: email-formatter
description: >
  Provides Gmail-compatible HTML template and inline CSS rules for formatting
  wellness report emails. Use when formatting and sending wellness reports
  via email with send_email.
---

# Email Formatter — Gmail-Compatible HTML

## When to Use

When sending a wellness report via `send_email`. The body **must** be HTML
with inline CSS only — Gmail strips `<style>` blocks and CSS classes.

## Formatting Rules

- Inline CSS on **every** element. No `<style>` tags, no CSS classes.
- Use `<table>` with inline styles for multi-column layout.
- Max width **600px** for email client compatibility.
- Red Hat header: `background-color:#CC0000; color:white`.
- Metric highlight boxes: `background-color:#f5f5f5; padding:12px; border-radius:6px`.
- Section dividers: `<hr style="border:none;border-top:1px solid #ddd;margin:20px 0;">`.
- Footer disclaimer: `font-size:12px; color:#999`.

## Sections to Include

1. **Header** — Red Hat branded banner
2. **BMI Result** — value, category, one-line interpretation in a highlight box
3. **Daily Targets** — water intake and calorie targets
4. **Health Tips** — actionable tips as a bullet list
5. **Disclaimer** — footer with medical advice disclaimer

For the HTML template, see [TEMPLATE.html](TEMPLATE.html).

## Gotchas

- **Never use CSS classes or `<style>` tags** — they are stripped by Gmail.
- **Always include the disclaimer footer** — it is mandatory.
- **Test width** — anything over 600px breaks on mobile email clients.
