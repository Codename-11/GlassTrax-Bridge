# Database Migrations

This directory contains Alembic database migrations for GlassTrax Bridge.

## Quick Reference

```powershell
# Check current version
python32\python.exe -m alembic current

# View migration history
python32\python.exe -m alembic history

# Upgrade to latest
python32\python.exe -m alembic upgrade head

# Downgrade one revision
python32\python.exe -m alembic downgrade -1

# Create new migration (auto-detect changes)
python32\python.exe -m alembic revision --autogenerate -m "Description of changes"

# Create empty migration (manual)
python32\python.exe -m alembic revision -m "Description of changes"
```

## Before First Use

If you have an existing database without Alembic tracking:

```powershell
# Stamp the database as being at the initial revision
python32\python.exe -m alembic stamp head
```

## Adding New Models

1. Create the model in `api/models/`
2. Import it in `api/models/__init__.py`
3. Import it in `migrations/env.py`
4. Run: `python32\python.exe -m alembic revision --autogenerate -m "Add model_name table"`
5. Review the generated migration file
6. Run: `python32\python.exe -m alembic upgrade head`

## SQLite Limitations

SQLite has limited ALTER TABLE support. Alembic uses "batch mode" to work around this:
- Column additions work normally
- Column removals, renames, and type changes use table recreation
- This is handled automatically by `render_as_batch=True` in env.py

## Production Deployment

1. Always backup `data/glasstrax_bridge.db` before migrations
2. Test migrations on a copy of production data first
3. Run `alembic upgrade head` as part of deployment
4. The app will warn on startup if migrations are pending
