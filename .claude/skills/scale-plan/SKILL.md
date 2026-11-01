---
name: scale-plan
description: Write or update docs/ARCHITECTURE.md and the scaling, deployment and cost plan for the judges' presentation. Use for architecture diagrams, data model, API summaries, hosting choices, cost estimates or presentation preparation.
---

# Architecture and scale plan

Scalability and architecture are 40% of the judging score. Hosting is not required, but the plan is. Write for judges in a short presentation.

Base `docs/ARCHITECTURE.md` on `SuryaSetu Architecture.html`, then bring it in line with what was really built. It must cover:

1. **Walkthrough:** the request → quote → accept flow.
2. **Components:** web, API, rules engine, worker, LLM gateway, database, storage, as a diagram.
3. **Data model and APIs:** from the real code. Do not describe unbuilt work as if it exists.
4. **Scale:** sections 09 and 10 of the design, covering the database, photos, background AI jobs and LLM limits.
5. **Hosting and cost:** section 11, for state scale and the one-district pilot.

## Before presenting

- Correct the worked example: the annual saving is ₹25,740 and payback is 4.2 years.
- Replace "Gemini 2.x Flash" with the model actually used, and check it against the provider's docs.
- Replace the MNRE attribution on the 120 kWh figure unless a source has been found.
- Look up current prices, cite them with the date, and show the arithmetic.
- State which LLM volume exceeds the free tier.
