# Business Analysis: Auto-Renew Nudge Pilot for Manual-Renew Subscribers

Portfolio project. Stakeholder roles, costs and operational details are **assumed for illustration** and are marked as such. All figures come from a 7,500-customer random sample (seed 42) of 2017 KKBox data, with features cut off at 2017-02-28. They are not company-wide numbers.

## 1. Decision

**Decision requested:** Approve the *design* of a controlled pilot, not a rollout. The pilot tests whether an opt-in auto-renew nudge reduces churn among manual-renew subscribers.

**Targeting decision:** Select pilot customers with a simple renewal-status rule (manual-renew), not the churn model. Section 5 shows why.

| Item | Proposal |
|---|---|
| Decision owner (assumed) | Head of Retention |
| Required sign-off (assumed) | Finance reviewer: cost model, budget cap |
| Primary metric | Churn rate at 30 days after membership expiry, nudge vs control |
| No-go rule | Do not roll out unless the churn reduction is statistically significant, at least the break-even reduction in `business_case.xlsx`, and no guardrail is breached |

| Option | Assessment |
|---|---|
| A. Do nothing | Leaves the highest-churn group (41.58%) untouched |
| B. Roll out the nudge to all manual-renew customers | Evidence is observational. Effect, cost and customer harm are unknown |
| **C. Run a controlled pilot (recommended)** | Measures the missing piece: does the nudge itself change churn? |

## 2. Evidence behind the decision

| Finding | Result | What it means for the decision |
|---|---|---|
| Churn by renewal type | Manual-renew 41.58% (1,015 customers) vs auto-renew 4.37% (6,470) | Manual-renew is where churn concentrates |
| Adjusted association | Auto-renew linked to about 84% lower odds of churn (odds ratio 0.157) | Strong association, but loyal customers may simply choose auto-renew. Only a pilot can test cause |
| Recency | 31+ days since latest transaction: 76.42% churn (352 customers) | Close to the churn definition. Many of these customers may already be gone, so this is win-back, not retention |
| Recent listening | 8.18% to 10.64% churn across activity groups | Engagement does not separate churners; not a useful targeting signal |
| Model vs rule | See section 5 | The model does not beat a simple rule at the same contact budget |

These are associations. The data cannot show that switching a customer to auto-renew lowers their churn.

## 3. Stakeholders and RACI (assumed)

| Activity | Head of Retention | Finance | Product Manager (Billing) | CRM / Marketing | Data and Privacy Lead | Analyst (author) |
|---|---|---|---|---|---|---|
| Approve pilot design | **A** | C | C | I | C | R |
| Approve budget cap and cost model | C | **A** | I | I | I | R |
| Build nudge in renewal journey | I | I | **A** | R | C | C |
| Confirm consent and opt-in wording | C | I | R | C | **A** | I |
| Randomise and monitor guardrails | I | I | I | C | C | **A/R** |
| Analyse results and recommend rollout or stop | **A** | C | C | I | I | R |

R = responsible, A = accountable (one per row), C = consulted, I = informed.

## 4. KPI definitions

| KPI | Definition | Sample value |
|---|---|---|
| Churn rate | Customers with no new valid subscription within 30 days of membership expiry, divided by customers (Kaggle definition) | 9.48% overall |
| Churn by renewal type | Churn rate by renewal type of the latest transaction | 41.58% manual, 4.37% auto |
| Precision | Share of contacted customers who would have churned | See section 5 |
| Capture | Share of all churners who were contacted | See section 5 |
| Auto-renew adoption (pilot) | Share of nudge-group customers who opt in to auto-renew within the pilot window | To be measured |

## 5. Targeting: does the model beat a simple rule?

Same 1,500 held-out test customers (142 churners), same contact budget. Source: `24_benchmark_rules.py`, `benchmark_model_vs_rules.csv`.

| Approach | Contacted | Churners caught | Precision | Capture |
|---|---|---|---|---|
| Rule: manual-renew | 200 (13.3%) | 83 | 41.5% | 58.5% |
| Model, same budget | 200 (13.3%) | 85 | 42.5% | 59.9% |
| Rule: manual-renew OR 31+ days lapsed | 223 (14.9%) | 99 | 44.4% | 69.7% |
| Model, same budget | 223 (14.9%) | 93 | 41.7% | 65.5% |
| Model, top 10% | 150 (10.0%) | 77 | 51.3% | 54.2% |
| Random, 10% (expected) | 150 (10.0%) | 14 | 9.5% | 10.0% |

**Conclusion.** At budgets around 13% to 15%, the model performs the same as a one-line rule. The two-point gap at 13.3% is noise. The rule is free to run, easy to explain and needs no scoring pipeline, so **the pilot uses the manual-renew rule**. The model only adds value if Retention can contact fewer than about 10% of customers, where it ranks the highest-risk customers more finely.

**Caveats.** Both rules came from descriptive analysis on the full sample, which includes these test customers, so the rules had a small head start. The test set was reused for this benchmark after the final model evaluation; no model choice changed as a result.

## 6. Current and proposed process

**Current (as-is), assumed:** Manual-renew customer's membership approaches expiry → standard renewal reminder → customer pays manually or lets the membership lapse → lapsed customers are not contacted by Retention.

**Proposed (to-be), pilot only:** Eligible manual-renew customers are randomised 1:1 → nudge group receives the existing reminder **plus** an opt-in prompt to switch to auto-renew → control group receives the existing reminder only → outcomes recorded at 30 days after expiry.

