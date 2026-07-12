# openstack-inventory-sync

`openstack-inventory-sync` collects inventory from OpenStack with Application Credentials and
synchronizes the current resource state into MySQL. It is intentionally only the inventory sync
service; it does not include a Flask API.

## Architecture

```text
OpenStack
    |
    v
openstack-inventory-sync
    |
    v
MySQL
    |
    v
Flask middleware API
```

The CLI creates one OpenStack SDK connection per run, one SQLAlchemy engine/session factory, and
then executes resource-specific synchronizers in transactions. Each synchronizer fetches OpenStack
resources, serializes SDK objects into ORM payloads, upserts changed rows, and marks missing rows as
deleted unless `--remove-missing` is used.

## Supported Resources

- projects
- flavors
- images
- networks
- subnets
- security groups
- ports
- servers
- volumes
- floating IPs

## Configuration

Copy `.env.example` to `.env` for local testing and fill in the values.

OpenStack authentication is Application Credential only:

```dotenv
OS_AUTH_URL=
OS_APPLICATION_CREDENTIAL_ID=
OS_APPLICATION_CREDENTIAL_SECRET=
OS_REGION_NAME=RegionOne
OS_INTERFACE=internal
OS_IDENTITY_API_VERSION=3
```

Do not set username/password, project, tenant, or domain environment variables. Application
Credentials are already project-scoped, and this service does not pass project-scoping arguments to
`openstack.connect()`.

MySQL settings:

```dotenv
MYSQL_HOST=
MYSQL_PORT=3306
MYSQL_DATABASE=openstack_inventory
MYSQL_USERNAME=
MYSQL_PASSWORD=
MYSQL_CHARSET=utf8mb4
MYSQL_POOL_SIZE=5
MYSQL_MAX_OVERFLOW=10
MYSQL_POOL_RECYCLE=1800
```

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
ruff check .
black --check .
mypy src
pytest
```

Run migrations:

```bash
alembic upgrade head
```

Run a full sync:

```bash
openstack-inventory-sync sync
```

Run one resource sync:

```bash
openstack-inventory-sync sync servers
```

Delete missing rows instead of soft-marking them:

```bash
openstack-inventory-sync sync --remove-missing
```

Check database connectivity:

```bash
openstack-inventory-sync healthcheck
```

List resource names:

```bash
openstack-inventory-sync list-resources
```

## Production Scheduling

Example systemd unit and timer files are provided in `systemd/`.

1. Install the project into `/opt/openstack-inventory-sync`.
2. Create `/etc/openstack-inventory-sync/openstack-inventory-sync.env` from `.env.example`.
3. Run `alembic upgrade head` with the production environment loaded.
4. Copy the service and timer units into `/etc/systemd/system/`.
5. Enable the timer:

```bash
systemctl daemon-reload
systemctl enable --now openstack-inventory-sync.timer
```

## Testing Without OpenStack or MySQL

Unit tests use fakes and SQLite in memory, so they do not require a real OpenStack cloud or MySQL
server. Integration testing guidance lives in `tests/integration/README.md`.
