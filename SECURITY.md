# Security

## Secrets

- Keep `TYPESAFE_API_KEY` in `.env` or a secret manager.
- Never insert the key into the included HTML or commit it to Git.
- Never place exchange, broker, or wallet credentials in this repository.

## Network boundary

The default API binds to `127.0.0.1`, not a public interface. Add authentication, TLS, rate limiting, and request-size limits before exposing it beyond the local machine.

## Data handling

Audit logs store a SHA-256 hash and length of the query, not the raw query. Market state and constraints are logged because they are needed to reproduce routing decisions. Remove or encrypt those fields if they contain sensitive strategy information.

## Execution boundary

`execution_allowed` is hard-coded to `false`. Keep routing and order execution in separate services with separate credentials and approval controls.

## Reporting

Report security issues privately to the repository owner before public disclosure.
