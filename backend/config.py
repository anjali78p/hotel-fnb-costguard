"""Configurable thresholds. PLACEHOLDER values: confirm with hotel policy before real use."""
DISCOUNT_LIMIT_PCT = 20.0        # discounts above this % are flagged for review
HIGH_AMENITY_VALUE = 5000.0      # single amenity check above this is flagged for review
REPEAT_VOID_MIN = 3              # same employee + outlet voids >= this are flagged for review
INVOICE_RATE_TOLERANCE_PCT = 0.0 # invoice vs PO rate difference allowed
