# Integration Testing

Integration tests are intentionally not automated in the default pytest run because they require a
real OpenStack cloud and MySQL instance.

Suggested manual flow:

1. Create a disposable MySQL database.
2. Create a least-privilege OpenStack Application Credential scoped to the target project.
3. Export environment variables from `.env.example`.
4. Run `alembic upgrade head`.
5. Run `openstack-inventory-sync healthcheck`.
6. Run `openstack-inventory-sync sync servers`.
7. Inspect the `servers` table and verify `first_seen_at`, `last_seen_at`, and `raw` payloads.
8. Run a full `openstack-inventory-sync sync`.

Do not use username/password OpenStack credentials for this service.
