"""
Text preprocessor: clean raw extracted text before chunking.

Handles common extraction artifacts:
- Multiple consecutive blank lines
- Leading/trailing whitespace per line
- Non-breaking spaces and unusual unicode whitespace
"""
import re
import unicodedata


def clean_text(text: str) -> str:
    """
    Normalize and clean extracted document text.

    Steps:
    1. Normalize unicode (NFKC) to collapse ligatures, special spaces, etc.
    2. Replace non-breaking spaces, zero-width chars with standard space.
    3. Strip leading/trailing whitespace from each line.
    4. Collapse runs of 3+ blank lines into a single blank line.
    5. Strip overall leading/trailing whitespace.
    """
    # 1. Unicode normalization
    text = unicodedata.normalize("NFKC", text)

    # 2. Replace zero-width and non-breaking space characters
    text = re.sub(r"[\u00a0\u200b\u200c\u200d\ufeff]", " ", text)

    # 3. Strip each line
    lines = [line.strip() for line in text.splitlines()]

    # 4. Collapse 3+ consecutive blank lines → 1 blank line
    cleaned_lines: list[str] = []
    blank_count = 0
    for line in lines:
        if line == "":
            blank_count += 1
            if blank_count <= 1:
                cleaned_lines.append(line)
        else:
            blank_count = 0
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()
