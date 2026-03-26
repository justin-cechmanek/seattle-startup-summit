# Build a Self-Improving AI Assistant (30-minute hands-on workshop)

**Short title:** Self-Improving AI Assistant with Redis Agent Memory Server

**Duration:** 25-30 minutes

**Audience:** AI engineers, founders, and developers who can run a small local Docker stack and a Python script or notebook.

## Objective

By the end of the workshop each participant will have a running mini assistant that:

- writes raw conversation turns into AMS working memory
- lets AMS extract and promote useful long-term memories
- retrieves relevant memories to improve later responses
- inspects working memory and long-term memory directly
- patches or deletes stored memories for debugging and correction

## Why this works in 25 minutes

- The architecture is small enough to explain live.
- AMS is visible instead of hidden behind app-side extraction code.
- The before/after behavior is easy to demonstrate with one profile message and one follow-up scheduling question.
- Correction and multi-user isolation give the demo a concrete production feel.

## Prerequisites

- Docker and Docker Compose
- Python 3.10+
- An `OPENAI_API_KEY`

## Repo layout

```text
self-improving-assistant-workshop/
├── README.md
├── RUN_DEMO.md
├── .env.example
├── compose.yaml
├── demo_data/
│   └── onboarding.txt
├── agent.py
├── memory_manager.py
└── self_improving_assistant_workshop.ipynb
```

## Quick setup

```bash
cp .env.example .env
docker compose up -d
curl http://localhost:8000/v1/health
pip install -r requirements.txt
python3 agent.py --showcase
```

`compose.yaml` enables AMS discrete memory extraction and connects AMS to Redis over Docker's internal network.

## Architecture

```text
user message
  -> agent.py
  -> AMS working memory PUT
  -> AMS extracts/promotes useful memories
  -> long-term memory search
  -> LLM response grounded with retrieved memories
```

## Workshop plan

**0:00-0:03 - Hook**

- Show the assistant answering a scheduling question without memory.
- Show the same question answered differently after a profile message is stored.

**0:03-0:08 - Setup**

- Start Docker services with `docker compose up -d`
- Verify AMS with `curl http://localhost:8000/v1/health`
- Install Python dependencies

**0:08-0:16 - Observable AMS write**

- Walk through `memory_manager.py`
- Show `agent.py` appending a raw user message to working memory
- Run `python3 agent.py --showcase`
- Point out the working-memory payload and AMS response

**0:16-0:22 - Retrieval and prompting**

- Inspect working memory with `/working`
- Inspect long-term memories with `/list`
- Search with `/search Summit Copilot vegetarian Seattle`
- Ask the scheduling question again and show the changed answer

**0:22-0:27 - Correction and isolation**

- Patch a memory with `/correct <memory_id> User prefers afternoon meetings.`
- Ask the scheduling question again
- Switch to `bob` with `/user bob` and repeat with a different profile

**0:27-0:30 - Recap**

- Summarize working memory vs long-term memory
- Discuss extensions like TTLs, privacy, summarization, and UI

## Core files

### `memory_manager.py`

- `get_working_memory(...)`
- `put_working_memory(...)`
- `search_long_term_memory(...)`
- `list_memories(...)`
- `update_memory(...)`
- `delete_memory(...)`

These helpers target the current AMS `/v1` API.

### `agent.py`

The CLI supports:

- `/showcase`
- `/working`
- `/list`
- `/search <query>`
- `/correct <memory_id> <new text>`
- `/delete <memory_id>`
- `/user <user_id>`
- `/clear`

Any non-command input is appended to AMS working memory and then answered using retrieved memory context.

## Demo scenarios

1. Before/after:
   Ask `Can you schedule a 30-minute sync next week?` before any memory exists.
2. Rich profile:
   Add `I'm a product engineer based in Seattle. I prefer morning meetings, I'm vegetarian, I'm working on Summit Copilot, and I love hiking and espresso.`
3. Inspect:
   Run `/working`, `/list`, and `/search Summit Copilot vegetarian Seattle`
4. Correct:
   Patch a memory by ID with `/correct <memory_id> User prefers afternoon meetings.`
5. Isolate:
   Switch to `bob`, add a different profile, and compare stored memory and answers.

## Troubleshooting

- If `/v1/health` fails, confirm Docker containers are running and port `8000` is available.
- If memories are not appearing immediately, give AMS a moment to promote them from working memory before searching again.
- If OpenAI requests fail, confirm `OPENAI_API_KEY` is set and outbound network access works.
- If AMS commands fail, confirm `AMS_URL` is `http://localhost:8000`.

## Slide checklist

- Problem statement
- Architecture diagram
- Setup commands
- Live demo: write, inspect, search
- Live demo: correct and re-query
- Next steps
