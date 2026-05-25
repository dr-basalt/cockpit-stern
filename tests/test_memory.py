"""Tests for MemoryService (not-self detection, no external deps)."""

import pytest
import asyncio

from app.services.memory import MemoryService


@pytest.mark.asyncio
async def test_detect_not_self_frustration():
    svc = MemoryService()
    from uuid import uuid4
    pid = uuid4()
    assert await svc.detect_not_self(pid, "Je suis frustré par ce blocage", "Frustration") is True
    assert await svc.detect_not_self(pid, "Tout va bien aujourd'hui", "Frustration") is False


@pytest.mark.asyncio
async def test_detect_not_self_amertume():
    svc = MemoryService()
    from uuid import uuid4
    pid = uuid4()
    assert await svc.detect_not_self(pid, "Je ne suis pas reconnu pour mon travail", "Amertume") is True


@pytest.mark.asyncio
async def test_detect_not_self_colere():
    svc = MemoryService()
    from uuid import uuid4
    pid = uuid4()
    assert await svc.detect_not_self(pid, "C'est inacceptable cette situation", "Colère") is True
