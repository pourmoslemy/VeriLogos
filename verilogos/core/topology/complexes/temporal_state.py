"""Temporal state module stub."""


class TemporalState:
    def __init__(self, t: float = 0.0):
        self.t = t
        self._data = {}

    def update(self, key, value):
        self._data[key] = value

    def snapshot(self) -> dict:
        return {"t": self.t, **self._data}

    def __repr__(self):
        return f"TemporalState(t={self.t})"


__all__ = ["TemporalState"]
