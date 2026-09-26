# AI Control Studio

An open-source native macOS workspace for AI gateways, MCPs, Claude Code configuration and optional Jev decision assistance. Built with AppKit, WebKit and Python's standard library.

## Screenshots and settings

![AI Control Studio Connections](docs/screenshots/connections.png)

Explore the [illustrated settings guide](docs/SETTINGS.md) for all six sections, credential setup, MCP prerequisites, Markdown editing and Jev controls. Screenshots use a public-safe demo profile, not live user accounts.

| MCP Catalog | Code Studio |
| --- | --- |
| ![MCP Catalog](docs/screenshots/mcp-catalog.png) | ![Code Studio](docs/screenshots/code-studio.png) |

| Gateway profiles | Mods → Jev |
| --- | --- |
| ![Gateway profiles](docs/screenshots/gateway-profiles.png) | ![Jev settings](docs/screenshots/mods-jev.png) |

![Secret Manager](docs/screenshots/secret-manager.png)

## Features

- **Connections:** switch Claude Desktop, Claude Code and Codex independently between a configured gateway and their normal provider. Consumer ChatGPT gateway routing is unavailable.
- **Gateway profiles:** named custom, LiteLLM, Bifrost and local Ollama endpoints with Keychain, environment or executable-helper credential references.
- **MCP Catalog:** searchable public connector metadata, prerequisite guides and local package review before registration. Registration is separate from authentication.
- **Code Studio:** inspect and edit local agents, skills, commands, plugins and hooks. Import skills from public GitHub sources after file review.
- **Mods → Jev:** OpenRouter model and credential settings, optional skill suggestions, Tavily discovery fallback, approval-based decision assistance and recent activity.
- **Secret Manager:** add, replace and remove named credentials directly in macOS Keychain. Secret values never pass through the HTML interface or enter the reference registry.

## Build and run

Requires macOS, Xcode Command Line Tools and Python **3.11+**. Install and authenticate Claude Code or Codex separately if you use those integrations. This app does not install runtimes or proxy servers.

```sh
bash build.sh
open "dist/AI Control Studio.app"
```

The build records your Python runtime location in the local app bundle. Build outputs are ignored by Git. A locally built app is not signed or notarized; prebuilt distribution is not provided yet.

## Local Ollama

Open **Gateway profiles → Gateway profile → Ollama**, load available models, choose a tool-capable model and save. The localhost endpoints and non-secret credential placeholder are prefilled. Saving can update already enabled gateway clients and offer a normal quit/reopen; terminal clients need a fresh session. Use **Connections** to enable additional clients. The app does not install Ollama or download models. See the [settings guide](docs/SETTINGS.md#local-ollama).

## Configure Jev through OpenRouter

1. Open **Secret Manager → OpenRouter → Add value**. Enter your key in the native secure field.
2. Open **Mods → Jev**. Select **macOS Keychain** and the **OpenRouter** secret reference.
3. Choose a Jev model (default `typesafe/jev-1.13`) and test the connection.
4. Apply the desired controls. Automatic skill suggestions share submitted prompts and bounded skill metadata with OpenRouter, and are off initially.

Decision assistance uses `ask_jev_decision` and requires approval for every request. Claude Code **2.1.199+** supports the required per-call interaction annotation. A SessionStart hook provides usage guidance, and a PreToolUse hook asks before sending decision evidence. Other clients must support MCP form elicitation or the decision call is refused. No result authorizes consequential actions.

If no installed skill matches, optional Tavily discovery searches a fixed general category rather than sending the full prompt. Results remain unverified until fetched and reviewed. Installation requires confirmation. Configure a Tavily credential in Keychain and its HTTP MCP endpoint first. Reuse of Claude Code's existing Tavily OAuth sign-in is **opt-in**, not an implicit credential fallback.

## Local storage and privacy

- App state and private backups: `~/Library/Application Support/AI Control Studio/`.
- Jev settings: `~/.claude/ai-control-jev.json`; reference IDs and controls only.
- Jev activity: `~/.claude/ai-control-jev-status.json`; last 20 outcomes/timings, no prompts or credentials.
- API secrets: macOS Keychain services prefixed `ai-control-studio.secret.`.
- Claude Code files: standard user/project `.claude` directories and `~/.claude.json`.

The app starts with **no gateway configured** and has no bundled API key, organization endpoint or private profile. It does not export Keychain data to repositories. Existing helpers, environment values and client-managed OAuth stores remain owned by those clients; this release does not silently migrate every pre-existing credential into Keychain.

MCP packages and imported skills can contain executable code. The app previews downloaded files and does not execute installation scripts, but the selected AI client can launch registered servers and invoke permitted tools. Review publisher provenance, dependencies, permissions and instructions before confirming an install.

## Tests

```sh
python3 -m unittest discover -p 'test_*.py'
node check_ui.cjs
```

Tests use temporary configuration files and mocked decision calls, not live API credentials. `Test OpenRouter connection` in the app sends a synthetic request when explicitly clicked.

## Project layout

`main.swift` and native views implement the Mac shell. `studio.html` provides the configuration editors. Python modules handle profiles, client settings, MCP inventory, package and skill import, Jev decisions and read-only Tavily search. `SecretVault.swift` writes Keychain values; `secret_store.py` resolves named credential references at runtime.

## Scope and limitations

This is a local Mac management tool, not centralized enterprise administration. Search is scoped to each section. Effective Claude Code skills can differ from file inventory. Public catalog refresh depends on the publisher's page format; third-party entries, authentication policies and compatibility can change. Claude Desktop third-party inference availability depends on the installed client deployment. Package signatures are not verified by the local importer.

## Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and [LICENSE](LICENSE). Software is MIT licensed. Third-party names, logos and catalog material remain subject to their owners' rights; see [NOTICE.md](NOTICE.md). No affiliation with the named providers is implied.
