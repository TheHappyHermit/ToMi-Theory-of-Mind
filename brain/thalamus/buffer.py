#!/usr/bin/env python3
"""
brain.thalamus.buffer — Ring buffer for raw sensory events and noise attenuation.
"""

from collections import deque
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class SensoryEvent:
    def __init__(self, source: str, raw_payload: str, metadata: Optional[Dict[str, Any]] = None):
        self.source = source
        self.raw_payload = raw_payload
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.gated = False
        self.saliency_score = 0.0


class SensoryBuffer:
    """Ring buffer holding incoming raw sensory percepts before attentional admission."""

    def __init__(self, maxlen: int = 100):
        self.buffer: deque[SensoryEvent] = deque(maxlen=maxlen)

    def append(self, source: str, payload: str, metadata: Optional[Dict[str, Any]] = None) -> SensoryEvent:
        event = SensoryEvent(source=source, raw_payload=payload, metadata=metadata)
        self.buffer.append(event)
        return event

    def get_recent(self, count: int = 10) -> List[SensoryEvent]:
        items = list(self.buffer)
        return items[-count:]

    def clear(self):
        self.buffer.clear()
