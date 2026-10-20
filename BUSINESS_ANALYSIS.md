# Business Analysis: Reducing Subscriber Churn

Portfolio project. Stakeholder roles are assumed for illustration. All figures come from a 7,500-customer sample of 2017 KKBox data and are not company-wide numbers.

## 1. Business problem
A subscription music service loses subscribers when they do not renew. In the sample, 711 of 7,500 customers (9.48%) churned. The retention team needs to know where churn concentrates and which customers to prioritise for retention actions.

## 2. Objectives
1. Describe how churn varies across customer groups.
2. Identify characteristics associated with churn after adjustment.
3. Measure how well customers can be ranked by churn risk.
4. Recommend an action the team can test, with explicit assumptions.

## 3. Stakeholders (assumed)
| Role | Interest | Needs from this work |
|---|---|---|
| Head of Retention | Lower churn | Segments to target and a testable action |
| Product Manager (Billing) | Renewal experience | Evidence on auto-renew and payment behaviour |
| Marketing Analyst | Campaign targeting | A ranked risk list and how reliable it is |
| Finance | Revenue impact | Scenario values with clear assumptions and costs |
| Data and Privacy Lead | Compliance | Confirmation that no customer-level data is published |

## 4. KPI definitions
| KPI | Definition | Value (sample) |
|---|---|---|
| Churn rate | Churned customers divided by customers | 9.48% |
| Churn rate by renewal type | Churn rate among customers whose latest transaction was auto-renew or manual-renew | 4.37% and 41.58% |
| Precision at threshold 0.10 | Share of flagged customers who churned | 42.1% (95% interval 35.4% to 48.7%) |
| Recall at threshold 0.10 | Share of churners who were flagged | 65.5% (57.8% to 73.1%) |
| Lift in top risk decile | Churn rate in the top decile divided by the overall churn rate | 51.33% against 9.47%, about 5.4 times |
| Churners captured by top two deciles | Share of all test churners in the two highest-risk deciles | 69.7% |

Revenue is in NTD, calculated as latest paid amount divided by plan days, times 30.

## 5. Findings and what they imply
1. Manual-renew customers churned at 41.58% against 4.37% for auto-renew customers (1,015 and 6,470 customers). After adjustment, auto-renew was associated with about 84% lower odds of churn.
2. Customers whose latest transaction was 31 or more days before the cutoff churned at 76.42%. This is tied to how churn is defined, so it is a risk indicator, not an independent explanation.
3. Recent listening did not clearly separate churners from retained customers, and adding it to the model raised ROC-AUC by only about 0.004.
4. The model ranks risk usefully (ROC-AUC 0.8191), but at threshold 0.10 about 58 in 100 flagged customers would not have churned.

These are associations. The data cannot show that changing renewal type causes lower churn.

## 6. Recommendation: test, do not roll out
Run a randomised pilot among eligible manual-renew customers, comparing an auto-renew enrolment nudge with the existing renewal journey.

| Design element | Proposal |
|---|---|
| Population | Manual-renew customers due to renew |
| Groups | Random split into nudge and control |
| Primary measures | Auto-renew adoption, renewal rate |
| Secondary measures | Churn rate, incentive cost, net retained revenue, opt-outs and complaints |
| Cuts | Payment method and customer tenure |
| Sample size | To be set by a power calculation (baseline manual-renew churn 41.58%) |
| Decision rule | Roll out only if net retained revenue is positive after incentive cost |

## 7. Illustrative business case
These values are gross, in NTD, before intervention costs, and apply to the 1,015 manual-renew customers in the sample, not the whole customer base. They assume revenue stays constant and every avoided churner stays for the period. They are a what-if, not a forecast.

| Churn reduction | Avoided churn events | Gross monthly (NTD) | Gross annual (NTD) |
|---|---|---|---|
| 2 points | 20.30 | 2,857.48 | 34,289.74 |
| 5 points | 50.75 | 7,143.70 | 85,724.34 |
| 10 points | 101.50 | 14,287.39 | 171,448.69 |

## 8. Requirements
| ID | Requirement | Priority |
|---|---|---|
| R1 | Report churn rate by renewal type with group sizes | Must |
| R2 | Rank customers by churn risk and report precision and recall with intervals | Must |
| R3 | Label recency as a target-proximal indicator | Must |
| R4 | Show scenario values as gross, illustrative and before costs | Must |
| R5 | Publish no customer-level data | Must |
| R6 | Provide a secure internal retention queue | Should |
| R7 | Test for a campaign effect with a randomised pilot | Should |
| R8 | Add temporal validation if future-period labels are available | Could |
| R9 | Forecast revenue impact | Won't (data does not support it) |

User stories:
- As Head of Retention, I want churn by renewal type with group sizes, so that I can choose a segment to test.
- As a Marketing Analyst, I want customers ranked by risk with stated reliability, so that I can size a campaign.
- As Finance, I want scenario values with assumptions, so that I can judge whether a pilot is worth running.

## 9. Assumptions, risks and limitations
| Item | Detail | Mitigation |
|---|---|---|
| Old data | 2017 data and a random split, not temporal validation | Make no claim about future performance |
| Association only | Auto-renew may reflect customer loyalty, not cause it | Test with a randomised pilot |
| Precision | About 58% of flagged customers would not have churned | Weigh intervention cost against benefit |
| Same-day transactions | Order rule reproducible but not verified as the official one; 54 customers affected | Documented in DATA_PROVENANCE.md |
| Small group | 15 customers with no transaction history | Draw no conclusions from it |
| Data licence | Competition data may not be redistributed | Publish aggregates and code only |

## 10. Next steps
1. Agree the pilot design and sample size with Retention and Finance.
2. Set the incentive budget and success threshold.
3. Run the pilot for at least one full renewal cycle.
4. Review results and decide on rollout.