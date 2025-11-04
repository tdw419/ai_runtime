#!/usr/bin/env python3

try:
    from core.structured_logger import StructuredLogger
    print("✓ structured_logger.py imports successfully")
except SyntaxError as e:
    print(f"✗ Syntax error in structured_logger.py: {e}")
except Exception as e:
    print(f"✗ Other error: {e}")

print("Syntax check complete")
