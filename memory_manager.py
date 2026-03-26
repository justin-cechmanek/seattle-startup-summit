# memory_manager.py — talks to Agent Memory Server (AMS) HTTP API
import os
from uuid import uuid4

import requests
from dotenv import load_dotenv

load_dotenv()

AMS_URL = os.environ.get('AMS_URL', 'http://localhost:8000')
AMS_V1_URL = f"{AMS_URL.rstrip('/')}/v1"

def create_long_term_memories(user_id: str, memories: list):
    payload = {
        "memories": [
            {
                "id": memory.get("id", f"mem-{uuid4()}"),
                "user_id": user_id,
                **memory,
            }
            for memory in memories
        ]
    }
    r = requests.post(f"{AMS_V1_URL}/long-term-memory/", json=payload)
    r.raise_for_status()
    return r.json()

def search_long_term_memory(user_id: str, query: str):
    payload = {
        "text": query,
        "user_id": {"eq": user_id},
        "limit": 10,
    }
    r = requests.post(f"{AMS_V1_URL}/long-term-memory/search", json=payload)
    r.raise_for_status()
    return r.json()

def list_memories(user_id: str):
    payload = {
        "user_id": {"eq": user_id},
        "limit": 100,
    }
    r = requests.post(f"{AMS_V1_URL}/long-term-memory/search", json=payload)
    r.raise_for_status()
    return r.json()

def delete_memory(user_id: str, memory_id: str):
    r = requests.delete(
        f"{AMS_V1_URL}/long-term-memory",
        params={"memory_ids": memory_id},
    )
    r.raise_for_status()
    return r.json()
