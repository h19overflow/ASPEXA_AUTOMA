"""FastStream event consumer base utilities."""
from typing import Callable, Any
from faststream.redis import RedisBroker
from libs.events.publisher import broker


def subscribe_to_stream(
    stream: str,
    group: str,
    handler: Callable
):
    """
    Subscribe to a Redis stream with a consumer group.
    
    Args:
        stream: Stream name to subscribe to
        group: Consumer group name
        handler: Async function to handle messages
    
    Returns:
        Decorated handler function
    """
    return broker.subscriber(stream, group=group)(handler)


def subscribe_fanout(
    stream: str,
    group: str,
    handler: Callable
):
    """
    Subscribe to a stream in fan-out mode (different groups get all messages).
    
    Args:
        stream: Stream name to subscribe to
        group: Unique consumer group name for this service
        handler: Async function to handle messages
    
    Returns:
        Decorated handler function
    """
    return broker.subscriber(stream, group=group)(handler)


def subscribe_load_balanced(
    stream: str,
    group: str,
    handler: Callable
):
    """
    Subscribe to a stream in load-balanced mode (same group shares messages).
    
    Args:
        stream: Stream name to subscribe to
        group: Shared consumer group name
        handler: Async function to handle messages
    
    Returns:
        Decorated handler function
    """
    return broker.subscriber(stream, group=group)(handler)


def subscribe_serial(
    stream: str,
    group: str,
    handler: Callable
):
    """
    Subscribe to a stream with serial execution (one message at a time).
    Used for safety-critical operations like attack execution.
    
    Args:
        stream: Stream name to subscribe to
        group: Consumer group name
        handler: Async function to handle messages
    
    Returns:
        Decorated handler function
    """
    # Serial execution is enforced by deployment (1 replica)
    # or application-level locking
    return broker.subscriber(stream, group=group)(handler)
