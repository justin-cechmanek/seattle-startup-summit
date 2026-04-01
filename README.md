# Self-Improving AI Assistant Workshop

This repo demonstrates an AMS-native assistant flow:

- raw user messages are appended to AMS working memory
- AMS extracts and promotes useful long-term memories
- the assistant searches those memories to ground later responses
- stored memories can be inspected, patched, or deleted during the demo

## Prerequisites

- Python 3.10+
- Docker
- An `OPENAI_API_KEY`

## Setup

1. Copy the env file:

```bash
cp .env.example .env
```

2. Edit `.env` and set:

```bash
OPENAI_API_KEY=your_key_here
AMS_URL=http://localhost:8000
USER_ID=test_user
```

3. Start Redis and AMS:

```bash
docker compose up -d
```

This uses [compose.yaml](/Users/justin.cechmanek/Documents/demos/seattle-startup-summit/compose.yaml), enables AMS discrete memory extraction, and connects AMS to Redis over Docker's internal network.

4. Verify AMS:

```bash
curl http://localhost:8000/v1/health
```

5. Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Run the demo

For the scripted showcase:

```bash
python3 agent.py --showcase
```

The showcase demonstrates:

- before/after behavior on a scheduling question
- visible AMS working-memory writes
- long-term memory search

For interactive mode:

```bash
python3 agent.py
```

## Troubleshooting

- If `/v1/health` fails, confirm the Docker containers are running and port `8000` is available.
- If memories do not appear immediately, give AMS a moment to promote them from working memory before searching again.
- If OpenAI requests fail, confirm `OPENAI_API_KEY` is set and outbound network access works.
- If AMS commands fail, confirm `AMS_URL` is `http://localhost:8000`.
