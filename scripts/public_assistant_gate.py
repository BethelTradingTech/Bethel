"""Static regression checks for the additive public website assistant."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, *needles: str) -> None:
    data = text(path)
    missing = [needle for needle in needles if needle not in data]
    if missing:
        raise SystemExit(f"PUBLIC ASSISTANT GATE FAIL {path}: missing {missing}")


require(
    "api/public_assistant.py",
    'router = APIRouter(prefix="/public/assistant"',
    'os.getenv("OPENAI_API_KEY"',
    'https://api.openai.com/v1/responses',
    'PUBLIC_SUPPORT_EMAIL',
    'info@betheltradingtechnologies.com',
    'BETHEL_ASSISTANT_MAX_REQUESTS_PER_WINDOW',
    'BETHEL_ASSISTANT_MAX_MESSAGE_CHARS',
    'BETHEL_ASSISTANT_MAX_OUTPUT_TOKENS',
    'gpt-5.6-luna',
    'Never provide personalized financial, investment or trading advice',
)
require(
    "render_app.py",
    'PUBLIC_ASSISTANT_PATH = "/public/assistant/chat"',
    'app.include_router(public_assistant_router)',
)
require(
    "frontend/index.html",
    'css/chat-assistant.css?v=1',
    'js/chat-assistant.js?v=1',
)
require(
    "frontend/js/chat-assistant.js",
    'https://api.betheltradingtechnologies.com/public/assistant/chat',
    'mailto:',
    'info@betheltradingtechnologies.com',
)

# The browser bundle must never contain the OpenAI secret or call OpenAI directly.
frontend = text("frontend/js/chat-assistant.js") + text("frontend/index.html")
if "OPENAI_API_KEY" in frontend or "api.openai.com" in frontend:
    raise SystemExit("PUBLIC ASSISTANT GATE FAIL: OpenAI credentials/API must remain server-side")

print("PASS: additive public AI assistant safeguards")
