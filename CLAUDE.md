# Skills Repo — Project Context

This is an OpenCode skills development repository. Develops, stores, and manages custom skills (agent workflows) and their bundled subagents.

## Structure

```
<skill-name>/                    # Skill source directory
  SKILL.md                       # Skill definition (frontmatter + instructions)
  _agents/                       # Bundled subagents for this skill
  agents/                        # Agent convention output directory (openai.yaml)
  references/                    # Format/reference specifications (CONTRACT-FORMAT.md, WORKFLOW-PROCESS.md, etc.)
```

## Agent Naming Conventions

- Each skill's agents use a unique prefix: `spec-` (generate-engineering-specs), `tix-` (generate-tickets), etc.
- No `-agent` suffix in agent names.
- Agent name = filename (without `.md` extension) = `name:` frontmatter field.

## Context7 Integration Rules

<rules>
  <rule priority="CRITICAL" id="context7-third-party-packages">
    <description>
      Always use Context7 MCP server for any task related to third-party packages.
      This ensures access to the most up-to-date documentation and code examples.
    </description>

    <triggers>
      <trigger>Importing or requiring a third-party package</trigger>
      <trigger>Using APIs from node_modules</trigger>
      <trigger>Writing code that depends on external libraries</trigger>
      <trigger>Debugging third-party package issues</trigger>
      <trigger>Searching for package documentation</trigger>
      <trigger>Learning about package features or APIs</trigger>
      <trigger>Migrating or upgrading package versions</trigger>
    </triggers>

    <third_party_definition>
      <condition>Any module located in node_modules directory</condition>
      <condition>Any package installed via npm, yarn, pnpm, or bun</condition>
      <condition>Any external library not part of the project's core source code</condition>
      <condition>Any package listed in package.json dependencies or devDependencies</condition>
    </third_party_definition>

    <workflow>
      <step order="1">
        <action>Identify the package name and version from package.json</action>
        <tool>Read package.json</tool>
        <tool>Use Grep to find package imports in source files</tool>
      </step>

      <step order="2">
        <action>Resolve library ID using Context7</action>
        <tool>mcp__plugin_context7_context7__resolve-library-id</tool>
        <parameters>
          <libraryName>{package_name}</libraryName>
          <query>{user_task_description}</query>
        </parameters>
      </step>

      <step order="3">
        <action>Query documentation with resolved library ID</action>
        <tool>mcp__plugin_context7_context7__query-docs</tool>
        <parameters>
          <libraryId>{resolved_library_id_from_step_2}</libraryId>
          <query>{specific_question_about_api_usage}</query>
        </parameters>
        <constraints>
          <constraint>Maximum 3 calls per question</constraint>
          <constraint>Be specific in queries about API usage</constraint>
          <constraint>Include context about the task being performed</constraint>
        </constraints>
      </step>

      <step order="4">
        <action>Implement code using retrieved documentation</action>
        <reference>Cite Context7 as source of documentation</reference>
      </step>
    </workflow>

    <exceptions>
      <exception>
        <condition>Package is not available in Context7</condition>
        <fallback>Use WebSearch for official documentation</fallback>
        <fallback>Use WebReader to fetch docs from official site</fallback>
      </exception>
      <exception>
        <condition>Task involves only standard library (Node.js built-ins, native browser APIs)</condition>
        <action>No Context7 call needed</action>
      </exception>
    </exceptions>

    <best_practices>
      <practice>Always check package.json for exact version before querying Context7</practice>
      <practice>Include version-specific context in queries when behavior differs between versions</practice>
      <practice>Combine multiple related questions into single query-docs calls</practice>
      <practice>Cache resolved library IDs during a session for efficiency</practice>
      <practice>Provide context about the task when formulating queries</practice>
    </best_practices>
  </rule>
</rules>

## Exa + Context7 Hybrid Research Rules

