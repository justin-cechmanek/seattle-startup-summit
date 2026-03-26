# Build a Self‑Improving AI Assistant (30‑minute hands‑on workshop)

**Short title:** Self‑Improving AI Assistant with Redis Agent Memory Server

**Duration:** 25–30 minutes

**Audience:** AI engineers, founders, and developers who can run a small local Docker stack and a Python script/notebook.

**Objective:** By the end of the workshop each participant will have a running mini assistant that:

- extracts facts from user conversations automatically
- persists those facts as long‑term memories in Redis via Agent Memory Server (AMS)
- retrieves relevant memories to improve subsequent responses
- allows editing/deleting of memories for quick debugging

**Why this is cool in 25 minutes**
- Demonstrates an end‑to‑end memory lifecycle (observe → extract → store → retrieve → use)
- Feels magical: user corrects the assistant once and it "remembers" later
- Highlights production‑grade building blocks (AMS + Redis + embeddings)

---

## Prerequisites (what attendees need on their laptop)
- Laptop with Docker and Docker Compose installed
- Python 3.10+ and `pip`
- Git (optional)
- A free **Redis Cloud** account or willingness to run Redis locally via docker
- OpenAI API key (or other LLM key) in `OPENAI_API_KEY` environment variable

> Provide test dataset and code so they *don't* have to upload anything extra.

---

## Quick Setup (5–7 minutes)

Option A: Run Redis & AMS locally (recommended for demo reproducibility)

```bash
# start Redis Stack
docker run -d --name redis-stack -p 6379:6379 redis/redis-stack:latest

# start Agent Memory Server (AMS)
# the official docker image tag may change; use latest if available
docker run -d --name agent-memory-server -p 8000:8000 redis/agent-memory-server:latest

# verify
curl http://localhost:8000/health
```

Option B: Use Redis Cloud and AMS running in Docker (change config in .env)

**Files attendees will clone:**

```
self-improving-assistant-workshop/
├── README.md
├── requirements.txt
├── .env.example
├── demo_data/
│   └── onboarding.txt
├── agent.py
├── memory_manager.py
├── extractors.py
└── notebook.ipynb
```

---

## Workshop plan & minute-by-minute script (30 minutes)

**0:00–0:03 (3m) — Welcome & Hook**
- One quick slide: "Your assistant should learn from each conversation — we'll build that."
- Show a very short demo video/recording of the final assistant remembering a fact. (15–20s)

**0:03–0:08 (5m) — Setup check & local stack**
- Ask attendees to run the startup commands (Docker) if they haven't
- Confirm OpenAI key present: `export OPENAI_API_KEY=...`

**0:08–0:16 (8m) — Ingest + Automatic Extraction**
- Explain the idea of extraction (convert conversation to structured facts)
- Walk through `extractors.py` (simple rule-based + small LLM-based extractor)
- Run a demo where user says: "I prefer morning meetings and I love hiking."
- Show how extraction yields: `{ "prefers_meetings_at": "morning", "likes": ["hiking"] }`
- Save those facts into AMS via `memory_manager.create_long_term_memories(...)`

**0:16–0:22 (6m) — Retrieval + Use in Prompting**
- Show how the assistant fetches relevant memories at query time
- Run a query: "Schedule a meeting with me next week" → shows that assistant uses the `prefers_meetings_at` memory to suggest times
- Walk through the retrieval code and the prompt template that injects memories

**0:22–0:27 (5m) — Editing & Self‑improvement**
- Demonstrate editing a memory (fix a wrong fact)
- Show that subsequent queries use corrected memory
- Optionally show a simple UI snippet or `curl` commands to list / delete memories via AMS HTTP API

**0:27–0:30 (3m) — Recap & Next steps**
- Quick summary of architecture
- Give ideas to extend (multi-user, privacy, TTLs, embeddings, vector-only memories)
- Link to full repo and slides

---

## Core code snippets (drop‑in ready)

