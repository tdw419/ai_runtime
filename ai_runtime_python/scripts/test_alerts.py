#!/usr/bin/env python3
import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.daemon import AIDaemon  # noqa: E402


async def test_alerts() -> None:
    daemon = AIDaemon()

    print("Testing alert channels...")
    test_context = {
        "component": "alert_test",
        "test_run": True,
    }

    try:
        await daemon.send_alert({
            "level": "warning",
            "message": "Test alert from AI Daemon",
            "context": test_context,
        })
        print("✓ Alert sent successfully")
    except Exception as exc:
        print(f"✗ Alert failed: {exc}")


if __name__ == "__main__":
    asyncio.run(test_alerts())
