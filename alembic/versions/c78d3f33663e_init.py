"""init

Revision ID: c78d3f33663e
Revises: 
Create Date: 2023-11-28 16:26:19.662201

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c78d3f33663e'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def downgrade() -> None:
    pass

def upgrade() -> None:
    op.create_table('work_units',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('area', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('location', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('category', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('subcategory', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('action', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('quantity', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('profession', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('digest', sa.TEXT(), sa.Computed('md5((((((((area)::text || (location)::text) || (category)::text) || (subcategory)::text) || (action)::text) || (quantity)::text) || (profession)::text))', persisted=True), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name='work_units_pkey'),
    sa.UniqueConstraint('digest', name='ensure_unique_work_unit')
    )
    op.create_table('users',
    sa.Column('email', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('phone_number', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('password', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('admin', sa.BOOLEAN(), autoincrement=False, nullable=True),
    sa.Column('role', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('email', name='users_pkey'),
    sa.UniqueConstraint('id', name='users_id_key'),
    sa.UniqueConstraint('phone_number', name='users_phone_number_key'),
    postgresql_ignore_search_path=False
    )
    op.create_table('contractors',
    sa.Column('quality_rating', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('budget_rating', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('on_schedule_rating', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('first_name', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('last_name', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('bio', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('avatar_uri', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['id'], ['users.id'], name='contractors_id_fkey', initially='DEFERRED', deferrable=True),
    sa.PrimaryKeyConstraint('id', name='contractors_pkey'),
    postgresql_ignore_search_path=False
    )
    op.create_table('contractor_area_preferences',
    sa.Column('area', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('contractor_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['contractor_id'], ['contractors.id'], name='contractor_area_preferences_contractor_id_fkey', initially='DEFERRED', deferrable=True),
    sa.PrimaryKeyConstraint('area', 'contractor_id', name='contractor_area_preferences_pkey')
    )
    op.create_table('contractor_profession_preferences',
    sa.Column('work_unit_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('contractor_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['contractor_id'], ['contractors.id'], name='contractor_profession_preferences_contractor_id_fkey', initially='DEFERRED', deferrable=True),
    sa.ForeignKeyConstraint(['work_unit_id'], ['work_units.id'], name='contractor_profession_preferences_work_unit_id_fkey'),
    sa.PrimaryKeyConstraint('work_unit_id', 'contractor_id', name='contractor_profession_preferences_pkey')
    ) 
    op.create_table('external_portfolio_projects',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('contractor_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('title', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('description', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('zipcode', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['contractor_id'], ['contractors.id'], name='external_portfolio_projects_contractor_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='external_portfolio_projects_pkey'),
    postgresql_ignore_search_path=False
    )
    op.create_table('external_portfolio_project_units',
    sa.Column('work_unit_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('portfolio_project_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['portfolio_project_id'], ['external_portfolio_projects.id'], name='external_portfolio_project_units_portfolio_project_id_fkey', initially='DEFERRED', deferrable=True),
    sa.ForeignKeyConstraint(['work_unit_id'], ['work_units.id'], name='external_portfolio_project_units_work_unit_id_fkey'),
    sa.PrimaryKeyConstraint('work_unit_id', 'portfolio_project_id', name='external_portfolio_project_units_pkey')
    )
    op.create_table('contractor_analytics',
    sa.Column('tasks', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('completed_projects', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('reviews', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('contractor_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['contractor_id'], ['contractors.id'], name='contractor_analytics_contractor_id_fkey', initially='DEFERRED', deferrable=True),
    sa.PrimaryKeyConstraint('contractor_id', name='contractor_analytics_pkey')
    )   
    op.create_table('homeowners',
    sa.Column('first_name', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('last_name', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('avatar_uri', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('rating', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['id'], ['users.id'], name='homeowners_id_fkey', initially='DEFERRED', deferrable=True),
    sa.PrimaryKeyConstraint('id', name='homeowners_pkey'),
    postgresql_ignore_search_path=False
    )
    op.create_table('bookings',
    sa.Column('title', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('zipcode', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('address', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('homeowner_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('is_active', sa.BOOLEAN(), autoincrement=False, nullable=True),
    sa.Column('is_booked', sa.BOOLEAN(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['homeowner_id'], ['homeowners.id'], name='bookings_homeowner_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='bookings_pkey'),
    postgresql_ignore_search_path=False
    )
    op.create_table('booking_units',
    sa.Column('work_unit_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('quantity', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('description', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('booking_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name='booking_units_booking_id_fkey', initially='DEFERRED', deferrable=True),
    sa.ForeignKeyConstraint(['work_unit_id'], ['work_units.id'], name='booking_units_work_unit_id_fkey'),
    sa.PrimaryKeyConstraint('work_unit_id', 'booking_id', name='booking_units_pkey'),
    sa.UniqueConstraint('id', name='booking_units_id_key')
    )
    op.create_table('booking_invites',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('booking_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('contractor_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('accepted', sa.BOOLEAN(), autoincrement=False, nullable=True),
    sa.Column('rejected', sa.BOOLEAN(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name='booking_invites_booking_id_fkey'),
    sa.ForeignKeyConstraint(['contractor_id'], ['contractors.id'], name='booking_invites_contractor_id_fkey'),
    sa.PrimaryKeyConstraint('booking_id', 'contractor_id', name='booking_invites_pkey'),
    sa.UniqueConstraint('id', name='booking_invites_id_key'),
    postgresql_ignore_search_path=False
    )
    op.create_table('booking_images',
    sa.Column('uri', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('caption', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('booking_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name='booking_images_booking_id_fkey', initially='DEFERRED', deferrable=True),
    sa.PrimaryKeyConstraint('id', name='booking_images_pkey')
    )
    op.create_table('quotes',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('booking_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('booking_invite_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('accepted', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name='quotes_booking_id_fkey'),
    sa.ForeignKeyConstraint(['booking_invite_id'], ['booking_invites.id'], name='quotes_booking_invite_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='quotes_pkey'),
    postgresql_ignore_search_path=False
    )
    op.create_table('quote_items',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('qoute_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('booking_unit_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('work_hours', sa.NUMERIC(precision=8, scale=3), autoincrement=False, nullable=True),
    sa.Column('work_rate', sa.NUMERIC(precision=8, scale=3), autoincrement=False, nullable=True),
    sa.Column('work_cost', sa.NUMERIC(precision=8, scale=3), autoincrement=False, nullable=True),
    sa.Column('description', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('modified_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('status', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('is_active', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['booking_unit_id'], ['booking_units.id'], name='quote_items_booking_unit_id_fkey'),
    sa.ForeignKeyConstraint(['qoute_id'], ['quotes.id'], name='quote_items_qoute_id_fkey', initially='DEFERRED', deferrable=True),
    sa.PrimaryKeyConstraint('id', name='quote_items_pkey')
    )
    op.create_table('material_units',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('quote_item_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('cost', sa.NUMERIC(precision=8, scale=3), autoincrement=False, nullable=True),
    sa.Column('description', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['quote_item_id'], ['quote_items.id'], name='material_units_quote_item_id_fkey', initially='DEFERRED', deferrable=True),
    sa.PrimaryKeyConstraint('id', name='material_units_pkey')
    )
    op.create_table('projects',
    sa.Column('booking_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('contractor_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('completed_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('signal_completion', sa.BOOLEAN(), autoincrement=False, nullable=True),
    sa.Column('is_public', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('is_active', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name='projects_booking_id_fkey'),
    sa.ForeignKeyConstraint(['contractor_id'], ['contractors.id'], name='projects_contractor_id_fkey'),
    sa.PrimaryKeyConstraint('booking_id', name='projects_pkey'),
    postgresql_ignore_search_path=False
    )
    op.create_table('project_images',
    sa.Column('uri', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('caption', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('booking_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['booking_id'], ['projects.booking_id'], name='project_images_booking_id_fkey', initially='DEFERRED', deferrable=True),
    sa.PrimaryKeyConstraint('id', name='project_images_pkey')
    )
    op.create_table('contractor_reviews',
    sa.Column('quality_rating', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('budget_rating', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('on_schedule_rating', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('booking_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('to_', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('from_', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('budget_words', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('quality_words', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('schedule_words', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('description', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['booking_id'], ['projects.booking_id'], name='contractor_reviews_booking_id_fkey', initially='DEFERRED', deferrable=True),
    sa.ForeignKeyConstraint(['from_'], ['homeowners.id'], name='contractor_reviews_from__fkey'),
    sa.ForeignKeyConstraint(['to_'], ['contractors.id'], name='contractor_reviews_to__fkey'),
    sa.PrimaryKeyConstraint('booking_id', 'to_', 'from_', name='contractor_reviews_pkey')
    )
    op.create_table('homeowner_reviews',
    sa.Column('booking_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('to_', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('from_', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('rating_words', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('rating', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('description', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['booking_id'], ['projects.booking_id'], name='homeowner_reviews_booking_id_fkey', initially='DEFERRED', deferrable=True),
    sa.ForeignKeyConstraint(['from_'], ['contractors.id'], name='homeowner_reviews_from__fkey'),
    sa.ForeignKeyConstraint(['to_'], ['homeowners.id'], name='homeowner_reviews_to__fkey'),
    sa.PrimaryKeyConstraint('booking_id', 'to_', 'from_', name='homeowner_reviews_pkey')
    )
    op.create_table('external_portfolio_images',
    sa.Column('uri', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('caption', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('portfolio_project_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['portfolio_project_id'], ['external_portfolio_projects.id'], name='external_portfolio_images_portfolio_project_id_fkey', initially='DEFERRED', deferrable=True),
    sa.PrimaryKeyConstraint('id', name='external_portfolio_images_pkey')
    )