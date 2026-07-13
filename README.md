# openstack-inventory-sync

`openstack-inventory-sync` collects OpenStack inventory with Application Credentials and
synchronizes resource state into MySQL. It is only the sync service; it does not include a Flask API.

## Multi-Project Architecture

```text
OpenStack project AppDev  -> appdev.env  -> openstack-inventory-sync --env-file appdev.env  -> MySQL
OpenStack project AppTest -> apptest.env -> openstack-inventory-sync --env-file apptest.env -> MySQL
```

Each OpenStack Application Credential is project-scoped, so run one sync instance per project. Each
instance has one environment file, one `INVENTORY_SCOPE`, one configured OpenStack project ID, and
one source-specific lock file. The shared MySQL database stores all scopes in the same schema.

Every inventory table is source-owned through `inventory_source_id`. Repository writes, reactivation,
hard deletion, and soft deletion include the current source. A sync for `appdev` cannot mark
`apptest` resources deleted because missing-resource comparisons only query rows for the current
`inventory_sources.id`.

Public/shared flavors and public/shared/community images are stored as one copy per inventory source.
This is intentionally simple and safe: no synchronization run relies on global OpenStack UUID
uniqueness across projects.

## Supported Resources

- projects
- flavors
- images
- networks
- subnets
- security groups and rules
- ports
- servers, tags, and addresses
- volumes and attachments
- floating IPs

## Configuration

Copy `.env.example` for each project, for example:

```text
/etc/openstack-inventory-sync/appdev.env
/etc/openstack-inventory-sync/apptest.env
```

Existing shell environment variables override values loaded from an env file. This is the default
`python-dotenv` precedence and is useful for temporary local overrides.

AppDev example:

```dotenv
INVENTORY_SCOPE=appdev
OPENSTACK_PROJECT_ID=<appdev-project-uuid>
OPENSTACK_PROJECT_NAME=DF-APPDEV
INVENTORY_LOCK_DIR=/tmp/openstack-inventory-sync

OS_AUTH_URL=https://identity.internal.ebsicloud.com/v3
OS_APPLICATION_CREDENTIAL_ID=<appdev-credential-id>
OS_APPLICATION_CREDENTIAL_SECRET=<appdev-credential-secret>
OS_REGION_NAME=RegionOne
OS_INTERFACE=internal
OS_IDENTITY_API_VERSION=3

MYSQL_HOST=mysql-server.ebsi.corp
MYSQL_PORT=3306
MYSQL_DATABASE=openstack_inventory
MYSQL_USERNAME=openstack_inventory
MYSQL_PASSWORD=<mysql-password>
MYSQL_CHARSET=utf8mb4
MYSQL_POOL_SIZE=5
MYSQL_MAX_OVERFLOW=10
MYSQL_POOL_RECYCLE=1800
```

AppTest example:

```dotenv
INVENTORY_SCOPE=apptest
OPENSTACK_PROJECT_ID=<apptest-project-uuid>
OPENSTACK_PROJECT_NAME=DF-APPTEST
INVENTORY_LOCK_DIR=/tmp/openstack-inventory-sync

OS_AUTH_URL=https://identity.internal.ebsicloud.com/v3
OS_APPLICATION_CREDENTIAL_ID=<apptest-credential-id>
OS_APPLICATION_CREDENTIAL_SECRET=<apptest-credential-secret>
OS_REGION_NAME=RegionOne
OS_INTERFACE=internal
OS_IDENTITY_API_VERSION=3

MYSQL_HOST=mysql-server.ebsi.corp
MYSQL_PORT=3306
MYSQL_DATABASE=openstack_inventory
MYSQL_USERNAME=openstack_inventory
MYSQL_PASSWORD=<mysql-password>
```

Authentication remains Application Credential only. Do not set `OS_USERNAME`, `OS_PASSWORD`,
`OS_PROJECT_NAME`, `OS_PROJECT_ID`, tenant, or domain variables. `OPENSTACK_PROJECT_ID` is inventory
metadata and a safety check; it is never passed to `openstack.connect()`.

After authentication, the service attempts to read the authenticated project ID from the OpenStack
SDK session/token. If the SDK exposes a project ID and it differs from `OPENSTACK_PROJECT_ID`, the
sync stops before writing inventory. If the SDK cannot expose it reliably, the service logs a
sanitized warning and retains the explicit configured source context.

Secrets are never written to logs. Database URLs are logged with passwords hidden.

## Local Development

