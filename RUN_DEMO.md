# Run The Demo

## Prerequisites

- Python 3.10+
- Docker
- An `OPENAI_API_KEY`

## 1. Install Python dependencies

From the repo root, run:

```bash
pip install -r requirements.txt
```

## 2. Create your env file

Copy the example file:

```bash
cp .env.example .env
```

Edit `.env` and set:

```bash
OPENAI_API_KEY=your_key_here
AMS_URL=http://localhost:8000
USER_ID=test_user
```

## 3. Start Redis and Agent Memory Server

Run:

```bash
docker compose up -d
```

This uses [compose.yaml](/Users/justin.cechmanek/Documents/demos/seattle-startup-summit/compose.yaml), reads `OPENAI_API_KEY` from `.env`, and connects AMS to Redis over Docker's internal network.

## 4. Verify AMS is up

Run:

```bash
curl http://localhost:8000/v1/health
```

You should get a small JSON response.

## 5. Run the scripted AMS showcase

Run:

```bash
python3 agent.py --showcase
```

The showcase proves four things in sequence:

- Before/after: the assistant answers a scheduling question before any memory exists, then answers again after AMS extracts memories from the user's profile message.
- Observability: each turn prints the working-memory payload, the AMS working-memory response, retrieved memories, and prompt context.
- Correction: the demo patches a stored long-term memory by ID.
- Isolation: `alice` and `bob` get separate memory sets and different scheduling recommendations.

The richer profile used in the showcase is in [demo_data/onboarding.txt](/Users/justin.cechmanek/Documents/demos/seattle-startup-summit/demo_data/onboarding.txt).

## 6. Run the interactive AMS demo

Run:

```bash
python3 agent.py
```

Useful commands:

- `/help`
- `/showcase`
- `/debug on`
- `/working`
- `/list`
- `/search Summit Copilot vegetarian Seattle`
- `/correct <memory_id> User prefers afternoon meetings.`
- `/user bob`
- `/clear`

Any non-command input goes through the assistant pipeline and prints the AMS trace by default.

## 7. Suggested live flow

If you want a short manual walkthrough instead of the scripted showcase:

1. Ask: `Can you schedule a 30-minute sync next week?`
2. Add a richer profile: `I'm a product engineer based in Seattle. I prefer morning meetings, I'm vegetarian, I'm working on Summit Copilot, and I love hiking and espresso.`
3. Run `/working`, then `/list` or `/search Summit Copilot vegetarian Seattle`.
4. Ask the scheduling question again.
5. Copy a memory ID from `/list` and correct it with `/correct <memory_id> User prefers afternoon meetings.`
6. Ask the scheduling question again.
7. Switch users with `/user bob` and add a different profile to show isolation.

## 8. Notebook demo

Open:

`self_improving_assistant_workshop.ipynb`

The notebook now mirrors the same AMS-native flow as the CLI, but the default showcase path is still [agent.py](/Users/justin.cechmanek/Documents/demos/seattle-startup-summit/agent.py).

## 9. Common issues

If `curl` to `/v1/health` fails:

- Check that the `agent-memory-server` container is running.
- Check that Redis is running on port `6379`.

If the Python demo fails with OpenAI errors:

- Confirm `OPENAI_API_KEY` is set in `.env`.
- Confirm your machine has network access.

If AMS commands fail:

- Confirm `AMS_URL` points to `http://localhost:8000`.
- Run `/health` from the CLI to verify the server is reachable.
