# Agent Notes

- This repository is the inventory synchronization service only. Do not add a Flask API here.
- Authentication must remain OpenStack Application Credential only.
- Do not introduce Docker files unless the project requirements change.
- Keep database schema changes in Alembic migrations.
- Unit tests should run without a live OpenStack cloud or MySQL server.
