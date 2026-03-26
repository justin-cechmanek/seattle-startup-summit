# agent.py — AMS-native interactive showcase
import argparse
import asyncio
import json
import os
import shlex

from dotenv import load_dotenv
from openai import OpenAI
from requests import RequestException

load_dotenv()

from memory_manager import (
    delete_all_memories,
    delete_memory,
    delete_working_memory,
    get_working_memory,
    healthcheck,
    list_memories,
    put_working_memory,
    search_long_term_memory,
    update_memory,
)

USER_ID = os.environ.get("USER_ID", "test_user")
SESSION_PREFIX = os.environ.get("SESSION_PREFIX", "ams-demo")
DEFAULT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a helpful assistant with access to a user's remembered preferences.
Use remembered facts when they are relevant, but do not mention internal tools or memory systems.
If the user is sharing preferences or personal facts, acknowledge them briefly and respond naturally.
If the user asks for scheduling help and you know a meeting-time preference, use it in your answer.
Do not invent preferences that are not present in the provided memories.
"""


def _print_header(title):
    print(f"\n=== {title} ===")


def _json_dump(payload):
    return json.dumps(payload, indent=2, sort_keys=True)


def _session_id_for_user(user_id):
    return f"{SESSION_PREFIX}:{user_id}"


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


def _fallback_answer(message, mem_text):
    lower_message = message.lower()
    is_scheduling_request = any(
        phrase in lower_message
        for phrase in ("schedule", "sync", "calendar", "time slot", "availability")
    )
    if is_scheduling_request:
        if "afternoon" in mem_text.lower():
            return "You prefer afternoon meetings, so I suggest a 30-minute afternoon slot next week."
        if "morning" in mem_text.lower():
            return "You prefer morning meetings, so I suggest a 30-minute morning slot next week."
        if "evening" in mem_text.lower():
            return "You prefer evening meetings, so I suggest a 30-minute evening slot next week."
        return "I can suggest a 30-minute slot next week. If you share a meeting-time preference, I can tailor it."

    if mem_text:
        return f"I've stored these memories for future turns:\n{mem_text}"

    return "Thanks, I understand. What would you like to do next?"


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


def _print_observable_result(result):
    _print_header(f"AMS Trace for user={result['user_id']}")
    print(f"Session ID: {result['session_id']}")
    print(f"User message: {result['message']}")

    print("\nWorking memory update payload:")
    print(_json_dump(result["working_memory_payload"]))

    if result["working_memory_after"] is not None:
        print("\nWorking memory after PUT:")
        print(_json_dump(result["working_memory_after"]))

    print("\nLong-term memories retrieved:")
    _render_memories(result["retrieved_memories"])

    print("\nPrompt memory context:")
    print(result["prompt_memory_text"] or "None")

    if result["errors"]:
        print("\nErrors:")
        for error in result["errors"]:
            print(f"- {error}")


async def handle_user_message(message, user_id=USER_ID, debug=False):
    session_id = _session_id_for_user(user_id)
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
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=200,
            temperature=0.2,
        )
        result["answer"] = response.choices[0].message.content.strip()
    except Exception as exc:
        result["errors"].append(f"LLM response failed: {exc}")
        result["answer"] = _fallback_answer(message, result["prompt_memory_text"])

    if debug:
        _print_observable_result(result)

    return result


def _show_health():
    _print_header("AMS Health")
    try:
        print(_json_dump(healthcheck()))
    except RequestException as exc:
        print(f"AMS health check failed: {exc}")


def _show_working_memory(user_id):
    _print_header(f"Working memory for {user_id}")
    try:
        working_memory = get_working_memory(_session_id_for_user(user_id), user_id)
    except RequestException as exc:
        print(f"AMS working-memory read failed: {exc}")
        return
    print(_json_dump(working_memory))


def _show_memories(user_id):
    _print_header(f"Long-term memories for {user_id}")
    try:
        memories = list_memories(user_id).get("memories", [])
    except RequestException as exc:
        print(f"AMS list failed: {exc}")
        return
    _render_memories(memories)


def _search_memories(user_id, query):
    _print_header(f"Search long-term memories for {user_id}")
    print(f"Query: {query}")
    try:
        memories = search_long_term_memory(user_id, query).get("memories", [])
    except RequestException as exc:
        print(f"AMS search failed: {exc}")
        return []
    _render_memories(memories)
    return memories


def _delete_memory(memory_id):
    _print_header("Delete Memory")
    try:
        print(_json_dump(delete_memory(memory_id)))
    except RequestException as exc:
        print(f"AMS delete failed: {exc}")


def _clear_user(user_id):
    _print_header(f"Clear memories for {user_id}")
    try:
        deleted = delete_all_memories(user_id)
    except RequestException as exc:
        print(f"AMS long-term clear failed: {exc}")
        deleted = []

    try:
        delete_working_memory(_session_id_for_user(user_id), user_id)
        print("Deleted working memory session.")
    except RequestException as exc:
        print(f"AMS working-memory clear failed: {exc}")

    if deleted:
        print("Deleted long-term memory IDs:")
        for memory_id in deleted:
            print(f"- {memory_id}")
    elif not deleted:
        print("No long-term memories to delete.")


def _correct_memory(memory_id, new_text):
    _print_header("Correct Memory")
    print(f"Updating memory {memory_id}")
    try:
        print(_json_dump(update_memory(memory_id, {"text": new_text})))
    except RequestException as exc:
        print(f"AMS correction failed: {exc}")


async def _wait_for_long_term_memory(user_id, query, min_count=1, attempts=8, delay_seconds=0.75):
    for _ in range(attempts):
        try:
            memories = search_long_term_memory(user_id, query).get("memories", [])
        except RequestException:
            return []
        if len(memories) >= min_count:
            return memories
        await asyncio.sleep(delay_seconds)
    return []


async def _run_turn(user_id, message, debug):
    print(f"\nUSER ({user_id}): {message}")
    result = await handle_user_message(message, user_id=user_id, debug=debug)
    print(f"ASSISTANT: {result['answer']}")
    return result


def _find_first_memory_id_by_query(user_id, query):
    try:
        memories = search_long_term_memory(user_id, query).get("memories", [])
    except RequestException:
        return None
    if not memories:
        return None
    return memories[0].get("id")


async def run_showcase(debug=True):
    alice = "alice"
    bob = "bob"

    _print_header("Redis AMS Showcase")
    print("This walkthrough demonstrates AMS-managed extraction from working memory,")
    print("observable working-memory writes, long-term search, memory editing, and multi-user isolation.")

    _show_health()

    for user_id in (alice, bob):
        _clear_user(user_id)

    await _run_turn(alice, "Can you schedule a 30-minute sync next week?", debug)
    await _run_turn(
        alice,
        (
            "I'm a product engineer based in Seattle. I prefer morning meetings, "
            "I'm vegetarian, I'm working on Summit Copilot, and I love hiking and espresso."
        ),
        debug,
    )
    await _wait_for_long_term_memory(alice, "Seattle morning vegetarian Summit Copilot", min_count=1)
    _show_working_memory(alice)
    _show_memories(alice)
    _search_memories(alice, "Summit Copilot vegetarian Seattle")
    await _run_turn(alice, "Can you schedule a 30-minute sync next week?", debug)

    memory_id = _find_first_memory_id_by_query(alice, "morning meetings preference")
    if memory_id:
        _correct_memory(memory_id, "User prefers afternoon meetings.")
    else:
        print("\nNo memory matched the correction query. Skip the edit or inspect /list output.")
    _show_memories(alice)
    await _run_turn(alice, "Can you schedule a 30-minute sync next week?", debug)

    await _run_turn(
        bob,
        (
            "I'm a founder in New York. I prefer evening meetings, "
            "I'm vegan, and I'm building FinPilot."
        ),
        debug,
    )
    await _wait_for_long_term_memory(bob, "New York evening vegan FinPilot", min_count=1)
    await _run_turn(bob, "Can you schedule a 30-minute sync next week?", debug)

    _print_header("Isolation Check")
    print("Alice:")
    _show_memories(alice)
    print("\nBob:")
    _show_memories(bob)


def _print_help():
    _print_header("Commands")
    print("/help                             Show commands")
    print("/showcase                         Run the scripted AMS showcase")
    print("/debug on|off                     Toggle verbose AMS tracing")
    print("/user <user_id>                   Switch the active user")
    print("/health                           Check AMS health")
    print("/working                          Show working memory for the active user")
    print("/list                             List long-term memories for the active user")
    print("/search <query>                   Search long-term memories for the active user")
    print("/delete <memory_id>               Delete a memory by ID")
    print("/correct <memory_id> <new text>   Patch a memory's text by ID")
    print("/clear                            Delete working and long-term memory for the active user")
    print("/quit                             Exit")
    print("\nAny other input is appended to AMS working memory and handled through the assistant pipeline.")


async def interactive_cli(default_user_id, debug):
    current_user_id = default_user_id
    _print_header("AMS Interactive Demo")
    print(f"Active user: {current_user_id}")
    print("Use /showcase for the guided demo or /help for commands.")

    while True:
        try:
            raw = input(f"{current_user_id}> ").strip()
        except EOFError:
            print()
            break

        if not raw:
            continue

        if raw.startswith("/"):
            parts = shlex.split(raw)
            command = parts[0]

            if command == "/help":
                _print_help()
            elif command == "/showcase":
                await run_showcase(debug=debug)
            elif command == "/debug" and len(parts) == 2:
                debug = parts[1].lower() == "on"
                print(f"Debug tracing {'enabled' if debug else 'disabled'}.")
            elif command == "/user" and len(parts) == 2:
                current_user_id = parts[1]
                print(f"Active user switched to {current_user_id}.")
            elif command == "/health":
                _show_health()
            elif command == "/working":
                _show_working_memory(current_user_id)
            elif command == "/list":
                _show_memories(current_user_id)
            elif command == "/search" and len(parts) >= 2:
                _search_memories(current_user_id, " ".join(parts[1:]))
            elif command == "/delete" and len(parts) == 2:
                _delete_memory(parts[1])
            elif command == "/clear":
                _clear_user(current_user_id)
            elif command == "/correct" and len(parts) >= 3:
                _correct_memory(parts[1], " ".join(parts[2:]))
            elif command == "/quit":
                break
            else:
                print("Unknown command. Use /help.")
            continue

        result = await handle_user_message(raw, user_id=current_user_id, debug=debug)
        print(f"Assistant: {result['answer']}")


def main():
    parser = argparse.ArgumentParser(description="Redis AMS workshop demo")
    parser.add_argument(
        "--showcase",
        action="store_true",
        help="run the scripted AMS showcase and exit",
    )
    parser.add_argument(
        "--user-id",
        default=USER_ID,
        help="default user id for interactive mode",
    )
    parser.add_argument(
        "--no-debug",
        action="store_true",
        help="disable verbose AMS tracing",
    )
    args = parser.parse_args()

    debug = not args.no_debug
    if args.showcase:
        asyncio.run(run_showcase(debug=debug))
        return

    asyncio.run(interactive_cli(default_user_id=args.user_id, debug=debug))


if __name__ == "__main__":
    main()
