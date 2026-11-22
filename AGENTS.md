# Standing user preferences

## Cluster job scheduling

- All future cluster batch jobs must request at most one hour of walltime (`--time=01:00:00` for Slurm). This applies to conversion, preparation, training, evaluation, and other batch workloads unless the user explicitly changes this instruction.
- Split longer workloads into linked jobs with successful-completion dependencies (for example, Slurm `afterok`) so each segment resumes the preceding segment's saved progress.
- Budget time to save and verify checkpoints before the one-hour limit. For training, preserve model/adapters, optimizer, scheduler, random-number state, and data position; for conversion or evaluation, persist completed shards and progress.
- Preserve the intended total workload and training/evaluation protocol when splitting jobs; do not shorten the run or restart completed work merely to fit one-hour allocations.

--- project-doc ---

# CuraLink project instructions

## Engineering record

- Read `docs/engineering-handbook.md` before substantive CuraLink engineering work.
- Keep that handbook current as part of the same task whenever the user accepts a significant design decision, revises a requirement or baseline, or a verified result materially changes the design. The user has authorized these routine documentation updates; do not ask again.
- Record only decisions that affect architecture, interfaces, performance, power, physical implementation, verification, or substantial project risk. Do not log ordinary conversation, every candidate component, or routine code edits.
- Do not convert a proposal into an accepted decision. Use the handbook's status vocabulary; retain unresolved suggestions in the open-work table only when important.
- Use the actual local date in America/New_York. Distinguish a decision's date from its recording date; never invent historical dates.
- For a material change, update the current-design summary and relevant decision entry, and append a concise revision-history row explaining what changed and why. Preserve superseded rationale when it explains architectural evolution. Do not silently rewrite history.
- Use stable decision IDs. Follow the compact decision format in the handbook: choice and status; objective; constraints/evidence; alternatives and tradeoffs; rationale; risks; verification and reopening conditions.
- Distinguish requirements, baselines, candidates, calculations, and measurements. Include units, bandwidths, assumptions, and source links when applicable. Verify external technical claims with primary sources before using them to finalize a new design choice.
- Keep detailed derivations, simulation outputs, and measurements in linked supporting files as they accumulate. Keep the handbook readable on its own and avoid competing copies of specifications.
- At the end of work that changes the engineering record, briefly mention that the handbook was updated.

## Engineering approach

- Reason from functional objectives and explicit tradeoffs. Do not accept a number solely because it appeared in an earlier conversation or another system used it.
- When asked to choose an engineering part or topology, present the decision criteria and functional objectives first. Give each meaningful option a one- or two-sentence description, parallel pros and cons, then a recommendation with its evidence, assumptions, and condition for revisiting it.
- Preserve the user's established decisions unless new evidence justifies reopening them; explain that evidence.
- Treat Rev A as potentially the only main PCB revision. Include observability, isolation, tuning access, footprint audits, and manufacturability in design evaluations.
- Main design reasoning belongs in the conversation. Do not create firmware, select parts as final, or expand implementation scope solely because the handbook lists future work.
