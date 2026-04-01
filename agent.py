# agent.py — AMS-native interactive showcase
import asyncio
import os
import time
from dotenv import load_dotenv
from openai import AsyncOpenAI
from requests import RequestException

from agent_memory_client import MemoryAPIClient, MemoryClientConfig
from agent_memory_client.models import MemoryMessage, MemoryStrategyConfig


load_dotenv()

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
USER_ID = "justin"
NAMESPACE = "LIVE_DEMO"
SESSION_PREFIX = os.environ.get("SESSION_PREFIX", "ams-demo")
DEFAULT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-5.4")

SYSTEM_PROMPT = """You are a helpful assistant with access to a user's remembered preferences.
Use remembered facts when they are relevant, but do not mention internal tools or memory systems.
If the user is sharing preferences or personal facts, acknowledge them briefly and respond naturally.
Do not invent preferences that are not present in the provided memories.
"""

llm_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def _message_text(message):
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        return content.get("text", "")
    return str(content)


def _recent_transcript(messages, limit=6):
    lines = []
    for message in messages[-limit:]:
        lines.append(f"{message.get('role', 'unknown')}: {_message_text(message)}")
    return "\n".join(lines)


def _render_memories(memories):
    if not memories:
        print("No memories found.")
        return

    for memory in memories:
        print(
            f"- id={memory.get('id')} text={memory.get('text')} "
            f"memory_type={memory.get('memory_type')} score={memory.get('score')}"
        )


def _working_memory_payload(user_id, messages, existing_working_memory):
    payload = {
        "user_id": user_id,
        "messages": messages,
    }
    if existing_working_memory.get("context"):
        payload["context"] = existing_working_memory.get("context")
    if existing_working_memory.get("data"):
        payload["data"] = existing_working_memory.get("data")
    return payload


async def handle_user_message(message, user_id=USER_ID):
    session_id = SESSION_PREFIX
    result = {
        "user_id": user_id,
        "session_id": session_id,
        "message": message,
        "working_memory_payload": {},
        "working_memory_after": None,
        "retrieved_memories": [],
        "prompt_memory_text": "",
        "errors": [],
        "answer": "",
    }

    existing_working_memory = {
        "messages": [],
        "memories": [],
        "context": None,
        "data": None,
    }
    try:
        existing_working_memory = get_working_memory(session_id, user_id)
    except RequestException as exc:
        result["errors"].append(f"AMS working-memory read failed: {exc}")

    updated_messages = list(existing_working_memory.get("messages", []))
    updated_messages.append({"role": "user", "content": message})
    result["working_memory_payload"] = _working_memory_payload(
        user_id,
        updated_messages,
        existing_working_memory,
    )

    working_memory_after = existing_working_memory
    try:
        working_memory_after = put_working_memory(
            session_id,
            user_id,
            updated_messages,
            context=existing_working_memory.get("context"),
            data=existing_working_memory.get("data"),
            model_name=DEFAULT_MODEL,
        )
        result["working_memory_after"] = working_memory_after
    except RequestException as exc:
        result["errors"].append(f"AMS working-memory write failed: {exc}")

    try:
        retrieved = search_long_term_memory(user_id, message)
        result["retrieved_memories"] = retrieved.get("memories", [])
    except RequestException as exc:
        result["errors"].append(f"AMS long-term search failed: {exc}")

    working_memory_structured = working_memory_after.get("memories", []) or []
    memory_texts = [
        memory.get("text", "")
        for memory in result["retrieved_memories"] + working_memory_structured
        if memory.get("text")
    ]
    result["prompt_memory_text"] = "\n".join(dict.fromkeys(memory_texts))

    recent_transcript = _recent_transcript(working_memory_after.get("messages", []))
    user_prompt = (
        "Recent conversation:\n"
        f"{recent_transcript or 'None'}\n\n"
        "Relevant memories:\n"
        f"{result['prompt_memory_text'] or 'None'}\n\n"
        f"Respond to the latest user message: {message}"
    )

    try:
        response = await llm_client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_completion_tokens=200,
            temperature=0.2,
        )
        result["answer"] = (response.choices[0].message.content or "").strip()
    except Exception as exc:
        result["errors"].append(f"LLM response failed: {exc}")
    return result


