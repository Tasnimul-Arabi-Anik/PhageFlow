# Security Policy

PhageFlow is a local bioinformatics workflow. It does not provide a network service, authentication layer, or clinical decision system.

## Reporting Security Issues

Please report suspected security issues through GitHub issues unless the report includes sensitive private data. Include:

- the affected PhageFlow commit or release;
- operating system and execution mode;
- the command that triggered the issue;
- whether untrusted input files or archives were involved;
- the observed behavior and expected behavior.

## Data And Execution Boundaries

- Treat input FASTA files, metadata tables, databases, and archives as untrusted files.
- Run PhageFlow in a working directory where generated outputs can be safely created and deleted.
- Avoid running third-party optional tools on sensitive data unless their own security and data-handling properties are acceptable for your environment.
- Do not use PhageFlow reports as clinical, biosafety, regulatory, or wet-lab decision authority.
