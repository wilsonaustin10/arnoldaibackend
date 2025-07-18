"""Initial migration

Revision ID: 51ced4ee98d7
Revises: 
Create Date: 2025-07-04 06:21:39.833103

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51ced4ee98d7'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('workouts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('workout_date', sa.Date(), nullable=False),
    sa.Column('exercise', sa.String(), nullable=False),
    sa.Column('reps', sa.Integer(), nullable=False),
    sa.Column('weight_lbs', sa.Float(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_exercise_date', 'workouts', ['exercise', 'workout_date'], unique=False)
    op.create_index(op.f('ix_workouts_exercise'), 'workouts', ['exercise'], unique=False)
    op.create_index(op.f('ix_workouts_id'), 'workouts', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_workouts_id'), table_name='workouts')
    op.drop_index(op.f('ix_workouts_exercise'), table_name='workouts')
    op.drop_index('idx_exercise_date', table_name='workouts')
    op.drop_table('workouts')
    # ### end Alembic commands ###