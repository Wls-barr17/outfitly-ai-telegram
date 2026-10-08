"""Create Outfitly.AI relational schema."""

from alembic import op
from app.database import models  # noqa: F401
from app.database.base import Base

revision = "20261007_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
