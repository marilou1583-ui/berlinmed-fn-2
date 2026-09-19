"""add product_image table for multiple product images

Revision ID: 0004_product_images
Revises: 0003_page_content
Create Date: 2026-08-19

"""
from alembic import op
import sqlalchemy as sa


revision = "0004_product_images"
down_revision = "0003_page_content"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "product_image",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_image_product_id", "product_image", ["product_id"])

    connection = op.get_bind()
    product_table = sa.table(
        "product",
        sa.column("id", sa.Integer()),
        sa.column("image", sa.String()),
    )
    product_image_table = sa.table(
        "product_image",
        sa.column("product_id", sa.Integer()),
        sa.column("filename", sa.String()),
        sa.column("sort_order", sa.Integer()),
    )
    existing_products = connection.execute(sa.select(product_table.c.id, product_table.c.image)).fetchall()
    for product_id, image in existing_products:
        if image:
            connection.execute(
                product_image_table.insert().values(product_id=product_id, filename=image, sort_order=0)
            )


def downgrade():
    op.drop_index("ix_product_image_product_id", table_name="product_image")
    op.drop_table("product_image")