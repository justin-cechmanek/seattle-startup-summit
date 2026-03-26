# memory_manager.py — talks to Agent Memory Server (AMS) HTTP API
import os

import requests
from dotenv import load_dotenv

load_dotenv()

AMS_URL = os.environ.get("AMS_URL", "http://localhost:8000")
AMS_V1_URL = f"{AMS_URL.rstrip('/')}/v1"
REQUEST_TIMEOUT_SECONDS = 10
DEFAULT_MODEL_NAME = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")


def _raise_for_status(response):
    response.raise_for_status()
    return response


def healthcheck():
    response = requests.get(f"{AMS_V1_URL}/health", timeout=REQUEST_TIMEOUT_SECONDS)
    return _raise_for_status(response).json()


def get_working_memory(session_id, user_id, model_name=DEFAULT_MODEL_NAME):
    response = requests.get(
        f"{AMS_V1_URL}/working-memory/{session_id}",
        params={"user_id": user_id, "model_name": model_name},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code == 404:
        return {
            "session_id": session_id,
            "user_id": user_id,
            "messages": [],
            "memories": [],
            "context": None,
        }
    return _raise_for_status(response).json()


def put_working_memory(
    session_id,
    user_id,
    messages,
    memories=None,
    context=None,
    data=None,
    model_name=DEFAULT_MODEL_NAME,
):
    payload = {
        "user_id": user_id,
        "messages": messages,
    }
    if memories is not None:
        payload["memories"] = memories
    if context is not None:
        payload["context"] = context
    if data is not None:
        payload["data"] = data

    response = requests.put(
        f"{AMS_V1_URL}/working-memory/{session_id}",
        params={"model_name": model_name},
        json=payload,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    return _raise_for_status(response).json()


def delete_working_memory(session_id, user_id):
    response = requests.delete(
        f"{AMS_V1_URL}/working-memory/{session_id}",
        params={"user_id": user_id},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    return _raise_for_status(response).json()


def search_long_term_memory(user_id, query, limit=10):
    payload = {
        "text": query,
        "user_id": {"eq": user_id},
        "limit": limit,
    }
    response = requests.post(
        f"{AMS_V1_URL}/long-term-memory/search",
        json=payload,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    return _raise_for_status(response).json()


def list_memories(user_id, limit=100):
    payload = {
        "text": "",
        "user_id": {"eq": user_id},
        "limit": limit,
    }
    response = requests.post(
        f"{AMS_V1_URL}/long-term-memory/search",
        json=payload,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    return _raise_for_status(response).json()


def update_memory(memory_id, updates):
    response = requests.patch(
        f"{AMS_V1_URL}/long-term-memory/{memory_id}",
        json=updates,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    return _raise_for_status(response).json()


def delete_memory(memory_id):
    response = requests.delete(
        f"{AMS_V1_URL}/long-term-memory",
        params={"memory_ids": memory_id},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    return _raise_for_status(response).json()


def delete_all_memories(user_id):
    memories = list_memories(user_id).get("memories", [])
    deleted = []
    for memory in memories:
        memory_id = memory.get("id")
        if not memory_id:
            continue
        delete_memory(memory_id)
        deleted.append(memory_id)
    return deleted
