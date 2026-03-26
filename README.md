# Self-Improving AI Assistant Workshop

## Quick start

1. Clone this repo.
2. Copy `.env.example` to `.env` and add your `OPENAI_API_KEY`.
3. Start Redis and Agent Memory Server (AMS):

```bash
docker compose up -d

# verify AMS
curl http://localhost:8000/v1/health
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Run the AMS showcase:

```bash
python3 agent.py --showcase
```

This scripted walkthrough demonstrates:
- AMS-managed extraction from working memory
- visible working-memory writes and long-term searches
- live memory editing with `PATCH`
- multi-user isolation with `alice` and `bob`

## Interactive mode

Run:

```bash
python3 agent.py
```

Useful commands:
- `/showcase`
- `/working`
- `/list`
- `/search <query>`
- `/correct <memory_id> <new text>`
- `/user <user_id>`
- `/clear`

The CLI prints the working-memory payload, the AMS working-memory response, retrieved long-term memories, and the prompt memory context so AMS is observable during the demo.