**Business rules:**
- **BR1 Eligibility:** latest transaction is manual-renew; membership expires inside the pilot window; customer has a valid marketing consent; customer is not in another retention campaign.
- **BR2 Consent:** auto-renew is switched on only after an explicit customer opt-in. No pre-ticked boxes.
- **BR3 Frequency:** at most one nudge per customer per renewal cycle.
- **BR4 Assignment:** a customer's group is fixed at randomisation and never changes.
- **BR5 Exclusion:** customers with an open complaint or payment dispute are excluded.

A BPMN diagram of both processes is in `docs/process_as_is_to_be.png` (to be added).

## 7. Pilot protocol

| Element | Design |
|---|---|
| Population | Manual-renew subscribers whose membership expires during the pilot window and who meet BR1 |
| Unit and assignment | Customer, randomised 1:1, stratified by payment method |
| Intervention | Existing renewal reminder plus an opt-in auto-renew prompt (in-app and email). No price incentive in the base design |
| Control | Existing renewal reminder only |
| Primary outcome | Churn at 30 days after membership expiry (Kaggle definition) |
| Secondary outcomes | Auto-renew adoption, cancellations within 60 days, revenue per customer |
| Guardrails (assumed thresholds) | Complaint rate, unsubscribe rate and payment disputes. Pause if the nudge group exceeds control by more than 1 percentage point on any guardrail |
| Sample size | **1,491 per arm (2,982 total)** to detect a drop from 41.58% to 36.58% with 80% power at 5% two-sided significance |
| Feasibility | Manual-renew customers were 13.5% of the sample. At full scale the pilot needs at least 2,982 eligible customers expiring in the window. **Assumption to confirm with Retention:** monthly eligible volume |
| Duration | One renewal cycle (about 30 days) plus the 30-day outcome window |
| Analysis | Intention-to-treat. Two-proportion test on the primary outcome. Analysis plan fixed before launch; no early peeking except guardrail checks |
| Decision rule | See the no-go rule in section 1 |

**Why 5 points?** It is a planning assumption, not an estimate. A smaller true effect would need a larger pilot: about 9,460 customers per arm for a 2-point drop.

## 8. Business case

The full model, with live formulas, cost inputs and scenarios, is in `business_case.xlsx`. All cost inputs there are assumptions.

Gross value at sample scale, before any cost (average monthly revenue of a churned manual-renew customer: 140.76 NTD):

| Churn reduction | Avoided churn events (of 1,015) | Gross monthly (NTD) | Gross annualised (NTD) |
|---|---|---|---|
| 2 points | about 20 | about 2,860 | about 34,300 |
| 5 points | about 51 | about 7,140 | about 85,700 |
| 10 points | about 102 | about 14,290 | about 171,400 |

These assume each avoided churner stays for the whole period at the same revenue. They are what-ifs, not forecasts.

## 9. Requirements with acceptance criteria

| ID | Requirement | Priority | Acceptance criteria | Status |
|---|---|---|---|---|
| R1 | Report churn by renewal type with group sizes | Must | Given the dashboard summary tables, when Retention views renewal type, then each group shows its churn rate and customer count | Done |
| R2 | Compare model and rule targeting at equal budgets | Must | Given the held-out test set, when the benchmark runs, then precision and capture are reported for each approach at the same contact count | Done |
| R3 | Select pilot customers by rule | Must | Given a customer list on the pilot start date, when BR1 is applied, then only eligible manual-renew customers are included and each has one assignment | Proposed |
| R4 | Enforce opt-in consent | Must | Given a nudge-group customer, when they have not confirmed opt-in, then auto-renew stays off | Proposed |
| R5 | Monitor guardrails | Must | Given weekly pilot data, when any guardrail gap exceeds 1 point, then the pilot is paused and the decision owner is notified | Proposed |
| R6 | Publish no customer-level data | Must | Given the public repository, when it is scanned, then no raw, customer-level or prediction files are present | Done |
| R7 | Calculate break-even churn reduction | Should | Given cost inputs in the business case, when any input changes, then break-even updates automatically | In progress |
| R8 | Forecast revenue impact | Won't | The data does not support a forecast | Won't do |

## 10. Assumptions and risks

| Item | Type | Detail | Mitigation |
|---|---|---|---|
| Stakeholder roles | Assumption | Invented for illustration | Replace with real owners before use |
| 5-point effect | Assumption | Planning value, not an estimate | Sample size shown for 2 points as well |
| Guardrail thresholds | Assumption | 1-point pause rule is illustrative | Agree with Retention and Privacy before launch |
| Monthly eligible volume | Assumption | Unknown outside the sample | Confirm with Retention; extend window if too low |
| Self-selection | Risk | Auto-renew customers may be loyal already | Randomised design isolates the nudge effect |
| Customer harm | Risk | Unwanted charges if auto-renew is unclear | BR2 opt-in consent, guardrails R5 |
| Old data | Limitation | 2017 data, random not temporal split | No claim about current performance |
| Test-set reuse | Limitation | Holdout reused for the benchmark | Disclosed; no model choice changed |

## 11. Next steps

1. Head of Retention and Finance review this pilot design and the cost model.
2. Confirm monthly eligible volume, consent wording and guardrail thresholds.
3. Fix the analysis plan, then run the pilot for one renewal cycle.
4. Decide on rollout using the no-go rule in section 1.
