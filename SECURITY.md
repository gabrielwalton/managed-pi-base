# Security model

Managed Pi assumes the configured GitHub repository and MQTT broker are trusted administrative systems.

- Do not commit `managed-pi.env`, MQTT passwords or SSH private keys.
- Prefer a public read-only application repository when its source can be public.
- For private repositories, use a repository-scoped read-only deploy key rather than a personal access token.
- Restrict the MQTT user so it can read only its own command topic and publish only its own discovery, availability, status and version topics.
- Do not grant the `managedpi` account interactive login access.
- Review application changes before merging to the deployed branch. A trusted application commit runs arbitrary code as `managedpi`, although systemd and sudo restrictions prevent it from becoming root through the deployment interface.
- Rotate credentials before distributing an image outside the trusted local environment.

Report a suspected vulnerability privately to the repository owner rather than publishing secrets or exploit details in an issue.

