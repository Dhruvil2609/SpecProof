# Production TLS Baseline

- All remote station, browser, API, database, object-storage, telemetry, registry, update,
  backup, and support connections use TLS.
- Production platform startup requires HTTPS and HSTS configuration.
- TLS termination permits TLS 1.2 and 1.3 only; obsolete protocols, compression, renegotiation,
  and weak cipher suites are disabled at the deployment ingress.
- Station API access requires a certificate chaining to an explicitly allow-listed root, the
  client-authentication EKU, certificate validity, online revocation checking, an active
  database identity, and the matching stored SHA-256 certificate fingerprint.
- Private keys remain non-exportable where supported and are rotated through audited station
  certificate rotation.
- Internal PostgreSQL, object storage, OTLP, and backup connections must validate server
  identity and cannot use plaintext production endpoints.

Deployment acceptance records certificate chain, subject alternative names, root hash,
expiry, revocation result, negotiated protocol/cipher, HSTS, and negative tests for expired,
untrusted, wrong-EKU, wrong-host, and revoked certificates.
