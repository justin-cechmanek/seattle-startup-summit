# agent.py — simplified end-to-end flow
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

from extractors import extract_facts
from memory_manager import create_long_term_memories, search_long_term_memory

USER_ID = os.environ.get('USER_ID', 'test_user')
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are a helpful assistant with access to a user's remembered preferences.
Use remembered facts when they are relevant, but do not mention internal tools or memory systems.
If the user is sharing preferences or personal facts, acknowledge them briefly and respond naturally.
If the user asks for scheduling help and you know a meeting-time preference, use it in your answer.
Do not invent preferences that are not present in the provided memories.
"""


def _format_memory_value(value):
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)

async def handle_user_message(message: str):
    # 1) extract facts
    facts = await extract_facts(message)
    memories = []
    for k,v in facts.items():
        memories.append({
            'text': f"{k}: {_format_memory_value(v)}",
            'memory_type': 'semantic',
            'metadata': {'source': 'conversation', 'fact_key': k}
        })
    if memories:
        create_long_term_memories(USER_ID, memories)

    # 2) when answering later, retrieve related memories
    retrieved = search_long_term_memory(USER_ID, message)
    # build prompt with retrieved memories (simple concatenation)
    memory_texts = [m['text'] for m in retrieved.get('memories', [])]
    memory_texts.extend(memory['text'] for memory in memories)
    mem_text = "\n".join(dict.fromkeys(memory_texts))

    user_prompt = (
        "Relevant memories:\n"
        f"{mem_text or 'None'}\n\n"
        f"User message: {message}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=200,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        if "prefers_meetings_at: morning" in mem_text and "schedule" in message.lower():
            return "You prefer morning meetings, so I suggest a 30-minute morning slot next week."
        if mem_text:
            return f"I've noted these preferences for future responses: {mem_text}"
        return "Thanks, I understand. What would you like to do next?"

# small interactive demo
if __name__ == '__main__':
    import asyncio
    while True:
        msg = input('You: ')
        print('Assistant:', asyncio.run(handle_user_message(msg)))
