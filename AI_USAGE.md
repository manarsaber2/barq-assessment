# AI Usage Disclosure

- **Tool/model**: Gemini
- **Purpose**: Assisting with Markdown documentation formatting and initial script boilerplate structure.
- **Files or decisions affected**: `validate.py`, `failure_test.py`, `decisions.md`, `security.md`.
- **What you changed or rejected**: Rejected standard Nginx timeout recommendations in favor of custom retry parameters (`fail_timeout=1s`, `proxy_connect_timeout 1s`), fine-tuned Python polling waits for bounded health checks, and manually verified Docker network isolation rules using container inspection commands.
- **How you independently verified it**: Ran the entire test suite (`validate.py` and `failure_test.py`) locally, inspecting Docker network states, container lifecycle responses, and Nginx logs to prove 100% failover success and data persistence.
- **Related commit**: 
  - `test(resilience): implement failure and recovery automation with zero-downtime nginx failover`
  - `docs(decisions): document architecture decisions, trade-offs, and limits`