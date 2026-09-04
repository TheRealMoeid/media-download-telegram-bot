# Security Policy

## Overview

Security is important for this project. Since this bot processes user-supplied
URLs and downloads media using external tools and services, vulnerabilities
in areas such as URL handling, command execution, file processing, credentials,
or dependencies may have significant impact.

If you believe you have found a security vulnerability, please report it
privately rather than opening a public GitHub issue.

## Supported Versions

Security fixes are primarily provided for the latest version of the project.

| Version | Supported |
|---------|-----------|
| Latest release | Yes |
| Older releases | No |
| Development branches | No |

## Reporting a Vulnerability

### Please do not

- Open a public GitHub issue for a security vulnerability.
- Publicly disclose the vulnerability before it has been investigated.
- Include real secrets, bot tokens, API keys, or credentials in a report.

### Please report privately

Use GitHub's private security vulnerability reporting mechanism if it is
available for this repository.

If private vulnerability reporting is not available, contact the repository
maintainer through a private channel rather than publicly disclosing the issue.

### What to include

A useful security report should contain as much of the following information
as possible:

- A clear description of the vulnerability.
- The affected component or file.
- The affected version or commit.
- Steps to reproduce the vulnerability.
- A minimal proof of concept, when safe to provide.
- The expected behavior.
- The actual behavior.
- The potential security impact.
- Any relevant logs or error messages, with secrets and personal information
  removed.
- A suggested mitigation or fix, if known.

For example:

```text
Affected component:
bot/handlers.py

Affected functionality:
URL processing / media download

Description:
A specially crafted URL causes ...

Steps to reproduce:
1. ...
2. ...
3. ...

Impact:
An attacker may be able to ...

Suggested mitigation:
Validate/restrict the URL before passing it to ...
