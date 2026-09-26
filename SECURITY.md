# Security

Never attach API keys, OAuth tokens, environment files, client configuration dumps or private backups to issues or pull requests. Report suspected credential exposure privately to the maintainer through GitHub's private vulnerability reporting when enabled; do not publish secret values.

Secret Manager uses macOS Keychain through Apple's Security framework. The WebKit bridge accepts credential reference IDs, not secret values. The native password dialog writes directly to Keychain. Helper scripts contain service/account references only; Python captures credential output privately for an authorized API request.

New installations use app-owned Keychain entries. Existing client OAuth credentials are not read automatically; Tavily credential reuse requires explicitly opting in. Automatic Jev suggestions are off initially. Decision assistance requires per-request user approval in a supported client. Activity stores outcomes and timing, not evidence or secrets.

Local client configurations may already contain plaintext secrets managed by another tool. This app does not guarantee those external files are secret-free. Private backups remain outside the repository and should be treated as sensitive. Do not upload them.

Review downloaded packages and skills before installation. This tool validates structure and archive paths but does not establish publisher trust or verify all package signatures.
