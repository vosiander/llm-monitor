"""
TickFunnel: Adaptive polling controller for LLM Monitor endpoints.

This module implements activity-based polling that adjusts refresh rates
based on frontend user activity (tick rate).
"""
import asyncio
from typing import Callable, Awaitable
from loguru import logger


class TickFunnel:
    """
    Adaptive polling controller that triggers refreshes based on 
    frontend activity (tick rate).
    
    Logic:
    - Counts ticks in 5-second windows
    - If >= tick_threshold ticks in window: trigger immediate refresh
    - Otherwise: wait for next window
    - Force refresh after max_cycles (60s max delay)
    - Reset counters after each refresh
    
    This dramatically reduces backend load during idle periods while
    maintaining immediate freshness during active use.
    """
    
    def __init__(self,
                 window_size: int = 5,        # 5 second windows
                 tick_threshold: int = 4,     # 4 ticks = active user
                 max_cycles: int = 12):       # 60s max delay (12 * 5s)
        """
        Initialize TickFunnel with configuration.
        
        Args:
            window_size: Duration of each window in seconds (default: 5)
            tick_threshold: Number of ticks needed to trigger immediate refresh (default: 4)
            max_cycles: Maximum cycles before forcing refresh (default: 12 = 60s)
        """
        self.window_size = window_size
        self.tick_threshold = tick_threshold
        self.max_cycles = max_cycles
        
        self.tick_count = 0
        self.cycle_count = 0
        self.refresh_callback: Callable[[], Awaitable[None]] | None = None
        self._lock = asyncio.Lock()
        self._cycle_task: asyncio.Task | None = None
        
        logger.info(
            f"TickFunnel initialized: window={window_size}s, "
            f"threshold={tick_threshold} ticks, "
            f"max_cycles={max_cycles} ({max_cycles * window_size}s max delay)"
        )
        
    async def start(self, refresh_callback: Callable[[], Awaitable[None]]):
        """
        Start the TickFunnel with a refresh callback.
        
        Args:
            refresh_callback: Async function to call when refresh is triggered
        """
        self.refresh_callback = refresh_callback
        self._cycle_task = asyncio.create_task(self._run_cycles())
        logger.info("TickFunnel started")
    
    async def tick(self):
        """
        Called by /tick endpoint - increment tick counter.
        
        If tick threshold is reached, triggers immediate refresh.
        """
        async with self._lock:
            self.tick_count += 1
            logger.debug(f"Tick received. Count: {self.tick_count}/{self.tick_threshold}")
            
            # Check if threshold reached
            if self.tick_count >= self.tick_threshold:
                logger.info(
                    f"Tick threshold reached ({self.tick_count} >= {self.tick_threshold}), "
                    "triggering refresh"
                )
                await self._trigger_refresh()
    
    async def _run_cycles(self):
        """
        Background task that checks cycles every window_size seconds.
        
        Runs continuously, managing cycle counting and forcing refreshes
        when max_cycles is reached.
        """
        logger.info("TickFunnel cycle loop started")
        
        while True:
            try:
                await asyncio.sleep(self.window_size)
                
                async with self._lock:
                    self.cycle_count += 1
                    logger.debug(
                        f"Cycle {self.cycle_count}/{self.max_cycles}, "
                        f"Ticks in window: {self.tick_count}"
                    )
                    
                    # Force refresh if max cycles reached
                    if self.cycle_count >= self.max_cycles:
                        logger.info(
                            f"Max cycles reached ({self.cycle_count}), "
                            "forcing refresh"
                        )
                        await self._trigger_refresh()
                    
                    # Reset tick count for next window
                    self.tick_count = 0
                    
            except asyncio.CancelledError:
                logger.info("TickFunnel cycle loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in TickFunnel cycle loop: {e}")
    
    async def _trigger_refresh(self):
        """
        Execute refresh callback and reset counters.
        
        This method is called either when:
        1. Tick threshold is reached (active user)
        2. Max cycles reached (force refresh for idle user)
        """
        if self.refresh_callback:
            try:
                await self.refresh_callback()
                logger.info("Refresh triggered successfully")
            except Exception as e:
                logger.error(f"Error during refresh: {e}")
        else:
            logger.warning("Refresh triggered but no callback registered")
        
        # Reset counters
        self.tick_count = 0
        self.cycle_count = 0
        logger.debug("Counters reset")
    
    async def stop(self):
        """Stop the TickFunnel and cancel background tasks."""
        if self._cycle_task:
            self._cycle_task.cancel()
            try:
                await self._cycle_task
            except asyncio.CancelledError:
                pass
        logger.info("TickFunnel stopped")


# Global TickFunnel instance
_tick_funnel: TickFunnel | None = None


def get_tick_funnel() -> TickFunnel:
    """
    Get or create the global TickFunnel instance.
    
    Returns:
        Global TickFunnel instance
    """
    global _tick_funnel
    if _tick_funnel is None:
        _tick_funnel = TickFunnel()
    return _tick_funnel
