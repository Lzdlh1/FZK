"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False, server_default=sa.text("'craftsman'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("univer_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "variables",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("placeholder", sa.Text(), nullable=False),
        sa.Column("sheet", sa.Text(), nullable=False),
        sa.Column("cell", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("data_type", sa.Text(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("depends_on", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False, server_default=sa.text("'{}'")),
        sa.UniqueConstraint("template_id", "name", name="uq_variables_template_name"),
    )

    op.create_table(
        "variable_prompts",
        sa.Column("variable_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("variables.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("output_constraints", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("confidence_threshold", sa.Float(), nullable=False, server_default=sa.text("0.7")),
        sa.Column("post_process", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    op.create_table(
        "few_shot_refs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("variable_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("variables.id", ondelete="CASCADE"), nullable=False),
        sa.Column("image_oid", sa.Text(), nullable=False),
        sa.Column("expected_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )

    op.create_table(
        "mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("templates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("drawing_field", sa.Text(), nullable=False),
        sa.Column("variable_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("variables.id"), nullable=False),
        sa.Column("auto_matched", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "preset_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("expression_template", sa.Text(), nullable=False),
        sa.Column("params", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("output_unit", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("built_in", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "formulas",
        sa.Column("variable_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("variables.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("expression", sa.Text(), nullable=False),
        sa.Column("preset_rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("preset_rules.id"), nullable=True),
        sa.Column("dependencies", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False, server_default=sa.text("'{}'")),
    )

    op.create_table(
        "database_params",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("field", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.UniqueConstraint("category", "model", "field", "version", name="uq_database_params_field"),
    )

    op.create_table(
        "rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.create_table(
        "ai_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("api_key_enc", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("healthy", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_check_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "parse_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("templates.id"), nullable=False),
        sa.Column("drawing_oid", sa.Text(), nullable=False),
        sa.Column("drawing_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "history_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("parse_job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("parse_jobs.id"), nullable=False),
        sa.Column("drawing_oid", sa.Text(), nullable=False),
        sa.Column("template_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("db_version", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("rule_version", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("ai_raw_result", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("manual_edits", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("output_oid", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("history_snapshots")
    op.drop_table("parse_jobs")
    op.drop_table("ai_providers")
    op.drop_table("rules")
    op.drop_table("database_params")
    op.drop_table("formulas")
    op.drop_table("preset_rules")
    op.drop_table("mappings")
    op.drop_table("few_shot_refs")
    op.drop_table("variable_prompts")
    op.drop_table("variables")
    op.drop_table("templates")
    op.drop_table("users")
