# External onboarding validation form

Use this form after a person outside the implementation effort attempts the
[15-minute Quick Start](contributor-quick-start.md). The project author cannot
serve as the external participant, and the result must not be marked successful
if the author had to explain an undocumented step.

The participant may report a role such as “classmate” or “open-source
contributor”; a legal name is not required. Do not include private molecules,
credentials, local database contents, or personal filesystem paths.

## Session record

```text
Date:
Participant role (no legal name required):
Was the participant outside the implementation effort? yes / no
Source commit (`git rev-parse --short HEAD`):
Operating system:
Docker version:
Start time:
Finish or stop time:

Did the author provide live help? yes / no
If yes, what help was needed?

Workspace started with `make onboarding`: pass / fail
Single CCO workflow: pass / fail / not reached
Batch sample_mixed.csv workflow: pass / fail / not reached
Assistant confirmation workflow: pass / fail / not reached
M12 evidence workflow: pass / fail / not reached
Services stopped with `make container-down`: pass / fail / not reached

First confusing or failing step:
Observed result:
Expected result:
Recovery attempted:
One documentation improvement:
Would the participant know where to make a first contribution? yes / no
Suggested contribution lane:
```

## Passing rule

The independent onboarding criterion passes only when at least one external
participant completes one full Mock workflow without author assistance. Record
minor wording suggestions even when the workflow passes. A failure is useful
evidence and should become a bounded documentation or tooling issue rather than
being rewritten as success.

Post the redacted record to [Issue #20](https://github.com/jichenggepeter-dev/adme-dialog-agent/issues/20)
or link a pull request that fixes the observed blocker. Keep #20 open until the
external completion actually happens.