def _clear_user(user_id):
    _print_header(f"Clear memories for {user_id}")
    try:
        deleted = delete_all_memories(user_id)
    except RequestException as exc:
        print(f"AMS long-term clear failed: {exc}")
        deleted = []

    try:
        delete_working_memory(SESSION_PREFIX, user_id)
        print("Deleted working memory session.")
    except RequestException as exc:
        print(f"AMS working-memory clear failed: {exc}")

    if deleted:
        print("Deleted long-term memory IDs:")
        for memory_id in deleted:
            print(f"- {memory_id}")
    elif not deleted:
        print("No long-term memories to delete.")



async def parse_prompt(prompt, client):
    if not prompt.startswith("/"):
        return prompt
    command, * args = prompt.split(" ")
    if command == "/help":
        print( "Available commands: help, clear, correct, delete, show, memories, working_memory")
    if command == "/clear":
        print( "Clearing memories and working memory...")
    if command == "/correct":
        print( "Correcting memory...")
    if command == "/delete":
        print( "Deleting memory_id: {args[0]}...")
        deleted = await client.delete_memory(args[0])
        print(deleted)
    if command == "/show_transcript":
        print( "Showing conversation transcript...")
        print('========================================')
        prompt_result = await client.memory_prompt(
            session_id=SESSION_PREFIX,
            query=" ".join(args[0:]),
            namespace=NAMESPACE,
            user_id=USER_ID,
            long_term_search={"user_id": {"eq": USER_ID}}
        )
        for m in prompt_result.get("messages", []):
            print(f"{m['role']}: {_message_text(m)}")
        print('========================================')
        return
    if command == "/show_memories":
        print(f"Showing memories for {USER_ID}")
        print('========================================')
        result = await client.search_long_term_memory(
            text=" ".join(args[0:]),  # Broad search
            namespace={"eq": NAMESPACE},
            user_id={"eq": USER_ID},
            limit=20,
        )
        for memory in result.memories:
            topics = memory.topics if memory.topics else []
            print(f"{memory.text}\n  topics: {topics}\n")
        print('========================================')
        return
    if command == "/exit":
        print( "Exiting...")
        exit()
    return prompt

async def async_main():
    config = MemoryClientConfig(
        base_url=BASE_URL,
        timeout=30.0,
        default_namespace=NAMESPACE,
    )

    client = MemoryAPIClient(config)
    created, working_memory = await client.get_or_create_working_memory(
        session_id=SESSION_PREFIX,
        namespace=NAMESPACE,
        user_id=USER_ID,
        long_term_memory_strategy=MemoryStrategyConfig(
            strategy="preferences"
        ),
    )


    while True:
        try:
            user_prompt = input(f"{USER_ID}> ").strip()
            user_prompt = await parse_prompt(user_prompt, client)
            if not user_prompt:
                continue
        except EOFError:
            print()
            break


        # get relevant memories from working_memory
        prompt_result = await client.memory_prompt(
            session_id=SESSION_PREFIX,
            query=user_prompt,
            namespace=NAMESPACE,
            user_id=USER_ID,
            long_term_search={
                "limit": 5,
                # distance_threshold: Lower = stricter when set. If omitted, the server
                # uses no distance filter (distance_threshold=None) for broader KNN recall.
                "user_id": {"eq": USER_ID}  # Only search this user's memories
            }
        )

        response = await llm_client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": m["role"], "content": _message_text(m)} for m in (prompt_result.get("messages") or [])
            ]
            + [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_prompt}],
            max_completion_tokens=200,
            temperature=0.2,
        )
        response = response.choices[0].message.content.strip()
        print(response)

        if (not user_prompt) or (not response):
            continue

        # append response to working_memory
        await client.append_messages_to_working_memory(messages=[
            MemoryMessage(role="user", content=user_prompt, created_at=time.time()),
            MemoryMessage(role="assistant", content=response, created_at=time.time()),
            ],
        session_id=SESSION_PREFIX,
        namespace=NAMESPACE,
        user_id=USER_ID,
        )
        # continue conversation


if __name__ == "__main__":
    asyncio.run(async_main())
