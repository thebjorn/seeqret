# Gemini Project Analysis: Tilly Monorepo

For general AI/LLM guidance read the AGENTS.md file.

## CRITICAL: Running commands on windows

### ⚠️ MANDATORY: Always prefix commands with `cmd.exe /c`

Use the run_command tool with cwd set to the root of the package you are working in.
Then prefix commands with `cmd.exe /c`

Example:

    run_command(
        command: "cmd.exe /c pnpm test",
        cwd: "packages/db"
    )
