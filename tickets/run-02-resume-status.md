# run-02-resume-status: Clear stale pause labels for queued models

- **Status**: Open
- **Priority**: Medium
- **Assignee**: Edward Benson
- **Branch**: Not claimed; discovered on `run-01-v1-model-campaign`
- **Machine**: eob-dev2
- **Harness**: codex
- **Session ID**: `/root` / FontBench release campaign

## Observed behavior

During a resumed invocation with all eleven models selected, models awaiting their first dispatch can retain a previous invocation's `paused` state and “Interrupted; resume to continue” reason. The scheduler still queues and eventually runs their missing inputs, but the summary and website incorrectly suggest that another resume is required.

At `2026-09-08T22:53:54.331437+00:00`, the V1.0.0 campaign was running. Claude had 294–296 observations per model, while the seven OpenAI/Gemini configurations had 348–349 and still showed the old interruption reason. An independent code review confirmed that the scheduler queues every missing selected task and resets invocation blocking sets; stored model states are used for reporting, not eligibility. They change to `running` only when the first request is dispatched. After a subsequent intentional drain, reconstructing the deterministic queue yielded 191 Claude entries before the first OpenAI entry.

Code base: `952c723f698bdc3f751a792d9a08293c42d9587c`. Relevant code: `baseline/runner.py`, pending queue construction, summary model-state export, and first-dispatch state update.

## Acceptance criteria

- Selected incomplete models with queued work display pending/queued and clear obsolete pause reasons before the first snapshot.
- Unselected models, completed models, and newly encountered provider errors retain accurate states.
- An offline regression reproduces unequal model progress across interruption/resume and checks reporting before delayed dispatch.
- Scheduling, completed results, costs, request bodies, and V1.0.0 release identities remain unchanged.

This is a reporting defect. No evidence indicates lost measurements or blocked scheduling. The cap update records this issue without changing benchmark source.
