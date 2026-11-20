"""Signal: a strategy's directional intent for one candle.

v1 is a plain enum with no confidence/weight/size — extending it is explicitly
out of scope until a strategy actually needs it (see
`docs/VECTORX-POST-MVP-ROADMAP.md`, Фаза 13).
"""

from enum import StrEnum


class Signal(StrEnum):
    """A strategy's directional intent for the candle it just saw."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
