# Project Mandates

1. **Deployment Workflow**: All code changes MUST be proposed via a **GitHub Pull Request** using the GitHub MCP tools. Direct commits to protected branches are strictly prohibited.
2. **Tooling**: Use the GitHub MCP server (`mcp_github_*`) for creating branches, pushing files, and opening pull requests. Do not use local `git push` if it requires manual credential entry.
3. **Execution Environment**: Code MUST only be run in Cloud Run. Never attempt to run or test the code in the local environment.
