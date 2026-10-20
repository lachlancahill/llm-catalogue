"""
Measure which models can actually see an image.

    uv run -m scripts.probe_images

A gateway that does not serve vision on a model either refuses (DeepInfra
answers a *405*, "does not accept image input") or answers as if no image were
sent. The two look different only when you try, so this sends one generated
image to each model in KEYS and logs what each said. A model card is not a
measurement (chat 0038).

The image is a green square with a red circle and the number 47. The question
hints at none of the three, so a model that names all three saw the picture.
The answer is judged by eye from the log.

Real requests: a fraction of a cent per model.
"""

import base64
import io
import logging

from anthropic import Anthropic
from PIL import Image, ImageDraw, ImageFont

from scripts.common import api_key, configure_logging, openai_compatible_client

logger = logging.getLogger(__name__)

# --- What to probe. Edit before running. ---------------------------------------
KEYS = ("together:deepseek-ai/DeepSeek-V4.1-Flash-1017",)
# -------------------------------------------------------------------------------

QUESTION = (
    "What is the background colour of this image, what shape is drawn on it, and what "
    "number is written on it? Answer in one short line. If you cannot see an image, "
    "say exactly: NO IMAGE."
)
# Room for a reasoning model to think and still answer in a few words.
MAX_OUTPUT_TOKENS = 8_000


def test_image() -> str:
    """A 512x512 PNG, base64: green ground, red circle, 47 in black."""
    image = Image.new("RGB", (512, 512), (40, 180, 60))
    draw = ImageDraw.Draw(image)
    draw.ellipse((96, 96, 416, 416), fill=(220, 30, 30))
    draw.text((256, 256), "47", fill=(0, 0, 0), font=ImageFont.load_default(size=160), anchor="mm")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def ask_anthropic(model: str, encoded: str) -> str:
    response = Anthropic(api_key=api_key("anthropic")).messages.create(
        model=model,
        max_tokens=MAX_OUTPUT_TOKENS,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": encoded},
                    },
                    {"type": "text", "text": QUESTION},
                ],
            }
        ],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def ask_openai_compatible(gateway: str, model: str, encoded: str) -> str:
    response = openai_compatible_client(gateway).chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}},
                    {"type": "text", "text": QUESTION},
                ],
            }
        ],
        max_completion_tokens=MAX_OUTPUT_TOKENS,
    )
    return response.choices[0].message.content or ""


def main() -> None:
    configure_logging()
    encoded = test_image()
    for key in KEYS:
        gateway, model = key.split(":", 1)
        try:
            if gateway == "anthropic":
                answer = ask_anthropic(model, encoded)
            else:
                answer = ask_openai_compatible(gateway, model, encoded)
        except Exception as exc:  # noqa: BLE001 - a refusal is the measurement
            logger.info("%-45s REJECTED - %s", key, str(exc)[:300])
            continue
        logger.info("%-45s %r", key, " ".join(answer.split())[:200])


if __name__ == "__main__":
    main()
