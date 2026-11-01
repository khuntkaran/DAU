---
name: pm-surya-rules
description: PM Surya Ghar subsidy, system sizing, cost, payback and quote scoring rules with their sources. Use before writing or changing anything that calculates or displays subsidy, system size, cost, savings, payback or vendor ranking, and when seeding quotes.
---

# PM Surya Ghar rules

The brief requires three things. Rules follow the public scheme, the app shows where each rule comes from, and subsidy, cost and payback are calculated in code, never by the LLM.

Read [references/rules.md](references/rules.md) for each rule's research status.

## Where the code lives

- `rules/pm_surya_ghar_v2024_03.yaml`: the only place rule values are written, each with `id`, `value`, `source`, `url` and `status`.
- `rules/loader.py`: loads and validates the YAML into a frozen `RuleSet`.
- `rules/sizing.py`, `subsidy.py`, `payback.py`, `scoring.py`, `checklist.py`: pure functions with no I/O.

Never write a rule value anywhere else, including seed data and UI copy.

## Required behaviour

1. Every result carries `rule_version` and `citations`. The API returns them, and the UI shows an ⓘ link beside each figure.
2. Anything with status `assumption` or `verify` is labelled as an estimate in the UI.
3. Money is whole rupees in `int`. Calculate with `Decimal`, and round half up once, at the end.
4. The LLM may receive calculated numbers to explain. It never produces one that reaches the user unchecked.
5. Scoring takes structured facts only. Free text has no effect on a score.

## Required tests

`rules/tests/test_golden.py` covers 0, 1, 2, 2.5, 3, 5 and 10 kW in both state categories, plus the golden example in the reference, including the ₹25,740 saving and 4.2 year payback. The design document's ₹28,080 is wrong, because it ignores the consumption cap.

Also test: negative input is rejected, payback is `None` when saving is zero, net cost never goes below zero, identical quotes differing only in notes score the same, and ranking is stable.

## Changing a rule

Update the YAML, `references/rules.md` and the tests in the same change, and record the check date. A rule with no source stays `assumption`. Do not upgrade a status to `confirmed` without reading the primary document.
