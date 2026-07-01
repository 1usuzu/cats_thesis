import asyncio
from typing import Any, Callable, Dict, List

import structlog

logger = structlog.get_logger()

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], Any]]] = {}
        self._queue = None
        self._task = None
        logger.warning(f"EventBus created with id {id(self)}")

    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], Any]):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.info(f"Subscribed to {event_type} on EventBus {id(self)}", callback=callback.__name__)

    async def publish(self, event_type: str, payload: Dict[str, Any]):
        if self._queue is None:
            logger.warning(f"EventBus {id(self)} queue not initialized, ignoring event")
            return
        event = {"type": event_type, "payload": payload}
        await self._queue.put(event)
        logger.debug(f"Event published: {event_type} on EventBus {id(self)}")

    async def _process_events(self):
        while True:
            try:
                event = await self._queue.get()
                event_type = event["type"]
                payload = event["payload"]

                logger.info(f"DEBUG EventBus processing event: {event_type} with payload: {payload}")

                if event_type in self._subscribers:
                    logger.info(f"DEBUG EventBus found {len(self._subscribers[event_type])} subscribers for {event_type}")
                    for callback in self._subscribers[event_type]:
                        try:
                            logger.info(f"DEBUG EventBus calling {callback.__name__}")
                            if asyncio.iscoroutinefunction(callback):
                                await callback(payload)
                            else:
                                callback(payload)
                            logger.info(f"DEBUG EventBus finished calling {callback.__name__}")
                        except Exception as e:
                            logger.error(f"Error in event handler for {event_type}", error=str(e), callback=callback.__name__)
                else:
                    logger.info(f"DEBUG EventBus no subscribers for {event_type}. Current subscribers: {list(self._subscribers.keys())}")

                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error processing event bus queue", error=str(e))

    def start(self):
        if self._queue is None:
            self._queue = asyncio.Queue()
        if self._task is None:
            self._task = asyncio.create_task(self._process_events())
            logger.info("EventBus started")

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("EventBus stopped")

# Global singleton
event_bus = EventBus()
