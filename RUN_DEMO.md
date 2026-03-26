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

## 5. Run the Python demo

Run:

```bash
python3 agent.py
```

Try this sequence:

1. Enter: `I prefer morning meetings and I love hiking.`
2. Enter: `Schedule a 30-minute sync next week.`

Expected behavior:

- The first message stores preferences in memory.
- The second message uses the stored morning-meeting preference in the assistant reply.

## 6. Run the notebook demo

Open:

`self_improving_assistant_workshop.ipynb`

Then:

1. Run the cells from top to bottom.
2. In the final demo section, run the sample messages or call `handle_user_message(...)` manually.

## 7. Common issues

If `curl` to `/v1/health` fails:

- Check that the `agent-memory-server` container is running.
- Check that Redis is running on port `6379`.

If the Python demo fails with OpenAI errors:

- Confirm `OPENAI_API_KEY` is set in `.env`.
- Confirm your machine has network access.

If the assistant does not use memory on the second turn:

- Make sure you used the same `USER_ID` for both turns.
- Make sure AMS is reachable at `http://localhost:8000`.
