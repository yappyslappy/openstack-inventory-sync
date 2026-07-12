#!/usr/bin/env python3
"""Production healthcheck entrypoint."""

from __future__ import annotations

from openstack_inventory_sync.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["healthcheck"]))
