import os
import pathlib
import uuid
import json
import datetime
import streamlit as st
from openai import OpenAI
from tools import extract_pdf_text, generate_quiz_prompt

 
# Read secret from Streamlit
gemini_api_key = st.secrets["GEMINI_API_KEY"]

if not gemini_api_key:
    st.error("GEMINI_API_KEY missing")
    st.stop()

# Correct Gemini OpenAI-Compatible client
client = OpenAI(
    api_key=gemini_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

st.set_page_config(layout="wide")
st.title("📘 Study Notes Summarizer & Quiz Generator")


# ------------------ UPLOAD PDF ------------------

uploaded_file = st.file_uploader("Upload PDF", type="pdf")

if uploaded_file:
    st.success("PDF uploaded successfully!")

    uploads_dir = pathlib.Path("uploads")
    uploads_dir.mkdir(exist_ok=True)

    file_id = uuid.uuid4().hex
    file_path = uploads_dir / f"{file_id}.pdf"

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.session_state["current_pdf_path"] = str(file_path)

    # ------------------ SUMMARIZING ------------------

    if st.button("Summarize"):
        with st.spinner("Summarizing document..."):
            try:
                full_text = extract_pdf_text(str(file_path))
                st.session_state["full_text"] = full_text

                summary_prompt = "Summarize this text:\n\n" + full_text[:4000]

                response = client.chat.completions.create(
                    model="gemini-2.0-flash",
                    messages=[
                        {"role": "user", "content": summary_prompt}
                    ]
                )

                summary_text = response.choices[0].message.content

                st.subheader("Summary")
                st.markdown(summary_text)

                # Save summary
                memory_dir = pathlib.Path("memory")
                memory_dir.mkdir(exist_ok=True)
                file_json = memory_dir / "summaries.json"

                saved = []
                if file_json.exists():
                    saved = json.load(open(file_json))

                saved.append({
                    "id": file_id,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "summary": summary_text,
                    "pdf_name": uploaded_file.name
                })

                json.dump(saved, open(file_json, "w"), indent=4)

                st.session_state["current_summary"] = summary_text
                st.success("Summary saved!")

            except Exception as e:
                st.error(f"An error occurred: {e}")


# ------------------ QUIZ GENERATOR ------------------

# ------------------ QUIZ GENERATOR ------------------

import re

def clean_json(raw: str) -> str:
    """Cleans model output to extract valid JSON only."""
    if not raw:
        return raw

    s = raw.strip()

    # Remove ```, ```json fences
    s = re.sub(r"```(?:json)?", "", s, flags=re.IGNORECASE)
    s = s.replace("```", "").strip()

    # Extract everything between first { or [ and last } or ]
    start = min(
        [i for i in [s.find("{"), s.find("[")] if i != -1],
        default=-1
    )
    end = max(s.rfind("}"), s.rfind("]"))

    if start != -1 and end != -1 and end > start:
        s = s[start : end + 1]

    # Replace fancy quotes with normal quotes
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")

    return s


if "full_text" in st.session_state:
    st.markdown("---")
    st.subheader("Generate Quiz")

    quiz_type = st.selectbox("Quiz type", ["MCQ", "Short", "Mixed"])
    num_questions = st.number_input("# Questions", min_value=3, max_value=50, value=5)

    if st.button("Create Quiz"):
        with st.spinner("Generating quiz..."):
            try:
                quiz_prompt = generate_quiz_prompt(
                    st.session_state["full_text"], quiz_type, num_questions
                )

                quiz_response = client.chat.completions.create(
                    model="gemini-2.0-flash",
                    messages=[{"role": "user", "content": quiz_prompt}]
                )

                raw_quiz = quiz_response.choices[0].message.content

                # ---- FIX: Clean the output BEFORE parsing ----
                cleaned = clean_json(raw_quiz)

                try:
                    quiz_questions = json.loads(cleaned)
                except Exception:
                    quiz_questions = []

                if quiz_questions:
                    st.subheader("Quiz")
                    for i, q in enumerate(quiz_questions):
                        st.markdown(f"### {i+1}. {q['question']}")
                        if "options" in q:
                            for idx, option in enumerate(q["options"]):
                                st.markdown(f"- {chr(65+idx)}. {option}")
                        st.markdown(f"**Answer:** {q['answer']}")

                    st.session_state["current_quiz"] = quiz_questions
                    st.success("Quiz created!")
                else:
                    st.warning("Invalid quiz JSON returned.")
                    st.text_area("Raw Model Output", raw_quiz, height=200)

            except Exception as e:
                st.error(f"An error occurred: {e}")

# ------------------ DOWNLOAD ------------------

st.markdown("---")

if "current_summary" in st.session_state:
    st.download_button(
        "Download Summary (Markdown)",
        data=st.session_state["current_summary"],
        file_name="summary.md",
        mime="text/markdown"
    )

if "current_quiz" in st.session_state:
    st.download_button(
        "Download Quiz (JSON)",
        data=json.dumps(st.session_state["current_quiz"], indent=4),
        file_name="quiz.json",
        mime="application/json"
    )
