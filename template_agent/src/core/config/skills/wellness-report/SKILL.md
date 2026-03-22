---
name: wellness-report
description: Use this skill when generating a wellness summary report for a user. Formats BMI results, health tips, and hydration/calorie targets into a clean branded report.
---

# Wellness Report Formatting

## BMI Categories
- Under 18.5: Underweight
- 18.5–24.9: Normal
- 25–29.9: Overweight
- 30+: Obese

## Report Structure
Always format the report as:
1. **BMI Result**: Value + category + one-line interpretation
2. **Daily Targets**: Water intake in liters (use multiply_tool: weight_kg × 0.033), base calories (use multiply_tool: weight_kg × 24)
3. **Health Tips**: 3 actionable tips from web_search_tool relevant to the BMI category, keep each to one sentence
4. **Disclaimer**: "This is not medical advice. Consult a healthcare professional."

## Tone
Friendly, encouraging, non-judgmental. Never use words like "bad" or "failing" about someone's BMI.
