"""Background task — runs pattern detection every hour."""
import asyncio
import logging

logger = logging.getLogger(__name__)

_task = None


async def _pattern_detector_loop():
    """Run pattern analysis every hour for active profiles."""
    from app.services.memory import MemoryService
    from app.services.pattern_detector import PatternDetector

    memory = MemoryService()
    detector = PatternDetector(memory)

    while True:
        try:
            await asyncio.sleep(3600)  # every hour
            logger.info("Pattern detector: running analysis cycle")
            # In a real implementation, fetch active profiles from DB
            # and run detector.analyze() for each
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Pattern detector error: {e}")
            await asyncio.sleep(60)


def start_pattern_detector():
    global _task
    if _task is None:
        _task = asyncio.ensure_future(_pattern_detector_loop())
        logger.info("Pattern detector background task started")
