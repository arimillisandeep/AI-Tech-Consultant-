# Scope of Work — BloomBox — E-commerce (Meeting B)

_Status: DRAFT — requires human approval before sending. Pipeline: scope-pipeline-v1_

## Requirements (with feasibility checked against product knowledge)

### REQ-001 — We need checkout to be reliable
- Status: **confirmed** · Priority: must-have · Feasibility: **needs_clarification**
- Feasibility note: No matching documented capability found. Absence of evidence is not evidence of absence — expert to confirm.
- Evidence: no KB citation (offline check)
- Acceptance: Client can verify: we need checkout to be reliable (confirm exact test at approval).
- Client said (Elena): “Elena: Customers abandon because card payments fail sometimes. We need checkout to be reliable. We use Stripe, some florists ask about PayPal too.”

### REQ-002 — We also want order notification emails that actually arrive — confirmations, and a reminder before a subscription renews
- Status: **confirmed** · Priority: should-have · Feasibility: **existing_with_limitation**
- Feasibility note: Templates editable/on-off; deliverability needs SPF+DKIM on sending domain.
- Evidence: no KB citation (offline check)
- Acceptance: Client can verify: we also want order notification emails that actually arrive — confirmations, and a reminder before a subscription renews (confirm exact test at approval).
- Client said (Elena): “Elena: We also want order notification emails that actually arrive — confirmations, and a reminder before a subscription renews. Right now half of them land in spam.”

### REQ-003 — Also, when a member cancels, we need refunds handled correctly — our team is unsure about the exact rules, like how old a payment can be for a refund
- Status: **confirmed** · Priority: must-have · Feasibility: **existing_configuration**
- Feasibility note: Refunds via Finance > Transactions; dashboard limit 180 days.
- Evidence: no KB citation (offline check)
- Acceptance: Client can verify: also, when a member cancels, we need refunds handled correctly — our team is unsure about the exact rules, like how old a payment can be for a refund (confirm exact test at approval).
- Client said (Elena): “Elena: Please do. Also, when a member cancels, we need refunds handled correctly — our team is unsure about the exact rules, like how old a payment can be for a refund.”

### REQ-004 — But I need a clear estimate split by item so I can choose what to approve
- Status: **confirmed** · Priority: must-have · Feasibility: **needs_clarification**
- Feasibility note: No matching documented capability found. Absence of evidence is not evidence of absence — expert to confirm.
- Evidence: no KB citation (offline check)
- Acceptance: Client can verify: but i need a clear estimate split by item so i can choose what to approve (confirm exact test at approval).
- Client said (Elena): “Elena: Timeline is flexible, quality matters more. But I need a clear estimate split by item so I can choose what to approve.”

## Explicit exclusions (from client's own words)

- None recorded — confirm at approval.

## Open questions (do not estimate as firm work until answered)

- REQ-001: We need checkout to be reliable — No matching documented capability found. Absence of evidence is not evidence of absence — expert to confirm.
- REQ-004: But I need a clear estimate split by item so I can choose what to approve — No matching documented capability found. Absence of evidence is not evidence of absence — expert to confirm.

## Effort summary

- Low: **11 h** · Likely: **23 h** · High: **42 h**
- Ranges, not a fixed quote. `needs_clarification` items carry only a discovery spike.

## Client responsibilities
- Approve/revise this scope; confirm acceptance tests; provide test data and timely feedback.
