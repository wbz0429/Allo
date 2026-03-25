import base64
import os
import base64
from pathlib import Path

import requests
from dotenv import load_dotenv
from PIL import Image


REQUEST_TIMEOUT = (10, 120)

_ROOT_DIR = Path(__file__).resolve().parents[4]
load_dotenv(_ROOT_DIR / ".env")
load_dotenv(_ROOT_DIR / "backend/.env", override=True)


def _save_base64_image(base64_image: str, output_file: str) -> str:
    with open(output_file, "wb") as f:
        f.write(base64.b64decode(base64_image))
    return f"Successfully generated image to {output_file}"


def _try_gemini_proxy(payload: dict, output_file: str) -> str | None:
    proxy_base_url = os.getenv("GEMINI_IMAGE_BASE_URL")
    proxy_api_key = os.getenv("GEMINI_IMAGE_API_KEY")
    if not (proxy_base_url and proxy_api_key):
        return None

    model_name = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    response = requests.post(
        f"{proxy_base_url.rstrip('/')}/v1beta/models/{model_name}:generateContent",
        headers={
            "Authorization": f"Bearer {proxy_api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    json_response = response.json()
    parts: list[dict] = json_response["candidates"][0]["content"]["parts"]
    image_parts = [part for part in parts if part.get("inlineData", False)]
    if len(image_parts) == 1:
        return _save_base64_image(image_parts[0]["inlineData"]["data"], output_file)
    raise Exception("Gemini proxy did not return image data")


def _try_gemini_official(payload: dict, output_file: str) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    if os.getenv("GEMINI_IMAGE_BASE_URL") or os.getenv("ARK_API_KEY"):
        return None

    response = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent",
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    json_response = response.json()
    parts: list[dict] = json_response["candidates"][0]["content"]["parts"]
    image_parts = [part for part in parts if part.get("inlineData", False)]
    if len(image_parts) == 1:
        return _save_base64_image(image_parts[0]["inlineData"]["data"], output_file)
    raise Exception("Official Gemini did not return image data")


def _try_seedream(prompt: str, output_file: str) -> str | None:
    ark_api_key = os.getenv("ARK_API_KEY")
    if not ark_api_key:
        return None

    response = requests.post(
        "https://ark.cn-beijing.volces.com/api/v3/images/generations",
        headers={
            "Authorization": f"Bearer {ark_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": os.getenv("SEEDREAM_MODEL", "doubao-seedream-5-0-260128"),
            "prompt": prompt,
            "response_format": "url",
            "size": os.getenv("SEEDREAM_SIZE", "2048x2048"),
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    json_response = response.json()
    image_url = json_response["data"][0]["url"]
    image_response = requests.get(image_url, timeout=REQUEST_TIMEOUT)
    image_response.raise_for_status()
    with open(output_file, "wb") as f:
        f.write(image_response.content)
    return f"Successfully generated image to {output_file}"


def validate_image(image_path: str) -> bool:
    """
    Validate if an image file can be opened and is not corrupted.

    Args:
        image_path: Path to the image file

    Returns:
        True if the image is valid and can be opened, False otherwise
    """
    try:
        with Image.open(image_path) as img:
            img.verify()  # Verify that it's a valid image
        # Re-open to check if it can be fully loaded (verify() may not catch all issues)
        with Image.open(image_path) as img:
            img.load()  # Force load the image data
        return True
    except Exception as e:
        print(f"Warning: Image '{image_path}' is invalid or corrupted: {e}")
        return False


def generate_image(
    prompt_file: str,
    reference_images: list[str],
    output_file: str,
    aspect_ratio: str = "16:9",
) -> str:
    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt = f.read()
    parts = []
    i = 0

    # Filter out invalid reference images
    valid_reference_images = []
    for ref_img in reference_images:
        if validate_image(ref_img):
            valid_reference_images.append(ref_img)
        else:
            print(f"Skipping invalid reference image: {ref_img}")

    if len(valid_reference_images) < len(reference_images):
        print(
            f"Note: {len(reference_images) - len(valid_reference_images)} reference image(s) were skipped due to validation failure."
        )

    for reference_image in valid_reference_images:
        i += 1
        with open(reference_image, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")
        parts.append(
            {
                "inlineData": {
                    "mimeType": "image/jpeg",
                    "data": image_b64,
                }
            }
        )

    payload = {
        "generationConfig": {"imageConfig": {"aspectRatio": aspect_ratio}},
        "contents": [{"role": "user", "parts": [*parts, {"text": prompt}]}],
    }

    errors: list[str] = []

    for provider_name, provider in [
        ("gemini_proxy", lambda: _try_gemini_proxy(payload, output_file)),
        ("gemini_official", lambda: _try_gemini_official(payload, output_file)),
        ("seedream", lambda: _try_seedream(prompt, output_file)),
    ]:
        try:
            result = provider()
            if result:
                return result
        except Exception as e:
            errors.append(f"{provider_name}: {e}")

    raise Exception(
        "All image providers failed: "
        + " | ".join(errors or ["no provider configured"])
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate images using Gemini API")
    parser.add_argument(
        "--prompt-file",
        required=True,
        help="Absolute path to JSON prompt file",
    )
    parser.add_argument(
        "--reference-images",
        nargs="*",
        default=[],
        help="Absolute paths to reference images (space-separated)",
    )
    parser.add_argument(
        "--output-file",
        required=True,
        help="Output path for generated image",
    )
    parser.add_argument(
        "--aspect-ratio",
        required=False,
        default="16:9",
        help="Aspect ratio of the generated image",
    )

    args = parser.parse_args()

    try:
        print(
            generate_image(
                args.prompt_file,
                args.reference_images,
                args.output_file,
                args.aspect_ratio,
            )
        )
    except Exception as e:
        print(f"Error while generating image: {e}")
