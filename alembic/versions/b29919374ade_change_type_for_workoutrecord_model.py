"""Change type for WorkoutRecord model

Revision ID: b29919374ade
Revises: 
Create Date: 2024-05-04 13:30:13.205833

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b29919374ade'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('workout_record', 'weight',
                    existing_type=sa.Integer(),
                    type_=sa.Float(),
                    existing_nullable=True)


def downgrade() -> None:
    op.alter_column('workout_record', 'weight',
                    existing_type=sa.Float(),
                    type_=sa.Integer(),
                    existing_nullable=True)
