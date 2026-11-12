---
name: env_probe
description: **Problem Category**: Environment/tooling discovery on a machine before building software.
entry_file: env_probe.py
---

# env_probe

## Description
**Problem Category**: Environment/tooling discovery on a machine before building software.
**Applicable Questions**: 'What Python packages/binaries are available for X', 'Is tool Y installed', 'Can I install Z / is there internet', general capability probing.
**Key Features**: LLM proposes safe read-only diagnostic commands, plus always-included robust Python import-spec probes and binary existence checks and an internet reachability test; runs them via shell and summarizes findings.
**Skills Used**: execute_shell_command, call_llm.
**Reasoning Pattern**: goal -> generate JSON command list (augmented with reliable import/binary/net probes) -> execute -> summarize.
**Input Format**: Natural-language investigation goal.
**Output Format**: dict with answer (JSON map of command->output) and LLM summary.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `env_probe.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "env_probe", "query": "<your focused sub-question>"}</params>
```
