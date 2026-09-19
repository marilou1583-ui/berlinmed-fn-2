"""redesign orders and add product stock

Revision ID: 0002_order_redesign
Revises: 0001_initial
Create Date: 2026-07-27

"""
from alembic import op
import sqlalchemy as sa


revision = "0002_order_redesign"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("product") as batch_op:
        batch_op.alter_column("price", existing_type=sa.Float(), type_=sa.Numeric(12, 2), existing_nullable=False)
        batch_op.add_column(sa.Column("stock", sa.Integer(), nullable=False, server_default="0"))
        batch_op.create_unique_constraint("uq_product_name", ["name"])
        batch_op.create_check_constraint("ck_product_stock_non_negative", "stock >= 0")

    op.drop_index("ix_order_customer", table_name="order")
    op.drop_index("ix_order_created_at", table_name="order")
    op.rename_table("order", "order_legacy")

    op.create_table(
        "order",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_number", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("customer_name", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.Column("shipping_address", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("payment_status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("payment_method", sa.String(length=50), nullable=True),
        sa.Column("tracking_number", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.CheckConstraint("total >= 0", name="ck_order_total_non_negative"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
        sa.UniqueConstraint("order_number"),
    )
    op.create_index("ix_order_created_at", "order", ["created_at"])
    op.create_index("ix_order_idempotency_key", "order", ["idempotency_key"])
    op.create_index("ix_order_order_number", "order", ["order_number"])
    op.create_index("ix_order_user_id", "order", ["user_id"])

    op.create_table(
        "order_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("product_image", sa.String(length=255), nullable=True),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("quantity >= 1", name="ck_order_item_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_order_item_unit_price_non_negative"),
        sa.ForeignKeyConstraint(["order_id"], ["order.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_item_order_id", "order_item", ["order_id"])
    op.create_index("ix_order_item_product_id", "order_item", ["product_id"])

    op.execute(
        """
        INSERT INTO "order" (id, order_number, customer_name, phone, shipping_address, status,
                             payment_status, total, created_at, updated_at, user_id)
        SELECT id, 'LEGACY-' || id, customer, '', '', 'pending', 'pending', total,
               created_at, created_at, user_id
        FROM order_legacy
        """
    )
    op.execute(
        """
        INSERT INTO order_item (order_id, product_id, product_name, product_image, unit_price, quantity, created_at)
        SELECT legacy.id, legacy.product_id, legacy.product, product.image, legacy.total / legacy.quantity,
               legacy.quantity, legacy.created_at
        FROM order_legacy AS legacy
        LEFT JOIN product ON product.id = legacy.product_id
        """
    )
    op.drop_table("order_legacy")


def downgrade():
    op.drop_index("ix_order_item_product_id", table_name="order_item")
    op.drop_index("ix_order_item_order_id", table_name="order_item")
    op.drop_table("order_item")
    op.drop_index("ix_order_user_id", table_name="order")
    op.drop_index("ix_order_order_number", table_name="order")
    op.drop_index("ix_order_idempotency_key", table_name="order")
    op.drop_index("ix_order_created_at", table_name="order")
    op.drop_table("order")
    raise RuntimeError("Downgrading the order redesign is not supported.")
