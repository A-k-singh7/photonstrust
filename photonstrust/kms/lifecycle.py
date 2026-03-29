"""Key lifecycle state machine for QKD key management.

Implements the key lifecycle from generation through expiration,
tracking state transitions and enforcing valid state changes.

States:
    GENERATED -> STORED -> DELIVERED -> CONSUMED -> EXPIRED
    GENERATED -> STORED -> EXPIRED  (unused key expiration)
    Any state -> REVOKED (compromise detected)

Key references:
    - ETSI GS QKD 014 V1.1.1 (2019) -- QKD KMS API
    - ETSI GS QKD 004 V2.1.1 (2020) -- QKD application interface
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class KeyState(Enum):
    """QKD key lifecycle states."""
    GENERATED = "generated"
    STORED = "stored"
    DELIVERED = "delivered"
    CONSUMED = "consumed"
    EXPIRED = "expired"
    REVOKED = "revoked"


# Valid state transitions
_VALID_TRANSITIONS: dict[KeyState, set[KeyState]] = {
    KeyState.GENERATED: {KeyState.STORED, KeyState.REVOKED},
    KeyState.STORED: {KeyState.DELIVERED, KeyState.EXPIRED, KeyState.REVOKED},
    KeyState.DELIVERED: {KeyState.CONSUMED, KeyState.EXPIRED, KeyState.REVOKED},
    KeyState.CONSUMED: {KeyState.EXPIRED, KeyState.REVOKED},
    KeyState.EXPIRED: set(),        # terminal
    KeyState.REVOKED: set(),        # terminal
}


@dataclass
class KeyTransition:
    """Record of a state transition."""
    from_state: KeyState
    to_state: KeyState
    timestamp: float
    reason: str = ""


@dataclass
class ManagedKey:
    """A QKD key with lifecycle tracking."""
    key_id: str
    key_length_bits: int
    state: KeyState = KeyState.GENERATED
    created_at: float = field(default_factory=time.time)
    ttl_seconds: float = 3600.0         # default 1 hour
    transitions: list[KeyTransition] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.state in {KeyState.EXPIRED, KeyState.REVOKED}

    @property
    def is_expired_by_ttl(self) -> bool:
        return time.time() > self.created_at + self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


class KeyLifecycleManager:
    """Manages QKD key lifecycle state transitions."""

    def __init__(self) -> None:
        self._keys: dict[str, ManagedKey] = {}
        self._transition_log: list[KeyTransition] = []

    @property
    def keys(self) -> dict[str, ManagedKey]:
        return dict(self._keys)

    def register_key(
        self,
        key_id: str,
        key_length_bits: int = 256,
        ttl_seconds: float = 3600.0,
        metadata: dict[str, Any] | None = None,
    ) -> ManagedKey:
        """Register a newly generated QKD key."""
        key = ManagedKey(
            key_id=key_id,
            key_length_bits=key_length_bits,
            state=KeyState.GENERATED,
            ttl_seconds=ttl_seconds,
            metadata=metadata or {},
        )
        self._keys[key_id] = key
        return key

    def transition(
        self,
        key_id: str,
        to_state: KeyState,
        reason: str = "",
    ) -> ManagedKey:
        """Transition a key to a new state.

        Validates the transition is legal according to the state machine.

        Args:
            key_id: Key identifier
            to_state: Target state
            reason: Optional reason for the transition

        Returns:
            Updated ManagedKey

        Raises:
            KeyError: If key_id not found
            InvalidTransitionError: If transition is not valid
        """
        key = self._keys[key_id]

        if to_state not in _VALID_TRANSITIONS.get(key.state, set()):
            raise InvalidTransitionError(
                f"Cannot transition key {key_id} from {key.state.value} "
                f"to {to_state.value}"
            )

        transition = KeyTransition(
            from_state=key.state,
            to_state=to_state,
            timestamp=time.time(),
            reason=reason,
        )
        key.transitions.append(transition)
        self._transition_log.append(transition)
        key.state = to_state
        return key

    def store(self, key_id: str) -> ManagedKey:
        """Move key from GENERATED to STORED."""
        return self.transition(key_id, KeyState.STORED, "stored in key pool")

    def deliver(self, key_id: str, recipient: str = "") -> ManagedKey:
        """Move key from STORED to DELIVERED."""
        return self.transition(key_id, KeyState.DELIVERED, f"delivered to {recipient}")

    def consume(self, key_id: str, purpose: str = "") -> ManagedKey:
        """Move key from DELIVERED to CONSUMED."""
        return self.transition(key_id, KeyState.CONSUMED, f"consumed for {purpose}")

    def expire(self, key_id: str) -> ManagedKey:
        """Move key to EXPIRED (TTL or policy)."""
        return self.transition(key_id, KeyState.EXPIRED, "TTL expired")

    def revoke(self, key_id: str, reason: str = "compromise detected") -> ManagedKey:
        """Emergency revocation from any non-terminal state."""
        return self.transition(key_id, KeyState.REVOKED, reason)

    def expire_stale_keys(self) -> list[str]:
        """Expire all keys past their TTL."""
        expired = []
        for key_id, key in self._keys.items():
            if key.is_expired_by_ttl and not key.is_terminal:
                try:
                    self.expire(key_id)
                    expired.append(key_id)
                except InvalidTransitionError:
                    pass
        return expired

    def count_by_state(self) -> dict[str, int]:
        """Count keys in each lifecycle state."""
        counts: dict[str, int] = {s.value: 0 for s in KeyState}
        for key in self._keys.values():
            counts[key.state.value] += 1
        return counts

    def get_transition_log(self) -> list[KeyTransition]:
        """Return full transition history."""
        return list(self._transition_log)
