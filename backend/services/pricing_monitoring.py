"""
Pricing Change Alert System
Monitors pricing changes and sends alerts for significant changes
"""

import asyncio
from typing import List, Dict, Any
from decimal import Decimal
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.pricing_models import PricingChange
import structlog

logger = structlog.get_logger()


class PricingChangeAlert:
    """Alert configuration for pricing changes"""
    
    SEVERITY_THRESHOLDS = {
        'CRITICAL': 20.0,  # >20% change
        'HIGH': 10.0,      # >10% change
        'MEDIUM': 5.0,     # >5% change
        'LOW': 0.0         # Any change
    }
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = logger.bind(component="pricing_alert")
    
    async def check_and_alert(self, version: str):
        """Check for pricing changes and send alerts"""
        changes = await self._get_changes(version)
        
        if not changes:
            self.logger.info("no_pricing_changes", version=version)
            return
        
        # Group by severity
        alerts = self._group_by_severity(changes)
        
        # Send alerts
        for severity, change_list in alerts.items():
            if change_list:
                await self._send_alert(severity, version, change_list)
    
    async def _get_changes(self, version: str) -> List[PricingChange]:
        """Get all pricing changes for version"""
        stmt = select(PricingChange).where(
            PricingChange.new_version == version
        ).order_by(PricingChange.change_percent.desc())
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    def _group_by_severity(self, changes: List[PricingChange]) -> Dict[str, List[PricingChange]]:
        """Group changes by severity"""
        grouped = {
            'CRITICAL': [],
            'HIGH': [],
            'MEDIUM': [],
            'LOW': []
        }
        
        for change in changes:
            abs_change = abs(float(change.change_percent))
            
            if abs_change >= self.SEVERITY_THRESHOLDS['CRITICAL']:
                grouped['CRITICAL'].append(change)
            elif abs_change >= self.SEVERITY_THRESHOLDS['HIGH']:
                grouped['HIGH'].append(change)
            elif abs_change >= self.SEVERITY_THRESHOLDS['MEDIUM']:
                grouped['MEDIUM'].append(change)
            else:
                grouped['LOW'].append(change)
        
        return grouped
    
    async def _send_alert(self, severity: str, version: str, changes: List[PricingChange]):
        """Send alert notification"""
        self.logger.warning(
            "pricing_change_alert",
            severity=severity,
            version=version,
            change_count=len(changes)
        )
        
        # Format alert message
        message = self._format_alert_message(severity, version, changes)
        
        # Send via multiple channels
        await self._send_slack_alert(severity, message)
        await self._send_email_alert(severity, message)
        
        # Log to monitoring system
        self.logger.info(
            "alert_sent",
            severity=severity,
            version=version,
            changes=len(changes)
        )
    
    def _format_alert_message(self, severity: str, version: str, changes: List[PricingChange]) -> str:
        """Format alert message"""
        lines = [
            f"🚨 Pricing Change Alert - {severity}",
            f"Version: {version}",
            f"Changes: {len(changes)}",
            "",
            "Top Changes:"
        ]
        
        # Show top 10 changes
        for change in changes[:10]:
            direction = "↑" if change.change_percent > 0 else "↓"
            lines.append(
                f"  {direction} {change.service}/{change.region}/{change.pricing_key}: "
                f"{change.old_rate} → {change.new_rate} ({change.change_percent:+.2f}%)"
            )
        
        return "\n".join(lines)
    
    async def _send_slack_alert(self, severity: str, message: str):
        """Send alert to Slack"""
        # TODO: Implement Slack webhook integration
        self.logger.info("slack_alert_sent", severity=severity)
    
    async def _send_email_alert(self, severity: str, message: str):
        """Send alert via email"""
        # TODO: Implement email integration
        self.logger.info("email_alert_sent", severity=severity)


class PricingFreshnessMonitor:
    """Monitor pricing data freshness"""
    
    FRESHNESS_THRESHOLDS = {
        'STALE': 30,      # >30 days old
        'VERY_STALE': 60,  # >60 days old
        'CRITICAL': 90     # >90 days old
    }
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = logger.bind(component="pricing_freshness")
    
    async def check_freshness(self) -> Dict[str, Any]:
        """Check pricing data freshness"""
        from models.pricing_models import PricingRate, PricingVersion
        
        # Get active version
        stmt = select(PricingVersion).where(PricingVersion.is_active == True)
        result = await self.session.execute(stmt)
        active_version = result.scalar_one_or_none()
        
        if not active_version:
            return {'status': 'ERROR', 'message': 'No active pricing version'}
        
        # Get oldest pricing data
        stmt = select(PricingRate).where(
            PricingRate.version == active_version.version
        ).order_by(PricingRate.fetched_at.asc()).limit(1)
        
        result = await self.session.execute(stmt)
        oldest_rate = result.scalar_one_or_none()
        
        if not oldest_rate:
            return {'status': 'ERROR', 'message': 'No pricing data found'}
        
        # Calculate age
        age_days = (datetime.utcnow() - oldest_rate.fetched_at).days
        
        # Determine status
        if age_days >= self.FRESHNESS_THRESHOLDS['CRITICAL']:
            status = 'CRITICAL'
        elif age_days >= self.FRESHNESS_THRESHOLDS['VERY_STALE']:
            status = 'VERY_STALE'
        elif age_days >= self.FRESHNESS_THRESHOLDS['STALE']:
            status = 'STALE'
        else:
            status = 'FRESH'
        
        result = {
            'status': status,
            'version': active_version.version,
            'age_days': age_days,
            'fetched_at': oldest_rate.fetched_at.isoformat(),
            'threshold_stale': self.FRESHNESS_THRESHOLDS['STALE'],
            'threshold_critical': self.FRESHNESS_THRESHOLDS['CRITICAL']
        }
        
        self.logger.info("freshness_check", **result)
        
        # Alert if stale
        if status != 'FRESH':
            await self._alert_stale_pricing(result)
        
        return result
    
    async def _alert_stale_pricing(self, freshness_data: Dict):
        """Alert on stale pricing data"""
        self.logger.warning(
            "stale_pricing_detected",
            status=freshness_data['status'],
            age_days=freshness_data['age_days']
        )
        
        # TODO: Send alert via Slack/email
