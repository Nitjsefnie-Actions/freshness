# Security

Report vulnerabilities privately through a
[security advisory on this repository](https://github.com/Nitjsefnie-Actions/freshness/security/advisories/new).
Include the action commit SHA, the calling workflow and the observed behavior
needed to reproduce the problem. Use a repository you control and keep
sensitive details out of public issues.

The action and this repository's workflows are in scope, especially a check
that passes a head it should refuse. The action reads the default branch's
rules with the job's token and runs only the code under its immutable
`github.action_path`; it executes no script from the consumer's checkout and
writes nothing to the repository or its pull requests.
