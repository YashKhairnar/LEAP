"""Explicit development/pilot/study labels; never silently promote dev records."""
import os


def collection_mode() -> str:
    mode = os.getenv("LEAP_COLLECTION_MODE", "development")
    if mode not in {"development", "pilot", "study"}:
        raise ValueError("LEAP_COLLECTION_MODE must be development, pilot, or study")
    return mode


def assessment_preview_allowed() -> bool:
    return collection_mode() == "development" and os.getenv("ENVIRONMENT", "development").lower() != "production"