<rules>
  <rule priority="CRITICAL" id="exa-context7-hybrid-research">
    <description>
      Combine Context7 and Exa MCP tools for comprehensive package and code research.
      Context7 provides official documentation, while Exa provides fresh web context, code examples, and deep research capabilities.
    </description>

    <decision_matrix>
      <scenario>
        <condition>Looking for official API documentation for a known package</condition>
        <primary_tool>Context7 (resolve-library-id + query-docs)</primary_tool>
      </scenario>

      <scenario>
        <condition>Need latest code examples, tutorials, or blog posts</condition>
        <primary_tool>Exa get_code_context_exa</primary_tool>
        <fallback>Exa web_search_exa</fallback>
      </scenario>

      <scenario>
        <condition>Package not found in Context7</condition>
        <primary_tool>Exa get_code_context_exa</primary_tool>
        <secondary>Exa web_search_exa for official docs</secondary>
      </scenario>

      <scenario>
        <condition>Complex research question requiring synthesis of multiple sources</condition>
        <primary_tool>Exa deep_researcher_start</primary_tool>
      </scenario>

      <scenario>
        <condition>Need content from a specific URL</condition>
        <primary_tool>Exa crawling_exa</primary_tool>
      </scenario>
    </decision_matrix>

    <workflow>
      <step order="1" id="identify-research-type">
        <action>Determine the type of information needed</action>
        <checklist>
          <item>Official API documentation? -> Try Context7 first</item>
          <item>Code examples/tutorials? -> Use Exa get_code_context_exa</item>
          <item>General web information? -> Use Exa web_search_exa</item>
          <item>Deep analysis? -> Use Exa deep_researcher_start</item>
        </checklist>
      </step>

      <step order="2" id="context7-first">
        <action>For package documentation, always try Context7 first</action>
        <tool>mcp__plugin_context7_context7__resolve-library-id</tool>
        <tool>mcp__plugin_context7_context7__query-docs</tool>
        <success_criteria>Got relevant documentation</success_criteria>
      </step>

      <step order="3" id="exa-fallback">
        <action>If Context7 fails or insufficient, use Exa tools</action>
        <tool>mcp__exa__get_code_context_exa</tool>
        <parameters>
          <query>{library_name} {specific_topic} code examples</query>
          <tokensNum>3000-10000</tokensNum>
        </parameters>
        <alternative>
          <tool>mcp__exa__web_search_exa</tool>
          <parameters>
            <query>{library_name} {specific_topic} documentation tutorial</query>
            <numResults>5-10</numResults>
            <livecrawl>preferred</livecrawl>
          </parameters>
        </alternative>
      </step>

      <step order="4" id="deep-research">
        <action>For complex topics, start deep research task</action>
        <tool>mcp__exa__deep_researcher_start</tool>
        <parameters>
          <instructions>{detailed_research_question}</instructions>
          <model>exa-research-pro</model>
        </parameters>
        <follow_up>
          <tool>mcp__exa__deep_researcher_check</tool>
          <parameters>
            <taskId>{taskId_from_start}</taskId>
          </parameters>
          <behavior>Poll until status is "completed"</behavior>
        </follow_up>
      </step>
    </workflow>

    <best_practices>
      <practice>Always try Context7 first for official package documentation</practice>
      <practice>Use get_code_context_exa for finding practical code examples</practice>
      <practice>Use web_search_exa when you need to discover recent articles or tutorials</practice>
      <practice>Use deep_researcher for complex, multi-faceted questions</practice>
      <practice>Use crawling_exa when you need full content from a specific URL</practice>
      <practice>Always cite the source (Context7 or Exa) when providing information</practice>
      <practice>Combine Context7's official docs with Exa's fresh examples for best results</practice>
    </best_practices>
  </rule>
</rules>

## Tool Quick Reference

### Context7 Tools (Official Documentation)

| Tool | Purpose |
|------|---------|
| `mcp__plugin_context7_context7__resolve-library-id` | Get Context7-compatible library ID from package name |
| `mcp__plugin_context7_context7__query-docs` | Query documentation and code examples |

### Exa Tools (Web Research & Code Context)

| Tool | Purpose |
|------|---------|
| `mcp__exa__get_code_context_exa` | Search for code context, examples, libraries, SDKs |
| `mcp__exa__web_search_exa` | Web search with content scraping |
| `mcp__exa__deep_researcher_start` | Start comprehensive AI research task |
| `mcp__exa__deep_researcher_check` | Check deep research task status |
| `mcp__exa__crawling_exa` | Extract full content from specific URLs |
| `mcp__exa__company_research_exa` | Research companies and businesses |
| `mcp__exa__linkedin_search_exa` | Search LinkedIn profiles/companies |

### Package Detection

```javascript
// These are third-party packages - use Context7 + Exa:
import express from 'express'              // npm package
import _ from 'lodash'                     // node_modules
const axios = require('axios')             // external dependency

// These are NOT third-party - no Context7/Exa needed:
import fs from 'fs'                        // Node.js built-in
import { myUtils } from './utils'          // Local project file
```