> The `agent.py` will orchestrate user input → extractor → store → respond.

### requirements.txt
```
openai
redis
requests
python-dotenv
fastapi
httpx
tqdm
```

### .env.example
```
OPENAI_API_KEY=sk-...
REDIS_URL=redis://localhost:6379
AMS_URL=http://localhost:8000
USER_ID=test_user
```

### extractors.py (simplified)
```python
# extractors.py — a tiny example extractor that uses a prompt-completion to extract simple facts
import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

EXTRACTION_PROMPT = """
Extract short JSON facts from the user message. Only output JSON. Keys: prefers_meetings_at, likes
User message: {message}
"""

async def extract_facts(message: str) -> dict:
    prompt = EXTRACTION_PROMPT.format(message=message)
    resp = client.chat.completions.create(model='gpt-4o-mini', messages=[{"role":"user","content":prompt}], max_tokens=200)
    # naive parse
    text = resp.choices[0].message.content
    import json
    try:
        return json.loads(text)
    except Exception:
        return {}
```

### memory_manager.py
```python
# memory_manager.py — talks to Agent Memory Server (AMS) HTTP API
import os
import requests

AMS_URL = os.environ.get('AMS_URL', 'http://localhost:8000')

def create_long_term_memories(user_id: str, memories: list):
    payload = {"user_id": user_id, "memories": memories}
    r = requests.post(f"{AMS_URL}/memories/long-term", json=payload)
    r.raise_for_status()
    return r.json()

def search_long_term_memory(user_id: str, query: str):
    r = requests.get(f"{AMS_URL}/memories/long-term/search", params={"user_id":user_id, "q":query})
    r.raise_for_status()
    return r.json()

def list_memories(user_id: str):
    r = requests.get(f"{AMS_URL}/memories/long-term", params={"user_id": user_id})
    r.raise_for_status()
    return r.json()

def delete_memory(user_id: str, memory_id: str):
    r = requests.delete(f"{AMS_URL}/memories/long-term/{memory_id}", params={"user_id": user_id})
    r.raise_for_status()
    return r.json()
```

### agent.py (or notebook cell)
```python
# agent.py — simplified end-to-end flow
import os
from extractors import extract_facts
from memory_manager import create_long_term_memories, search_long_term_memory

USER_ID = os.environ.get('USER_ID', 'test_user')

async def handle_user_message(message: str):
    # 1) extract facts
    facts = await extract_facts(message)
    memories = []
    for k,v in facts.items():
        memories.append({
            'text': f"{k}: {v}",
            'memory_type': 'semantic',
            'metadata': {'source': 'conversation', 'fact_key': k}
        })
    if memories:
        create_long_term_memories(USER_ID, memories)

    # 2) when answering later, retrieve related memories
    retrieved = search_long_term_memory(USER_ID, message)
    # build prompt with retrieved memories (simple concatenation)
    mem_text = "\n".join([m['text'] for m in retrieved.get('results', [])])

    answer_prompt = f"You are an assistant. Use these memories: {mem_text}\nUser asked: {message}"
    # call LLM for final answer (left as an exercise — use OpenAI or Anthropic)
    return answer_prompt

# small interactive demo
if __name__ == '__main__':
    import asyncio
    while True:
        msg = input('You: ')
        print('Assistant:', asyncio.run(handle_user_message(msg)))
```

---

## Demo data and scenarios (so attendees can reproduce quickly)
1. **Onboarding facts** — participant types: "I prefer morning meetings and I love hiking." → extractor should produce two facts.
2. **Follow-up use** — participant types later: "Schedule a 30‑minute sync next week" → assistant suggests morning slots.
3. **Correction** — participant types: "No, I actually prefer afternoons" → show deletion/edit flow and then re-query.

---

## Troubleshooting tips (common gotchas)
- If AMS returns 404 on `/memories/long-term`, ensure AMS container is up and that you used the correct image tag.
- If OpenAI calls fail, check `OPENAI_API_KEY` and network access.
- Extraction prompt might produce non‑JSON: include a fallback rule-based parser in `extractors.py` to avoid crashing.

