---
name: email-formatter
description: Use this skill when formatting and sending wellness reports via email. Provides a Gmail-compatible HTML template with Red Hat branding and inline CSS rules.
---

# Email Formatter — Gmail-Compatible HTML

## When to Use
When you need to send a wellness report via email. The body MUST be HTML with inline CSS only.
Gmail strips `<style>` blocks and CSS classes, so every element needs inline styles.

## HTML Template

```html
<div style="max-width:600px;margin:0 auto;font-family:Arial,Helvetica,sans-serif;color:#333;">
  <div style="background-color:#CC0000;color:white;padding:20px;text-align:center;">
    <h1 style="margin:0;font-size:22px;">Red Hat Wellness Report</h1>
  </div>
  <div style="padding:20px;">
    <!-- Metric box -->
    <div style="background-color:#f5f5f5;padding:12px;border-radius:6px;margin-bottom:16px;">
      <strong>BMI:</strong> VALUE (CATEGORY)
    </div>
    <!-- Use <h3>, <p>, <ul>/<li>, <strong> for content -->
    <!-- Separate sections with: -->
    <hr style="border:none;border-top:1px solid #ddd;margin:20px 0;">
  </div>
  <div style="padding:12px 20px;font-size:12px;color:#999;text-align:center;">
    This is not medical advice. Consult a healthcare professional.
  </div>
</div>
```

## Formatting Rules
- Inline CSS on every element. No `<style>` tags, no CSS classes.
- Use `<table>` with inline styles if you need multi-column layout.
- Max width 600px for email client compatibility.
- Red Hat header: `background-color:#CC0000; color:white`.
- Metric highlight boxes: `background-color:#f5f5f5; padding:12px; border-radius:6px`.
- Section dividers: `<hr style="border:none;border-top:1px solid #ddd;margin:20px 0;">`.
- Footer disclaimer in small gray text: `font-size:12px; color:#999`.

## Sections to Include
1. **Header** — Red Hat branded banner
2. **BMI Result** — value, category, one-line interpretation in a highlight box
3. **Daily Targets** — water intake and calorie targets
4. **Health Tips** — actionable tips as a bullet list
5. **Disclaimer** — footer with medical advice disclaimer
