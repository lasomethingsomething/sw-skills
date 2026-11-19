# Privacy boundaries and deployment review

The agent follows "Use during the prototype". "Before sharing or deploying" is for the team that deploys the skill.

This prototype is a skill used by an AI host. Its instructions are not a technical enforcement layer, and privacy depends on the host, model provider, connectors, project, and operator. The bundled search script runs locally and contains no network calls, telemetry, persistent logging, or identifier generation. This does not mean the AI host, shell, editor, operating system, other tools, or provider do the same.

## Use during the prototype

- Make AI use and any local project inspection opt-in. Before inspection, explain the intended scope, whether the agent or its tools may transmit information, the provider when known, and unknowns. A user's agreement to use a feature is not by itself a GDPR legal basis for processing other people's data.
- Start with exact product versions, generic technical descriptions, public upgrade guidance, and synthetic or anonymized examples. Ask for the minimum needed. Do not request customer names, email addresses, order or payment details, production database contents, logs, credentials, tokens or secrets.
- Do not read `.env` files, credential files, authentication settings, production database dumps, or bulk logs as part of planning. Do not paste data or code into web search, issues, comments, or a model prompt. If a relevant file might include personal information, keep it out of external services until the user has arranged appropriate authorization and safeguards. Redaction is not guaranteed to detect everything; pseudonymized information can still be personal data.
- The search command's `--query` argument can be recorded in shell history or visible in process listings. Use generic terms only. `--query-stdin` avoids passing the query as an argument, but stdin, shell pipelines, the host agent, or terminal logging may still expose it. Search output does not echo the query or an absolute local path; it can still contain text from public source documents.
- Public issue reports can identify people or contain personal data. Open issues only when needed and avoid copying reporters, comments, logs, screenshots, or identifiable information into outputs. Public availability does not itself remove data-protection obligations.
- Do not enable telemetry, analytics, session identifiers, or plan uploads in the prototype. Do not silently save plans or conversations. If the user asks to save a plan, minimize its content, use their chosen location and explain that the host or service controls access, retention and deletion. An anonymized plan is not guaranteed merely because obvious identifiers are removed.

## Before sharing or deploying

The responsible team should document the actual data flows and obtain a privacy review before collecting real user or shop information. In particular, establish:

1. Who controls and processes data, the purposes, categories of people and data, and a valid legal basis for each processing activity; cover transparency notices and applicable rights workflows.
2. The agent/model provider and any subprocessors, processing and storage locations, logging and training settings, security controls, retention and deletion capabilities; make appropriate processor agreements where required. Do not assume changing a skill controls provider behavior.
3. Whether any international transfer occurs and which applicable transfer mechanism and safeguards are required. Assess whether a data protection impact assessment is necessary for the actual deployment.
4. How access, retention, deletion, data-subject requests, correction, incident handling and periodic review work across every involved system, including user-generated plans and any public source indexes.
5. Whether telemetry is justified at all. A session or machine identifier can be personal data even if pseudonymous; use a separate purpose, data minimization, an appropriate legal basis, clear notice and documented retention if telemetry is later introduced.
6. How public issue metadata is reviewed and removed if necessary. Removing a file from the latest Git tree does not erase previous public Git history, forks, caches or copies; coordinate any remediation with the repository owner.

Review with Shopware's privacy or legal team and the deployment owner. No skill or code change alone certifies GDPR compliance.