---

## Extensions & next steps for participants (5–15 minute followups)
- Replace the extractor with a more advanced schema extractor (few‑shot examples)
- Add embeddings and semantic vector indexing in Redis (RedisVL) for faster retrieval
- Add privacy: mark memories as private and encrypt sensitive fields
- Build a small UI for listing and editing memories (FastAPI + simple HTML)
- Add TTLs or importance scores and automatic pruning

---

## Slide / Demo Checklist for presenter
- 1 slide: problem statement
- 1 slide: architecture diagram (user → extractor → AMS → Redis → LLM)
- 1 slide: commands to start stack
- 2 live demos (ingest facts; then use them)
- 1 slide: how AMS stores memories (json examples)
- 1 slide: next steps / repo link

---

## Repo & deliverables to attach to CFP
- `README.md` with one‑line setup and run instructions
- `demo_data/onboarding.txt` with sample utterances
- `agent.py`, `memory_manager.py`, `extractors.py`
- `notebook.ipynb` that walks step‑by‑step (cells for each block)
- `slides.pdf` (5–8 slides)

---

If you'd like, I can also:
- create the GitHub repo layout and push code examples for this workshop (I can generate the files here)
- produce a short 6‑slide deck
- produce the Jupyter notebook as a runnable file

I generated the runnable workshop files below. Each file is ready to copy into the repo `self-improving-assistant-workshop/`.

---

## File: requirements.txt
```
openai>=1.0.0
requests>=2.28.0
python-dotenv>=1.0.0
fastapi>=0.95.0
uvicorn>=0.22.0
httpx>=0.24.0
redis>=4.6.0
```

---

## File: .env.example
```
OPENAI_API_KEY=sk-REPLACE_ME
REDIS_URL=redis://localhost:6379
AMS_URL=http://localhost:8000
USER_ID=test_user
```

---

## File: README.md
```
# Self-Improving AI Assistant Workshop

## Quick start

1. Clone this repo.
2. Copy `.env.example` to `.env` and add your `OPENAI_API_KEY`.
3. Start Redis and Agent Memory Server (AMS):

```bash
# Redis Stack
docker run -d --name redis-stack -p 6379:6379 redis/redis-stack:latest

# Agent Memory Server (AMS)
docker run -d --name agent-memory-server -p 8000:8000 redislabs/agent-memory-server:latest
```

4. Install Python deps:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

5. Run the agent demo:

```bash
python agent.py
```

Type conversational lines like `I prefer morning meetings and I love hiking.` then ask `Schedule a meeting next week` to see the assistant use stored memories.
```

---

## File: extractors.py
```python
# extractors.py
import os
import json
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)

EXTRACTION_PROMPT = '''
You are a JSON extractor. Given a user message, output a JSON object with keys (only if present):
- prefers_meetings_at: one of "morning", "afternoon", "evening"
- likes: an array of short interests (e.g., hiking, cycling)

Only output valid JSON. If no facts are found, output {}.

User message: "{message}"
'''

async def extract_facts(message: str) -> dict:
    prompt = EXTRACTION_PROMPT.format(message=message)
    try:
        resp = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0
        )
        text = resp.choices[0].message.content.strip()
        return json.loads(text)
    except Exception as e:
        # Fallback: simple rule-based extractor
        facts = {}
        msg = message.lower()
        if 'morning' in msg:
            facts['prefers_meetings_at'] = 'morning'
        elif 'afternoon' in msg:
            facts['prefers_meetings_at'] = 'afternoon'
        elif 'evening' in msg:
            facts['prefers_meetings_at'] = 'evening'
        likes = []
        for kw in ['hiking', 'cycling', 'reading', 'cooking', 'travel']:
            if kw in msg:
                likes.append(kw)
        if likes:
            facts['likes'] = likes
        return facts
```

