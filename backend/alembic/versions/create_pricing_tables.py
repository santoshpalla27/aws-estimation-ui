"""
Database migration: Create pricing tables
Run with: alembic revision --autogenerate -m "create_pricing_tables"
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'create_pricing_tables'
down_revision = None  # Update with your current head
branch_labels = None
depends_on = None


def upgrade():
    # Create pricing_versions table
    op.create_table(
        'pricing_versions',
        sa.Column('version', sa.String(20), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('source_type', sa.String(50), nullable=False, server_default='aws_pricing_api'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('metadata', postgresql.JSONB(), nullable=True)
    )
    op.create_index('idx_pricing_versions_active', 'pricing_versions', ['is_active'])
    
    # Create pricing_rates table
    op.create_table(
        'pricing_rates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('version', sa.String(20), sa.ForeignKey('pricing_versions.version'), nullable=False),
        sa.Column('service', sa.String(100), nullable=False),
        sa.Column('region', sa.String(50), nullable=False),
        sa.Column('pricing_key', sa.String(200), nullable=False),
        sa.Column('rate', sa.Numeric(20, 10), nullable=False),
        sa.Column('unit', sa.String(50), nullable=True),
        sa.Column('source_sku', sa.String(200), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'))
    )
    op.create_index('idx_pricing_lookup', 'pricing_rates', ['version', 'service', 'region', 'pricing_key'])
    op.create_index('idx_pricing_service_region', 'pricing_rates', ['service', 'region'])
    op.create_index('idx_pricing_version', 'pricing_rates', ['version'])
    
    # Create pricing_metadata table
    op.create_table(
        'pricing_metadata',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('version', sa.String(20), sa.ForeignKey('pricing_versions.version'), nullable=False),
        sa.Column('service', sa.String(100), nullable=False),
        sa.Column('region', sa.String(50), nullable=False),
        sa.Column('free_tier', postgresql.JSONB(), nullable=True),
        sa.Column('tier_boundaries', postgresql.JSONB(), nullable=True),
        sa.Column('multipliers', postgresql.JSONB(), nullable=True),
        sa.Column('source_url', sa.Text(), nullable=True)
    )
    op.create_index('idx_pricing_metadata_lookup', 'pricing_metadata', ['version', 'service', 'region'], unique=True)
    
    # Create pricing_changes table
    op.create_table(
        'pricing_changes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('old_version', sa.String(20), nullable=True),
        sa.Column('new_version', sa.String(20), nullable=False),
        sa.Column('service', sa.String(100), nullable=False),
        sa.Column('region', sa.String(50), nullable=False),
        sa.Column('pricing_key', sa.String(200), nullable=False),
        sa.Column('old_rate', sa.Numeric(20, 10), nullable=True),
        sa.Column('new_rate', sa.Numeric(20, 10), nullable=False),
        sa.Column('change_percent', sa.Numeric(10, 4), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'))
    )
    op.create_index('idx_pricing_changes_version', 'pricing_changes', ['new_version'])
    op.create_index('idx_pricing_changes_service', 'pricing_changes', ['service', 'region'])


def downgrade():
    op.drop_table('pricing_changes')
    op.drop_table('pricing_metadata')
    op.drop_table('pricing_rates')
    op.drop_table('pricing_versions')