Use Python 3.12 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pre-commit install
```

Run checks:

```bash
black .
ruff check .
mypy src tests
pytest
```

Run migrations:

```bash
alembic upgrade head
```

Validate one project config without creating an inventory source:

```bash
openstack-inventory-sync \
  --env-file /etc/openstack-inventory-sync/appdev.env \
  validate-config
```

Run a full sync:

```bash
openstack-inventory-sync \
  --env-file /etc/openstack-inventory-sync/appdev.env \
  sync
```

Run one resource sync:

```bash
openstack-inventory-sync \
  --env-file /etc/openstack-inventory-sync/appdev.env \
  sync servers
```

Delete missing rows for only the active source instead of soft-marking them:

```bash
openstack-inventory-sync \
  --env-file /etc/openstack-inventory-sync/appdev.env \
  sync --remove-missing
```

## Inventory Sources

The first successful sync for a scope creates a row in `inventory_sources` with:

- `scope_key`
- `openstack_project_id`
- `openstack_project_name`
- `region_name`
- `auth_url`
- success/failure timestamps

Application Credential IDs and secrets are not stored.

Useful database filters:

```sql
SELECT s.*
FROM servers AS s
JOIN inventory_sources AS src ON src.id = s.inventory_source_id
WHERE src.scope_key = 'appdev'
  AND s.is_deleted = false;
```

```sql
SELECT src.scope_key, COUNT(*) AS active_servers
FROM servers AS s
JOIN inventory_sources AS src ON src.id = s.inventory_source_id
WHERE s.is_deleted = false
GROUP BY src.scope_key;
```

## Upgrading Existing Single-Project Installations

The new migration creates `inventory_sources` and adds `inventory_source_id` to existing inventory
tables. It will not guess which project existing rows belong to.

For an existing database with rows, run the migration with explicit backfill values in the
environment:

```bash
export INVENTORY_SCOPE=appdev
export OPENSTACK_PROJECT_ID=<existing-project-uuid>
export OPENSTACK_PROJECT_NAME=DF-APPDEV
export OS_AUTH_URL=https://identity.internal.ebsicloud.com/v3
export OS_REGION_NAME=RegionOne
alembic upgrade head
```

If those values are absent and existing rows are detected, the migration aborts before changing the
schema. For a new empty installation, no backfill values are required.

After migration:

```bash
openstack-inventory-sync --env-file /etc/openstack-inventory-sync/appdev.env validate-config
openstack-inventory-sync --env-file /etc/openstack-inventory-sync/appdev.env sync
```

## Troubleshooting

### `Data too long for column 'version_num'`

Alembic's default MySQL `alembic_version.version_num` column is `VARCHAR(32)`. If a migration uses a
revision identifier longer than 32 characters, MySQL can fail with:

```text
pymysql.err.DataError: (1406, "Data too long for column 'version_num'")
```

Revision identifiers are intentionally kept short, stable, and at most 32 characters. Do not modify
deployed database state automatically to work around this; fix the migration revision identifier
before applying the migration.

## Adding Or Disabling Projects

To add a second project:

1. Create a project-scoped OpenStack Application Credential for that project.
2. Create `/etc/openstack-inventory-sync/<scope>.env` with a unique `INVENTORY_SCOPE`.
3. Run `validate-config`.
4. Enable a timer instance.

To disable a project, stop and disable its timer. You can also set `inventory_sources.is_active` to
false for reporting, but do not delete source rows unless you intentionally want to remove that
source's inventory history.

## Production Scheduling

Template unit files are provided:

```text
systemd/openstack-inventory-sync@.service
systemd/openstack-inventory-sync@.timer
```

Install them into `/etc/systemd/system/`, then enable one timer per project:

```bash
systemctl daemon-reload
systemctl enable --now openstack-inventory-sync@appdev.timer
systemctl enable --now openstack-inventory-sync@apptest.timer
```

The service instance loads `/etc/openstack-inventory-sync/%i.env` and runs:

```bash
openstack-inventory-sync \
  --env-file /etc/openstack-inventory-sync/%i.env \
  sync
```

Timers include `RandomizedDelaySec` so all projects do not synchronize at the same instant. Different
scopes can run concurrently. Two syncs for the same scope are blocked by a source-specific lock such
as `/tmp/openstack-inventory-sync/openstack-inventory-sync-appdev.lock`.

Check status and logs:

```bash
systemctl status openstack-inventory-sync@appdev.service
journalctl -u openstack-inventory-sync@appdev.service
journalctl -u openstack-inventory-sync@apptest.service
```

## Testing Without OpenStack Or MySQL

Unit tests use fakes and SQLite in memory, so they do not require a real OpenStack cloud or MySQL
server. Integration testing guidance lives in `tests/integration/README.md`.