---

## File: memory_manager.py
```python
# memory_manager.py
import os
import requests
from dotenv import load_dotenv
load_dotenv()

AMS_URL = os.environ.get('AMS_URL', 'http://localhost:8000')

# Create long-term memories via AMS HTTP API
# NOTE: the exact AMS API path may differ depending on AMS version; adapt if necessary.

def create_long_term_memories(user_id: str, memories: list):
    payload = {"user_id": user_id, "memories": memories}
    r = requests.post(f"{AMS_URL}/memories/long-term", json=payload)
    r.raise_for_status()
    return r.json()

def search_long_term_memory(user_id: str, query: str, top_k: int = 5):
    params = {"user_id": user_id, "q": query, "top_k": top_k}
    r = requests.get(f"{AMS_URL}/memories/long-term/search", params=params)
    r.raise_for_status()
    return r.json()

def list_memories(user_id: str):
    params = {"user_id": user_id}
    r = requests.get(f"{AMS_URL}/memories/long-term", params=params)
    r.raise_for_status()
    return r.json()

def delete_memory(user_id: str, memory_id: str):
    r = requests.delete(f"{AMS_URL}/memories/long-term/{memory_id}", params={"user_id": user_id})
    r.raise_for_status()
    return r.json()
```

---

## File: agent.py
```python
# agent.py — simple interactive assistant demo
import os
import asyncio
import json
from dotenv import load_dotenv
load_dotenv()
from extractors import extract_facts
from memory_manager import create_long_term_memories, search_long_term_memory
from openai import OpenAI

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
USER_ID = os.environ.get('USER_ID', 'test_user')
client = OpenAI(api_key=OPENAI_API_KEY)

async def handle_user_message(message: str) -> str:
    # Step 1: extract facts and store
    facts = await extract_facts(message)
    memories = []
    for k, v in facts.items():
        mem_text = ''
        if isinstance(v, list):
            mem_text = f"{k}: {', '.join(v)}"
        else:
            mem_text = f"{k}: {v}"
        memories.append({
            'text': mem_text,
            'memory_type': 'semantic',
            'metadata': {'source': 'conversation', 'fact_key': k}
        })
    if memories:
        try:
            create_long_term_memories(USER_ID, memories)
        except Exception as e:
            print('Failed to create memories:', e)

    # Step 2: retrieve relevant memories
    try:
        res = search_long_term_memory(USER_ID, message)
        results = res.get('results', [])
    except Exception as e:
        print('Memory search failed:', e)
        results = []

    mem_text = '
'.join([r.get('text', '') for r in results])

    # Step 3: call LLM for final assistant reply, injecting memories
    prompt = f"You are a helpful assistant. Use the following memories if relevant:
{mem_text}

User: {message}
Assistant:"
    resp = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.2
    )
    answer = resp.choices[0].message.content.strip()
    return answer

async def repl():
    print('Self-improving assistant. Type messages. Ctrl+C to quit.')
    while True:
        msg = input('You: ').strip()
        if not msg:
            continue
        answer = await handle_user_message(msg)
        print('Assistant:', answer)

if __name__ == '__main__':
    try:
        asyncio.run(repl())
    except KeyboardInterrupt:
        print('
Goodbye')
```

---

## File: demo_data/onboarding.txt
```
I prefer morning meetings and I love hiking.
I like to work on backend systems and distributed systems.
I enjoy coffee and running.
No, actually I prefer afternoons for meetings.
```

---

## Notes
- The AMS HTTP API paths used above are based on common patterns; if your AMS image/version exposes different endpoints, update `memory_manager.py` accordingly.
- The OpenAI model names used (`gpt-4o-mini`, etc.) are examples — replace with the available model in your account.

---

If you'd like, I can now:
- create the Jupyter notebook cells from the same code,
- generate a 6-slide deck to accompany the live demo,
- or produce a zip file containing these files for download.

