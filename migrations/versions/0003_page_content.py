from alembic import op
import sqlalchemy as sa


revision = "0003_page_content"
down_revision = "0002_order_redesign"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "page_content",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_page_content_slug", "page_content", ["slug"])


def downgrade():
    op.drop_index("ix_page_content_slug", table_name="page_content")
    op.drop_table("page_content")
