# Feedback Signal Matrix and Dataset Sufficiency Policy

Every signal is stored as a filtered immutable event. A signal becomes a
preference candidate only when it has exact AI-answer provenance and an actual
alternative answer; no answer is synthesized for this pipeline.

| Signal | Strength | Preliminary label | Pair eligible |
|---|---|---|---|
| Explicit human correction linked to one AI answer | HIGH | AI negative / human positive | Yes; corrected human text is chosen and exact AI text is rejected |
| Rating 4–5 with exact answer provenance | MEDIUM | Positive | Only with a compatible, same-ticket/same-prompt negative AI alternative |
| Rating 1–2 with exact answer provenance | MEDIUM | Negative | Only with an actual correction or compatible positive alternative |
| Rating 3 | Neutral | Neutral | No |
| Resolved or closed alone | LOW | Neutral | No |
| Reopen explicitly linked to AI answer | MEDIUM | Negative evidence | Only with a real correction or compatible positive alternative |
| Escalation explicitly linked to AI answer | MEDIUM | Negative evidence | Only with a real correction or compatible positive alternative |
| Human takeover | LOW | Outcome context | No |
| Legacy ticket rating without answer ID | None | Unlinked | No |

The readiness policy (`preference-sufficiency-v2`) is conservative: 2,000
approved HIGH/MEDIUM pairs, 1,500 train, 200 validation, 200 held-out test,
at least 40% HIGH quality, at least three technical domains, no single ticket
group above 20%, duplicate-event rate at most 2%, and privacy rejection rate
at most 20%. Passing the policy does not authorize DPO/ORPO training; the
evaluation contract and explicit human experiment approval still apply.
