"""Derived analytics for visible order-book level lifetimes and public trade flow."""
from datetime import datetime
from decimal import Decimal


def _parse_time(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO-8601 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed


class LevelLifecycleTracker:
    """Track observed price-level presence, not individual orders or trader intent.

    Call seed() once per synchronized snapshot, then apply_event() for each
    applied diff-depth event. Lifetimes are observation intervals and reset
    after a process restart unless a caller restores prior state.
    """

    def __init__(self):
        self._levels = {"bid": {}, "ask": {}}

    def seed(self, bids, asks, timestamp):
        at = _parse_time(timestamp)
        for side, levels in (("bid", bids), ("ask", asks)):
            self._levels[side] = {
                Decimal(price): {"quantity": Decimal(quantity), "first_seen": at}
                for price, quantity in levels.items() if Decimal(quantity) > 0
            }

    def apply_event(self, event, timestamp):
        at = _parse_time(timestamp)
        emitted = []
        for side_name, key in (("bid", "b"), ("ask", "a")):
            levels = self._levels[side_name]
            for row in event.get(key, []):
                if len(row) < 2:
                    continue
                price, quantity = Decimal(str(row[0])), Decimal(str(row[1]))
                if price <= 0 or quantity < 0:
                    continue
                previous = levels.get(price)
                if quantity == 0:
                    if previous is not None:
                        emitted.append(self._record(
                            side_name, price, previous, at, "removed", previous["quantity"], Decimal(0)
                        ))
                        del levels[price]
                    continue
                if previous is None:
                    current = {"quantity": quantity, "first_seen": at}
                    levels[price] = current
                    emitted.append(self._record(side_name, price, current, at, "added", Decimal(0), quantity))
                elif previous["quantity"] != quantity:
                    current = {"quantity": quantity, "first_seen": previous["first_seen"]}
                    levels[price] = current
                    emitted.append(self._record(side_name, price, current, at, "quantity_changed", previous["quantity"], quantity))
        return emitted

    @staticmethod
    def _record(side, price, state, at, event_type, quantity_before, quantity_after):
        age_ms = max(0, int((at - state["first_seen"]).total_seconds() * 1000))
        return {
            "side": side,
            "price": str(price),
            "event_type": event_type,
            "quantity_before_event": str(quantity_before),
            "quantity_after_event": str(quantity_after),
            "first_observed_at": state["first_seen"].isoformat().replace("+00:00", "Z"),
            "observed_at": at.isoformat().replace("+00:00", "Z"),
            "observed_lifetime_ms": age_ms,
            "interpretation": "visible price-level lifetime; not individual-order age or intent",
        }


class CVDAccumulator:
    """Accumulate inferred aggressor-side public trade volume in base and quote units."""

    def __init__(self):
        self.buy_base = Decimal(0)
        self.sell_base = Decimal(0)
        self.buy_quote = Decimal(0)
        self.sell_quote = Decimal(0)

    def add_trade(self, price, quantity, buyer_is_maker):
        price, quantity = Decimal(str(price)), Decimal(str(quantity))
        if price <= 0 or quantity < 0:
            raise ValueError("trade price must be positive and quantity non-negative")
        # Binance m=true means the buyer was maker, so the seller was taker.
        side = "SELL" if buyer_is_maker else "BUY"
        quote = price * quantity
        if side == "BUY":
            self.buy_base += quantity
            self.buy_quote += quote
        else:
            self.sell_base += quantity
            self.sell_quote += quote
        return {
            "aggressor_side_inferred": side,
            "trade_base_quantity": str(quantity),
            "trade_quote_quantity": str(quote),
            "cumulative_buy_base": str(self.buy_base),
            "cumulative_sell_base": str(self.sell_base),
            "cvd_base": str(self.buy_base - self.sell_base),
            "cumulative_buy_quote": str(self.buy_quote),
            "cumulative_sell_quote": str(self.sell_quote),
            "cvd_quote": str(self.buy_quote - self.sell_quote),
            "note": "Inferred from public buyer-maker flag; resets when collector process restarts.",
        }
