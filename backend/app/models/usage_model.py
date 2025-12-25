"""
Usage model configuration.
Parameterizes time assumptions instead of hardcoding 730 hours/month.
"""
from enum import Enum
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class UsagePattern(str, Enum):
    """Supported usage patterns."""
    ALWAYS_ON = "always_on"           # 730 hours/month (24/7)
    BUSINESS_HOURS = "business_hours" # ~176 hours/month (8h/day, 22 days)
    PARTIAL = "partial"                # Custom hours
    SPOT = "spot"                      # Variable, with interruption factor
    LAMBDA = "lambda"                  # Event-driven, not time-based


class UsageModel(BaseModel):
    """
    Usage model for cost calculation.
    Makes time assumptions explicit and configurable.
    """
    pattern: UsagePattern = Field(
        default=UsagePattern.ALWAYS_ON,
        description="Usage pattern for the resource"
    )
    
    hours_per_month: Optional[Decimal] = Field(
        default=None,
        description="Custom hours per month (for PARTIAL pattern)"
    )
    
    interruption_factor: Optional[Decimal] = Field(
        default=None,
        ge=0,
        le=1,
        description="Expected interruption rate (for SPOT pattern, 0-1)"
    )
    
    invocations_per_month: Optional[int] = Field(
        default=None,
        description="Expected invocations (for LAMBDA pattern)"
    )
    
    def get_effective_hours(self) -> Decimal:
        """
        Get effective hours per month based on pattern.
        
        Returns:
            Effective hours for cost calculation
        
        Raises:
            ValueError: If pattern requires additional parameters
        """
        if self.pattern == UsagePattern.ALWAYS_ON:
            return Decimal("730")  # 24 * 365.25 / 12
        
        elif self.pattern == UsagePattern.BUSINESS_HOURS:
            # 8 hours/day * 22 business days/month
            return Decimal("176")
        
        elif self.pattern == UsagePattern.PARTIAL:
            if self.hours_per_month is None:
                raise ValueError(
                    "PARTIAL pattern requires hours_per_month parameter"
                )
            return self.hours_per_month
        
        elif self.pattern == UsagePattern.SPOT:
            base_hours = Decimal("730")
            if self.interruption_factor is not None:
                # Reduce hours by interruption factor
                return base_hours * (Decimal("1") - self.interruption_factor)
            return base_hours
        
        elif self.pattern == UsagePattern.LAMBDA:
            # Lambda doesn't use hours - return 0
            return Decimal("0")
        
        else:
            raise ValueError(f"Unknown usage pattern: {self.pattern}")
    
    def is_time_based(self) -> bool:
        """Check if this usage model is time-based."""
        return self.pattern != UsagePattern.LAMBDA
    
    @classmethod
    def always_on(cls) -> "UsageModel":
        """Create always-on usage model (730 hours/month)."""
        return cls(pattern=UsagePattern.ALWAYS_ON)
    
    @classmethod
    def business_hours(cls) -> "UsageModel":
        """Create business hours usage model (176 hours/month)."""
        return cls(pattern=UsagePattern.BUSINESS_HOURS)
    
    @classmethod
    def partial(cls, hours: Decimal) -> "UsageModel":
        """Create partial usage model with custom hours."""
        return cls(
            pattern=UsagePattern.PARTIAL,
            hours_per_month=hours
        )
    
    @classmethod
    def spot(cls, interruption_rate: Decimal = Decimal("0.1")) -> "UsageModel":
        """Create spot instance usage model with interruption factor."""
        return cls(
            pattern=UsagePattern.SPOT,
            interruption_factor=interruption_rate
        )
    
    @classmethod
    def lambda_usage(cls, invocations: int) -> "UsageModel":
        """Create Lambda usage model (event-driven)."""
        return cls(
            pattern=UsagePattern.LAMBDA,
            invocations_per_month=invocations
        )


# NO DEFAULT - usage model must be explicitly specified
# This prevents hardcoded time assumptions
