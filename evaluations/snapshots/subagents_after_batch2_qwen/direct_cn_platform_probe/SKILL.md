---
name: direct_cn_platform_probe
description: **Problem Category**: Discovering which direct Chinese social-media platform trending endpoints are reachable and their JSON schema.
entry_file: direct_cn_platform_probe.py
---

# direct_cn_platform_probe

## Description
**Problem Category**: Discovering which direct Chinese social-media platform trending endpoints are reachable and their JSON schema.
**Applicable Questions**: Any task needing to find working data sources for Weibo/Zhihu/Baidu/Bilibili/Douyin trending data in a restricted network.
**Key Features**: Probes direct platform endpoints (weibo.com/ajax/side/hotSearch, top.baidu.com/api/board, zhihu hot-lists, bilibili ranking, douyin hot, plus 60s aggregator) with browser UA/Referer and SSL fallback; reports HTTP status, JSON validity and schema via LLM analysis.
**Skills Used**: execute_shell_command
**Reasoning Pattern**: probe endpoints -> capture status/body/preview -> LLM schema analysis -> recommend best sources.
**Input Format**: free-text probing goal.
**Output Format**: returns {answer,summary} with which endpoints returned valid JSON and their title/heat field paths.

## Skills Used
execute_shell_command

## Usage

**Entry file**: `direct_cn_platform_probe.py`

**Query type**: Pass a focused sub-question as the query.

**How to call**:
```xml
<action>run_subagent</action>
<params>{"skill_name": "direct_cn_platform_probe", "query": "<your focused sub-question>"}</params>
```
