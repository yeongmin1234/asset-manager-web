"""Existing new_scm_dev baseline, adopted without recreating its 51 business tables.

Revision ID: 20260729_0012
Revises:
"""
revision = "20260729_0012"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    raise RuntimeError("Existing SCM baseline must never be applied to an empty database")


def downgrade():
    raise RuntimeError("Existing SCM baseline cannot be rolled back here")

