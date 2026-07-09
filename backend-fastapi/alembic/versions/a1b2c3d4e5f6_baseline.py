"""baseline: 16-table schema derived from JPA entities (no guessing)

Revision ID: a1b2c3d4e5f6
Revises: None
Create Date: 2026-07-06

HOW TO USE THIS MIGRATION
─────────────────────────
FOR AN EXISTING DATABASE (the normal case — Hibernate created the schema):
    alembic stamp a1b2c3d4e5f6

  This marks the DB as already being at this revision WITHOUT running any DDL.
  Then verify no drift:
    alembic check

FOR A FRESH DATABASE:
    alembic upgrade head

  This creates all 16 tables from scratch in dependency order.

SCHEMA AUTHORITY
────────────────
This migration was derived by reading the JPA entity annotations directly
(not docs/).  Column names use Hibernate's SpringPhysicalNamingStrategy
(camelCase → snake_case).  Column types use Hibernate's default PostgreSQL
dialect mappings.  Every table, column, constraint, and FK here was verified
against the Java source — see migration-notes/00-foundation.md for the
full env-var → column mapping table.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. roles ──────────────────────────────────────────────────────────────
    op.create_table(
        "roles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # ── 2. campuses ───────────────────────────────────────────────────────────
    op.create_table(
        "campuses",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("location", sa.String(150), nullable=False),
        # explicit @Column(name = "email_domain") in Java
        sa.Column("email_domain", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 3. users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        # fullName → full_name (SpringPhysicalNamingStrategy)
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(150), nullable=False),
        # No @Column(length) → Hibernate default VARCHAR(255)
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("campus_id", sa.BigInteger(), nullable=True),
        # primitive boolean isActive → is_active NOT NULL
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("no_show_count", sa.Integer(), nullable=False),
        # Java double (primitive) → DOUBLE PRECISION NOT NULL
        sa.Column("pending_penalty_amount", sa.Double(), nullable=False),
        sa.Column("account_status", sa.String(30), nullable=False),
        sa.Column("phone", sa.String(15), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("fcm_token", sa.String(300), nullable=True),
        sa.ForeignKeyConstraint(["campus_id"], ["campuses.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    # ── 4. outlets ────────────────────────────────────────────────────────────
    op.create_table(
        "outlets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("campus_id", sa.BigInteger(), nullable=False),
        sa.Column("manager_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("avg_prep_time", sa.Integer(), nullable=False),
        sa.Column("photo_url", sa.Text(), nullable=True),
        sa.Column("launched_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("opening_time", sa.Time(), nullable=True),
        sa.Column("closing_time", sa.Time(), nullable=True),
        # Bank details
        sa.Column("bank_account_number", sa.String(30), nullable=True),
        sa.Column("bank_ifsc_code", sa.String(11), nullable=True),
        sa.Column("bank_account_holder_name", sa.String(150), nullable=True),
        sa.Column("razorpay_fund_account_id", sa.String(50), nullable=True),
        sa.Column("razorpay_contact_id", sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(["campus_id"], ["campuses.id"]),
        sa.ForeignKeyConstraint(["manager_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 5. menu_items ─────────────────────────────────────────────────────────
    op.create_table(
        "menu_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("outlet_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("price", sa.Double(), nullable=False),
        sa.Column("prep_time", sa.Integer(), nullable=False),
        sa.Column("photo_url", sa.String(500), nullable=True),
        # primitive boolean isAvailable → is_available NOT NULL
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["outlet_id"], ["outlets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 6. pickup_slots ───────────────────────────────────────────────────────
    op.create_table(
        "pickup_slots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("outlet_id", sa.BigInteger(), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("slot_date", sa.Date(), nullable=False),
        sa.Column("max_orders", sa.Integer(), nullable=False),
        sa.Column("current_orders", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        # Hibernate @Version → BigInteger NOT NULL; SQLAlchemy version_id_col handles the rest
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["outlet_id"], ["outlets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 7. orders ─────────────────────────────────────────────────────────────
    op.create_table(
        "orders",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        # Nullable — counter orders have no linked student account
        sa.Column("student_id", sa.BigInteger(), nullable=True),
        sa.Column("outlet_id", sa.BigInteger(), nullable=False),
        # Nullable — counter orders have no pickup slot
        sa.Column("pickup_slot_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("total_amount", sa.Double(), nullable=False),
        sa.Column("payment_mode", sa.String(20), nullable=False),
        sa.Column("payment_status", sa.String(20), nullable=False),
        sa.Column("ready_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("pickup_otp", sa.String(4), nullable=True),
        # explicit @Column(name = "order_source") in Java
        sa.Column("order_source", sa.String(10), nullable=False),
        sa.Column("customer_name", sa.String(120), nullable=True),
        sa.ForeignKeyConstraint(["outlet_id"], ["outlets.id"]),
        sa.ForeignKeyConstraint(["pickup_slot_id"], ["pickup_slots.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 8. order_items ────────────────────────────────────────────────────────
    op.create_table(
        "order_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("menu_item_id", sa.BigInteger(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price_at_order", sa.Double(), nullable=False),
        sa.ForeignKeyConstraint(["menu_item_id"], ["menu_items.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 9. payments ───────────────────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        # Null for penalty payments
        sa.Column("order_id", sa.BigInteger(), nullable=True),
        # explicit @Column(name = "penalty_user_id") in Java
        sa.Column("penalty_user_id", sa.BigInteger(), nullable=True),
        sa.Column("razorpay_order_id", sa.String(100), nullable=False),
        sa.Column("razorpay_payment_id", sa.String(100), nullable=True),
        sa.Column("amount", sa.Double(), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("razorpay_order_id"),
    )

    # ── 10. outlet_payouts ────────────────────────────────────────────────────
    op.create_table(
        "outlet_payouts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("outlet_id", sa.BigInteger(), nullable=False),
        sa.Column("gross_amount", sa.Double(), nullable=False),
        sa.Column("commission_rate", sa.Double(), nullable=False),
        sa.Column("commission_amount", sa.Double(), nullable=False),
        sa.Column("net_amount", sa.Double(), nullable=False),
        sa.Column("order_count", sa.Integer(), nullable=False),
        sa.Column("cash_gross_amount", sa.Double(), nullable=False),
        sa.Column("cash_order_count", sa.Integer(), nullable=False),
        sa.Column("razorpay_payout_id", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("note", sa.String(300), nullable=True),
        sa.ForeignKeyConstraint(["outlet_id"], ["outlets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 11. outlet_ratings ────────────────────────────────────────────────────
    op.create_table(
        "outlet_ratings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("outlet_id", sa.BigInteger(), nullable=False),
        sa.Column("student_id", sa.BigInteger(), nullable=False),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("comment", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["outlet_id"], ["outlets.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        # @UniqueConstraint(columnNames = {"order_id"}) in Java
        sa.UniqueConstraint("order_id", name="uq_outlet_ratings_order_id"),
    )

    # ── 12. notifications ─────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        # columnDefinition = "TEXT"
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        # primitive boolean isRead → is_read NOT NULL
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 13. email_otp_tokens ──────────────────────────────────────────────────
    op.create_table(
        "email_otp_tokens",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(150), nullable=False),
        sa.Column("otp_code", sa.String(6), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        # primitive boolean → NOT NULL
        sa.Column("used", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 14. admin_applications ────────────────────────────────────────────────
    op.create_table(
        "admin_applications",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("applicant_email", sa.String(150), nullable=False),
        # columnDefinition = "TEXT"
        sa.Column("designation", sa.Text(), nullable=False),
        # Base64 ID card photo — TEXT (spec §4.5: not object storage)
        sa.Column("id_card_photo_url", sa.Text(), nullable=False),
        sa.Column("campus_name", sa.String(150), nullable=False),
        sa.Column("campus_location", sa.String(200), nullable=False),
        sa.Column("campus_email_domain", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_campus_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_campus_id"], ["campuses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 15. outlet_applications ───────────────────────────────────────────────
    op.create_table(
        "outlet_applications",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("manager_name", sa.String(120), nullable=False),
        sa.Column("manager_email", sa.String(150), nullable=False),
        sa.Column("outlet_name", sa.String(150), nullable=False),
        sa.Column("outlet_description", sa.Text(), nullable=True),
        sa.Column("avg_prep_time", sa.Integer(), nullable=False),
        # Base64 license doc — TEXT (spec §4.5)
        sa.Column("license_doc_url", sa.Text(), nullable=False),
        # Base64 outlet photo — TEXT (spec §4.5)
        sa.Column("outlet_photo_url", sa.Text(), nullable=True),
        sa.Column("fssai_license_number", sa.String(20), nullable=True),
        sa.Column("gstin", sa.String(20), nullable=True),
        sa.Column("pan_number", sa.String(15), nullable=True),
        sa.Column("bank_account_number", sa.String(25), nullable=True),
        sa.Column("bank_ifsc_code", sa.String(15), nullable=True),
        sa.Column("campus_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_outlet_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["campus_id"], ["campuses.id"]),
        sa.ForeignKeyConstraint(["created_outlet_id"], ["outlets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 16. verification_reports ──────────────────────────────────────────────
    op.create_table(
        "verification_reports",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        # @OneToOne owning side — FK here, unique constraint
        sa.Column("outlet_application_id", sa.BigInteger(), nullable=False),
        # FSSAI
        sa.Column("fssai_verified", sa.Boolean(), nullable=True),
        sa.Column("fssai_registered_name", sa.String(200), nullable=True),
        sa.Column("fssai_expiry_date", sa.String(30), nullable=True),
        sa.Column("fssai_name_match_score", sa.Double(), nullable=True),
        sa.Column("fssai_name_mismatch", sa.Boolean(), nullable=False),
        sa.Column("fssai_note", sa.String(500), nullable=True),
        # GSTIN
        sa.Column("gst_verified", sa.Boolean(), nullable=True),
        sa.Column("gst_business_name", sa.String(200), nullable=True),
        sa.Column("gst_name_mismatch", sa.Boolean(), nullable=False),
        sa.Column("gst_note", sa.String(500), nullable=True),
        # PAN
        sa.Column("pan_format_valid", sa.Boolean(), nullable=False),
        sa.Column("pan_note", sa.String(500), nullable=True),
        # Bank / IFSC
        sa.Column("bank_ifsc_valid", sa.Boolean(), nullable=True),
        sa.Column("bank_name", sa.String(100), nullable=True),
        sa.Column("bank_branch", sa.String(150), nullable=True),
        sa.Column("bank_note", sa.String(500), nullable=True),
        # Overall
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("overall_status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["outlet_application_id"], ["outlet_applications.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("outlet_application_id"),
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("verification_reports")
    op.drop_table("outlet_applications")
    op.drop_table("admin_applications")
    op.drop_table("email_otp_tokens")
    op.drop_table("notifications")
    op.drop_table("outlet_ratings")
    op.drop_table("outlet_payouts")
    op.drop_table("payments")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("pickup_slots")
    op.drop_table("menu_items")
    op.drop_table("outlets")
    op.drop_table("users")
    op.drop_table("campuses")
    op.drop_table("roles")
