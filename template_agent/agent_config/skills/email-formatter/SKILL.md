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

## Email Structure

The email has three layers: **header**, **body sections**, and **footer**.

### Fixed Sections (always present)

1. **Header** — Red Hat branded banner
2. **Disclaimer** — footer with medical advice disclaimer

### Dynamic Sections (include only what is provided in the input)

Each piece of content provided as input gets its own section in the body.
Render them in the order they appear below. **Skip any section whose data
was not provided — never leave an empty section or placeholder.**

| Section | When to include | Content |
|---------|----------------|---------|
| BMI Result | BMI value + category provided | Value, category, one-line interpretation in a highlight box |
| Daily Targets | Water and/or calorie targets provided | Water intake and calorie targets |
| Health Tips | Tips list provided | Actionable tips as a bullet list |
| Workout Plan | Workout plan provided | Weekly overview, exercises, sets/reps |
| Diet Plan | Diet plan provided | Calorie target, macros, sample meals |

This list is not exhaustive — if the input contains additional named sections
not listed above, render them using the same styling conventions (heading +
content + divider).

## HTML Template

```html
<div style="max-width:600px;margin:0 auto;font-family:Arial,Helvetica,sans-serif;color:#333;">
  <!-- Header (always) -->
  <div style="background-color:#CC0000;color:white;padding:20px;text-align:center;">
    <h1 style="margin:0;font-size:22px;">Red Hat Wellness Report</h1>
  </div>

  <div style="padding:20px;">
    <!-- Metric highlight box (if BMI provided) -->
    <div style="background-color:#f5f5f5;padding:12px;border-radius:6px;margin-bottom:16px;">
      <strong>BMI:</strong> VALUE (CATEGORY)
    </div>

    <!-- Repeat for each dynamic section present in the input:
         <h3 style="color:#CC0000;margin-top:24px;">SECTION TITLE</h3>
         ... section content using <p>, <ul>/<li>, <table>, <strong> ...
         <hr style="border:none;border-top:1px solid #ddd;margin:20px 0;">
    -->
  </div>

  <!-- Disclaimer (always) -->
  <div style="padding:12px 20px;font-size:12px;color:#999;text-align:center;">
    This is not medical advice. Consult a healthcare professional.
  </div>
</div>
```

## Gotchas

- **Never use CSS classes or `<style>` tags** — they are stripped by Gmail.
- **Always include the disclaimer footer** — it is mandatory.
- **Only render sections that have data** — no empty placeholders or headings without content.
- **Test width** — anything over 600px breaks on mobile email clients.
