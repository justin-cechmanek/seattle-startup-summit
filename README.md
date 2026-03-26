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

4. Run the demo:

```bash
python3 agent.py
```
