"""FastAPI application entry point."""

from fastapi import FastAPI


app = FastAPI(
    title="Food Trucks Nearby Search API",
    version="0.1.0",
    description="Find San Francisco food trucks near a map location.",
)
