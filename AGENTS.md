# Agent Notes

- This repository is the inventory synchronization service only. Do not add a Flask API here.
- Authentication must remain OpenStack Application Credential only.
- Never pass `OPENSTACK_PROJECT_ID` into Application Credential authentication.
- All project-scoped database operations require an inventory source context.
- Never introduce unscoped update, delete, reactivation, or soft-deletion logic.
- Do not introduce Docker files unless the project requirements change.
- Add new Alembic migrations rather than modifying deployed migrations.
- Run multi-source isolation tests before completing changes.
- Unit tests should run without a live OpenStack cloud or MySQL server.
