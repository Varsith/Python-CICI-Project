# coding: utf-8

import os
import re
from pathlib import Path

import oci


APP_FILE = Path("app/main.py")
TEST_DIR = Path("tests")
OUTPUT_TEST_FILE = TEST_DIR / "test_ai_generated.py"

CONFIG_PROFILE = os.getenv("OCI_CONFIG_PROFILE", "DEFAULT")
OCI_CONFIG_FILE = os.getenv("OCI_CONFIG_FILE")

COMPARTMENT_ID = os.getenv("OCI_COMPARTMENT_ID")
ENDPOINT = os.getenv("OCI_GENAI_ENDPOINT")
MODEL_ID = os.getenv("OCI_CHAT_MODEL_ID")


def validate_environment():
    missing = []

    if not OCI_CONFIG_FILE:
        missing.append("OCI_CONFIG_FILE")

    if not COMPARTMENT_ID:
        missing.append("OCI_COMPARTMENT_ID")

    if not ENDPOINT:
        missing.append("OCI_GENAI_ENDPOINT")

    if not MODEL_ID:
        missing.append("OCI_CHAT_MODEL_ID")

    if missing:
        raise EnvironmentError(
            "Missing required environment variables: " + ", ".join(missing)
        )

    if not APP_FILE.exists():
        raise FileNotFoundError(f"Application file not found: {APP_FILE}")


def read_application_code():
    return APP_FILE.read_text(encoding="utf-8")


def build_test_generation_prompt(source_code):
    return f"""
You are a senior Python QA automation engineer.

Generate pytest test cases for the Python source code below.

Strict output rules:
1. Output only Python code.
2. Do not include markdown.
3. Do not include ```python code fences.
4. Do not explain anything.
5. Use pytest.
6. Import the application exactly as: from app import main
7. Test normal cases.
8. Test edge cases.
9. Test exception cases wherever applicable.
10. The generated file must run using: pytest tests/
11. Do not use external services.
12. Do not generate destructive tests.
13. Do not use os.remove, shutil.rmtree, subprocess, socket, requests, eval, or exec.
14. Keep tests deterministic.

Python source code:
{source_code}
"""


def call_oci_genai(prompt):
    config = oci.config.from_file(OCI_CONFIG_FILE, CONFIG_PROFILE)

    client = oci.generative_ai_inference.GenerativeAiInferenceClient(
        config=config,
        service_endpoint=ENDPOINT,
        retry_strategy=oci.retry.NoneRetryStrategy(),
        timeout=(10, 240)
    )

    content = oci.generative_ai_inference.models.TextContent()
    content.text = prompt

    message = oci.generative_ai_inference.models.Message()
    message.role = "USER"
    message.content = [content]

    chat_request = oci.generative_ai_inference.models.GenericChatRequest()
    chat_request.api_format = (
        oci.generative_ai_inference.models.BaseChatRequest.API_FORMAT_GENERIC
    )
    chat_request.messages = [message]
    chat_request.max_tokens = 6000
    chat_request.temperature = 0.2
    chat_request.frequency_penalty = 0
    chat_request.presence_penalty = 0
    chat_request.top_p = 0.95
    chat_request.top_k = 1

    chat_detail = oci.generative_ai_inference.models.ChatDetails()
    chat_detail.serving_mode = (
        oci.generative_ai_inference.models.OnDemandServingMode(
            model_id=MODEL_ID
        )
    )
    chat_detail.chat_request = chat_request
    chat_detail.compartment_id = COMPARTMENT_ID

    response = client.chat(chat_detail)

    return extract_text_from_response(response)


def extract_text_from_response(response):
    try:
        choices = response.data.chat_response.choices
        if choices and choices[0].message.content:
            return choices[0].message.content[0].text
    except Exception:
        pass

    try:
        return response.data.chat_response.text
    except Exception:
        pass

    raise ValueError(f"Unable to extract generated text from OCI response: {response}")


def clean_generated_code(ai_output):
    code = ai_output.strip()

    code = re.sub(r"^```python", "", code)
    code = re.sub(r"^```", "", code)
    code = re.sub(r"```$", "", code)

    return code.strip() + "\n"


def validate_generated_test_code(code):
    dangerous_patterns = [
        "os.remove",
        "shutil.rmtree",
        "subprocess",
        "socket",
        "requests.",
        "open('/",
        'open("/',
        "rm -rf",
        "eval(",
        "exec("
    ]

    for pattern in dangerous_patterns:
        if pattern in code:
            raise ValueError(
                f"Generated test code contains unsafe pattern: {pattern}"
            )

    if "def test_" not in code:
        raise ValueError("Generated code does not contain pytest test functions.")

    if "from app import main" not in code:
        raise ValueError(
            "Generated code must import application using: from app import main"
        )


def write_test_file(code):
    TEST_DIR.mkdir(exist_ok=True)
    OUTPUT_TEST_FILE.write_text(code, encoding="utf-8")
    print(f"AI-generated pytest file created: {OUTPUT_TEST_FILE}")


def main():
    validate_environment()

    source_code = read_application_code()
    prompt = build_test_generation_prompt(source_code)

    print("Calling OCI Generative AI to generate pytest test cases...")

    ai_output = call_oci_genai(prompt)

    generated_code = clean_generated_code(ai_output)
    validate_generated_test_code(generated_code)

    write_test_file(generated_code)

    print("AI test generation completed successfully.")


if __name__ == "__main__":
    main()
