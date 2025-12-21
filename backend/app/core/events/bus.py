"""
Event Bus for Decoupled Service Communication

This module provides an event bus system for publishing and subscribing to events.
Events are used for cross-cutting concerns that can be asynchronous (notifications,
audit logs, analytics, etc.) and don't need to block the main business logic flow.
"""
from typing import List, Callable, Dict, Type
from abc import ABC
import logging
from concurrent.futures import ThreadPoolExecutor
import asyncio

logger = logging.getLogger(__name__)


class Event(ABC):
    """Base event class - all events inherit from this"""
    pass


class EventBus:
    """Event bus for decoupled service communication"""
    
    def __init__(self):
        self._subscribers: Dict[Type[Event], List[Callable]] = {}
        self._executor = ThreadPoolExecutor(max_workers=10)
        logger.info("Event bus initialized")
    
    def subscribe(self, event_type: Type[Event], handler: Callable):
        """
        Subscribe to an event type
        
        Args:
            event_type: The event class to subscribe to
            handler: Callable that handles the event
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed handler {handler.__name__} to {event_type.__name__}")
    
    def publish(self, event: Event):
        """
        Publish an event to all subscribers (synchronous)
        
        Events are handled synchronously but handlers should be fast.
        For long-running operations, use publish_async.
        
        Args:
            event: Event instance to publish
        """
        event_type = type(event)
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(
                        f"Error handling event {event_type.__name__} in {handler.__name__}: {e}",
                        exc_info=True
                    )
        else:
            logger.debug(f"No subscribers for event {event_type.__name__}")
    
    async def publish_async(self, event: Event):
        """
        Publish an event to all subscribers (asynchronous)
        
        Use this for handlers that may take time (API calls, database operations, etc.)
        
        Args:
            event: Event instance to publish
        """
        event_type = type(event)
        if event_type in self._subscribers:
            tasks = []
            for handler in self._subscribers[event_type]:
                if asyncio.iscoroutinefunction(handler):
                    tasks.append(handler(event))
                else:
                    # Run sync handler in thread pool
                    tasks.append(asyncio.get_event_loop().run_in_executor(
                        self._executor, handler, event
                    ))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                # Log any exceptions
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        handler = self._subscribers[event_type][i]
                        logger.error(
                            f"Error in async handler {handler.__name__} for {event_type.__name__}: {result}",
                            exc_info=True
                        )
        else:
            logger.debug(f"No subscribers for event {event_type.__name__}")


# Global event bus instance
event_bus = EventBus()


