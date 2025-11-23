import pypdf
import uuid
import json


# -----------------------------
# 1. Extract text from PDF
# -----------------------------
def extract_pdf_text(file_path: str) -> str:
    """
    Extract plain text from a local PDF file.
    Uses pypdf's PdfReader.
    """
    try:
        reader = pypdf.PdfReader(file_path)
        text = []

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)

        return "\n".join(text)

    except Exception as e:
        return f"ERROR extracting PDF text: {e}"


# -----------------------------
# 2. Build quiz generation prompt
# -----------------------------
def generate_quiz_prompt(text: str, q_type: str, n: int) -> str:
    """
    Creates the prompt that will be sent to the Gemini client
    to generate quiz questions in JSON format.
    """

    return f"""
You are a quiz generator.

Your task:
Generate **{n} quiz questions** strictly from the provided text.

Quiz Type: {q_type}
Allowed Types: MCQ, Short, Mixed

================ RULES ================
1. Your ENTIRE output must be ONLY valid JSON.  
2. Do NOT write anything outside the JSON.  
   - No explanations  
   - No markdown  
   - No comments  
   - No backticks  
   - No introductory text  
3. JSON must be an ARRAY of objects.  
4. Each object must follow EXACTLY this structure:

For MCQ:
{{
  "id": "string_unique_id",
  "question": "string",
  "options": ["A", "B", "C", "D"],
  "answer": "string"
}}

For Short:
{{
  "id": "string_unique_id",
  "question": "string",
  "answer": "string"
}}

For Mixed:
- Some questions follow MCQ format
- Some follow Short format

5. IMPORTANT:
- `id` must be unique.
- Answers must ONLY come from the provided text.
- NO fields other than the ones defined.
- NO trailing commas.

================ INPUT TEXT ================
{text}

================ OUTPUT FORMAT ================
Return ONLY a JSON array, like:
[
  {{
    "id": "q1",
    "question": "...",
    "options": ["A","B","C","D"],
    "answer": "..."
  }}
]
"""
