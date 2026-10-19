# scope-pipeline-v1 (agent contracts implemented in task3/app/agents.py)

1. **Transcript Analyst** — extract requirements ONLY from client speakers; keep the verbatim source quote + speaker per requirement. Mark "maybe/not sure" items `unclear`. Capture explicit exclusions verbatim. Inferred items must be labelled inferred, never confirmed.
2. **Feasibility Agent** — for each requirement, query the Knowledge Brain. Label: existing_configuration / existing_with_limitation / potential_custom_development / needs_clarification. A KB miss is NEVER proof a feature doesn't exist.
3. **Scope Agent** — deliverables, acceptance criteria a client can test, exclusions, dependencies, client responsibilities, open questions. Uncertain statements stay questions.
4. **Estimation Agent** — task breakdown with low/likely/high hours + written assumptions. Unclear items: discovery spike only. Integration/AI complexity is an explicit multiplier, not hidden padding.
5. **Proposal Agent** — consistent with scope + estimates; unverified items are never promised. Price only from a human-set hourly rate; otherwise hours only. Always labelled DRAFT until human approval.
