import streamlit as st
import time
import re
from google import genai
from google.genai import types

from prompts import SYSTEM_PROMPT, WELCOME_MESSAGE


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Vision Study Assistant",
    page_icon="🎓",
    layout="wide",
)


# ============================================================
# GEMINI MODEL OPTIONS
# ============================================================
# Stable model IDs listed in Google's Gemini API documentation.
# The user can change the model from the Streamlit sidebar.

MODEL_OPTIONS = {
    "Gemini 3.8 Flash": "gemini-3.8-flash",
    "Gemini 3.7 Flash": "gemini-3.7-flash",
    "Gemini 3.6 Flash": "gemini-3.6-flash",
    "Gemini 3.5 Flash": "gemini-3.5-flash",
    "Gemini 3.5 Flash-Lite": "gemini-3.5-flash-lite",
}

DEFAULT_MODEL_LABEL = "Gemini 3.8 Flash"


# ============================================================
# SESSION STATE
# ============================================================

def initialize_state():
    defaults = {
        "chat": None,
        "messages": [],
        "document_key": None,
        "document_loaded": False,
        "quiz_active": False,
        "quiz_question_number": 0,
        "quiz_correct": 0,
        "quiz_total": 0,
        "bonus_correct": 0,
        "bonus_total": 0,
        "last_quiz_question": "",
        "flashcards": [],
        "flashcard_index": 0,
        "flashcard_show_answer": False,
        "flashcards_studied": 0,
        "selected_model_label": DEFAULT_MODEL_LABEL,
        "current_model": MODEL_OPTIONS[DEFAULT_MODEL_LABEL],
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            if isinstance(value, list):
                st.session_state[key] = value.copy()
            else:
                st.session_state[key] = value


initialize_state()


# ============================================================
# GEMINI API CLIENT
# ============================================================

try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"].strip()
except Exception:
    GEMINI_API_KEY = ""


@st.cache_resource
def get_gemini_client(api_key):
    return genai.Client(api_key=api_key)


if GEMINI_API_KEY:
    gemini_client = get_gemini_client(GEMINI_API_KEY)
else:
    gemini_client = None


def create_chat(model_name=None):
    """Create a fresh Gemini chat using the selected model."""
    if gemini_client is None:
        return None

    selected_model = model_name or st.session_state.current_model

    return gemini_client.chats.create(
        model=selected_model,
        config={
            "system_instruction": SYSTEM_PROMPT
        },
    )


# ============================================================
# SIDEBAR / MODEL SELECTOR
# ============================================================

with st.sidebar:
    st.header("📚 Study Tools")

    st.subheader("🤖 AI Model")

    selected_model_label = st.selectbox(
        "Choose Gemini Model",
        options=list(MODEL_OPTIONS.keys()),
        index=list(MODEL_OPTIONS.keys()).index(
            st.session_state.selected_model_label
        ),
        key="model_selector",
        help="Changing the model starts a new AI conversation. Upload the material again if needed.",
    )

    selected_model = MODEL_OPTIONS[selected_model_label]

    # Change model only when the user actually selects a different one.
    if selected_model != st.session_state.current_model:
        st.session_state.selected_model_label = selected_model_label
        st.session_state.current_model = selected_model
        st.session_state.chat = create_chat(selected_model)
        st.session_state.messages = []
        st.session_state.document_loaded = False
        st.session_state.quiz_active = False
        st.session_state.quiz_question_number = 0
        st.session_state.quiz_correct = 0
        st.session_state.quiz_total = 0
        st.session_state.last_quiz_question = ""
        st.session_state.flashcards = []
        st.session_state.flashcard_index = 0
        st.session_state.flashcard_show_answer = False
        st.session_state.flashcards_studied = 0
        st.rerun()

    st.caption(f"Active model: `{st.session_state.current_model}`")

    st.divider()
    st.write("Upload your material and select a tool.")

    explain_button = st.button(
        "📖 Explain",
        use_container_width=True,
    )

    summarize_button = st.button(
        "📝 Summarize",
        use_container_width=True,
    )

    mcq_button = st.button(
        "❓ Generate MCQs",
        use_container_width=True,
    )

    quiz_button = st.button(
        "🎯 Quiz Me",
        use_container_width=True,
    )

    bonus_button = st.button(
        "🎁 Bonus Question",
        use_container_width=True,
    )

    flashcard_button = st.button(
        "🃏 Flashcards",
        use_container_width=True,
    )

    performance_button = st.button(
        "📈 Performance Dashboard",
        use_container_width=True,
    )

    score_button = st.button(
        "📊 Show Score",
        use_container_width=True,
    )

    st.divider()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat = create_chat()
        st.session_state.document_key = None
        st.session_state.document_loaded = False
        st.session_state.quiz_active = False
        st.session_state.quiz_question_number = 0
        st.session_state.quiz_correct = 0
        st.session_state.quiz_total = 0
        st.session_state.bonus_correct = 0
        st.session_state.bonus_total = 0
        st.session_state.last_quiz_question = ""
        st.session_state.flashcards = []
        st.session_state.flashcard_index = 0
        st.session_state.flashcard_show_answer = False
        st.session_state.flashcards_studied = 0
        st.rerun()


# ============================================================
# INITIALIZE CHAT AFTER MODEL SELECTION
# ============================================================

if not GEMINI_API_KEY:
    st.error(
        "🔑 GEMINI_API_KEY is missing. Add it to .streamlit/secrets.toml."
    )
    st.stop()

if st.session_state.chat is None:
    st.session_state.chat = create_chat()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def reset_quiz():
    st.session_state.quiz_active = False
    st.session_state.quiz_question_number = 0
    st.session_state.quiz_correct = 0
    st.session_state.quiz_total = 0
    st.session_state.bonus_correct = 0
    st.session_state.bonus_total = 0
    st.session_state.last_quiz_question = ""


def reset_everything():
    st.session_state.messages = []
    st.session_state.chat = create_chat()
    st.session_state.document_key = None
    st.session_state.document_loaded = False
    reset_quiz()


def friendly_api_error(error):
    """Convert common Gemini API errors into user-friendly messages."""
    error_message = str(error)
    lower_error = error_message.lower()

    if "429" in error_message or "resource_exhausted" in lower_error:
        return (
            "⚠️ **Gemini API quota/rate limit reached.**\n\n"
            "Please wait for the quota window to reset or use a project/tier "
            "with more available quota. Changing the model does not always "
            "bypass project-level limits."
        )

    if "503" in error_message or "unavailable" in lower_error:
        return (
            "⚠️ **Gemini is temporarily unavailable.**\n\n"
            "The selected model may be experiencing high demand. "
            "Try another available model from the sidebar or try again later."
        )

    if "400" in error_message or "invalid_argument" in lower_error:
        return (
            "⚠️ **Gemini rejected the request.**\n\n"
            "Check that the selected model is supported and that the uploaded "
            "file format is supported."
        )

    if "401" in error_message or "403" in error_message:
        return (
            "⚠️ **Gemini API authentication/permission problem.**\n\n"
            "Check your GEMINI_API_KEY and project permissions."
        )

    return f"⚠️ Gemini API error: {error_message}"


def send_to_gemini(prompt, max_retries=3):
    """Send a text request with limited retry handling."""
    if st.session_state.chat is None:
        return "⚠️ AI chat is not initialized. Check your API key."

    for attempt in range(max_retries):
        try:
            response = st.session_state.chat.send_message(prompt)
            return response.text

        except Exception as error:
            error_message = str(error)
            lower_error = error_message.lower()

            # Retry only temporary service-unavailable errors.
            if "503" in error_message or "unavailable" in lower_error:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue

            # Quota/rate-limit errors should not be repeatedly retried.
            if "429" in error_message or "resource_exhausted" in lower_error:
                return friendly_api_error(error)

            if "503" in error_message or "unavailable" in lower_error:
                return friendly_api_error(error)

            return friendly_api_error(error)

    return "⚠️ Gemini request could not be completed."


def send_document_to_gemini(file_part, document_prompt, max_retries=3):
    """Upload/read study material with limited retry handling."""
    if st.session_state.chat is None:
        return False, "⚠️ AI chat is not initialized. Check your API key."

    for attempt in range(max_retries):
        try:
            st.session_state.chat.send_message(
                [file_part, document_prompt]
            )
            return True, None

        except Exception as error:
            error_message = str(error)
            lower_error = error_message.lower()

            if "503" in error_message or "unavailable" in lower_error:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue

            return False, friendly_api_error(error)

    return False, "⚠️ Could not read the study material."


def add_assistant_message(answer):
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
        }
    )


def extract_quiz_result(text):
    """Extract Gemini's internal quiz result marker."""
    match = re.search(
        r"QUIZ_RESULT\s*:\s*(CORRECT|WRONG)",
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    return match.group(1).upper() == "CORRECT"


def clean_quiz_result(text):
    """Remove the internal result marker before showing the answer."""
    return re.sub(
        r"QUIZ_RESULT\s*:\s*(CORRECT|WRONG)\s*\n?",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()


def start_quiz():
    prompt = """
Start a quiz based ONLY on the uploaded study material.

Ask exactly ONE question.

Do not give the answer.

Number it as Question 1.

Wait for the student's answer.
"""

    answer = send_to_gemini(prompt)

    st.session_state.quiz_active = True
    st.session_state.quiz_question_number = 1
    st.session_state.quiz_correct = 0
    st.session_state.quiz_total = 0
    st.session_state.last_quiz_question = answer

    return answer


def evaluate_quiz_answer(student_answer):
    question_number = st.session_state.quiz_question_number

    prompt = f"""
We are conducting a quiz using ONLY the uploaded study material.

The current quiz question is:

{st.session_state.last_quiz_question}

The student's answer is:

{student_answer}

Evaluate the student's answer against the uploaded material.

Your response MUST follow this exact structure:

QUIZ_RESULT: CORRECT
or
QUIZ_RESULT: WRONG

Then:
1. Give a short explanation of the correct answer.
2. Ask exactly ONE new question from the uploaded study material.
3. Number the new question as Question {question_number + 1}.

Do not reveal the answer to the new question.

If the student's answer is substantially correct, mark it CORRECT.
"""

    answer = send_to_gemini(prompt)
    result = extract_quiz_result(answer)
    visible_answer = clean_quiz_result(answer)

    if result is not None:
        st.session_state.quiz_total += 1

        if result:
            st.session_state.quiz_correct += 1

    st.session_state.quiz_question_number += 1
    st.session_state.last_quiz_question = visible_answer

    return visible_answer, result


def generate_bonus_question():
    prompt = """
Create ONE bonus question from the uploaded study material.

Label it exactly as:

🎁 Bonus Question

Ask only the question.
Do not provide the answer.

The question must be based only on the uploaded material.
"""

    return send_to_gemini(prompt)


def generate_flashcards():
    prompt = """
Create exactly 8 flashcards from the uploaded study material.

Return ONLY valid JSON in this format:
[
  {"question": "Question 1", "answer": "Answer 1"},
  {"question": "Question 2", "answer": "Answer 2"}
]

Rules:
- Use ONLY information from the uploaded study material.
- Cover important concepts, definitions, examples and exam-relevant points.
- Keep questions clear and answers concise.
- Do not add markdown or extra text outside the JSON.
"""
    answer = send_to_gemini(prompt)

    try:
        cleaned = answer.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        import json
        cards = json.loads(cleaned)

        if not isinstance(cards, list):
            raise ValueError("Flashcard response is not a list.")

        valid_cards = [
            card for card in cards
            if isinstance(card, dict)
            and "question" in card
            and "answer" in card
        ]

        return valid_cards
    except Exception:
        return []


def show_flashcards():
    if not st.session_state.flashcards:
        st.info("Click 🃏 Flashcards to generate flashcards from your study material.")
        return

    cards = st.session_state.flashcards
    index = st.session_state.flashcard_index
    card = cards[index]

    st.subheader("🃏 Flashcards")
    st.caption(f"Card {index + 1} of {len(cards)}")

    st.markdown("### ❓ Question")
    st.info(card["question"])

    if st.session_state.flashcard_show_answer:
        st.markdown("### 💡 Answer")
        st.success(card["answer"])
    else:
        if st.button("👀 Show Answer", key="show_flashcard_answer"):
            st.session_state.flashcard_show_answer = True
            st.rerun()

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("⬅️ Previous", use_container_width=True, disabled=index == 0):
            st.session_state.flashcard_index -= 1
            st.session_state.flashcard_show_answer = False
            st.rerun()

    with col2:
        if st.button(
            "➡️ Next",
            use_container_width=True,
            disabled=index >= len(cards) - 1,
        ):
            st.session_state.flashcard_index += 1
            st.session_state.flashcard_show_answer = False
            st.session_state.flashcards_studied = max(
                st.session_state.flashcards_studied,
                st.session_state.flashcard_index + 1,
            )
            st.rerun()

    with col3:
        if st.button("🔄 Restart", use_container_width=True):
            st.session_state.flashcard_index = 0
            st.session_state.flashcard_show_answer = False
            st.session_state.flashcards_studied = 0
            st.rerun()


def show_performance_dashboard():
    quiz_total = st.session_state.quiz_total
    quiz_correct = st.session_state.quiz_correct
    quiz_wrong = max(quiz_total - quiz_correct, 0)

    accuracy = (quiz_correct / quiz_total * 100) if quiz_total else 0
    flashcards_studied = st.session_state.flashcards_studied

    st.subheader("📈 Performance Dashboard")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Questions Attempted", quiz_total)
    c2.metric("Correct Answers", quiz_correct)
    c3.metric("Wrong Answers", quiz_wrong)
    c4.metric("Accuracy", f"{accuracy:.0f}%")

    st.divider()

    c5, c6 = st.columns(2)
    c5.metric("🃏 Flashcards Studied", flashcards_studied)
    c6.metric("🎯 Quiz Questions", quiz_total)

    if quiz_total > 0:
        st.markdown("### Quiz Performance")
        import pandas as pd
        chart_data = pd.DataFrame(
            {
                "Result": ["Correct", "Wrong"],
                "Questions": [quiz_correct, quiz_wrong],
            }
        ).set_index("Result")
        st.bar_chart(chart_data)

        st.progress(
            min(accuracy / 100, 1.0),
            text=f"Quiz Accuracy: {accuracy:.0f}%"
        )
    else:
        st.info("Complete some quiz questions to see your performance chart.")

    if st.session_state.flashcards:
        st.markdown("### Flashcard Progress")
        total_cards = len(st.session_state.flashcards)
        progress = (
            min(flashcards_studied / total_cards, 1.0)
            if total_cards
            else 0
        )
        st.progress(
            progress,
            text=f"Flashcards studied: {flashcards_studied}/{total_cards}"
        )


def show_score():
    total = st.session_state.quiz_total
    correct = st.session_state.quiz_correct

    percentage = (correct / total) * 100 if total > 0 else 0

    st.sidebar.divider()
    st.sidebar.subheader("🎯 Quiz Score")
    st.sidebar.metric("Score", f"{correct}/{total}")
    st.sidebar.metric("Percentage", f"{percentage:.0f}%")

    if st.session_state.quiz_active:
        st.sidebar.caption(
            f"Question {st.session_state.quiz_question_number}"
        )


# ============================================================
# MAIN PAGE
# ============================================================

st.title("🎓 AI Vision Study Assistant")
st.write("Upload your study material and use AI to understand it.")

if WELCOME_MESSAGE:
    st.info(WELCOME_MESSAGE)


# ============================================================
# FILE UPLOAD
# ============================================================

uploaded_file = st.file_uploader(
    "📚 Upload your study material",
    type=[
        "png",
        "jpg",
        "jpeg",
        "webp",
        "pdf",
    ],
)


# ============================================================
# LOAD DOCUMENT ONLY ONCE
# ============================================================

if uploaded_file:
    current_document_key = (
        f"{uploaded_file.name}_"
        f"{uploaded_file.size}_"
        f"{uploaded_file.type}"
    )

    # New document detected.
    if current_document_key != st.session_state.document_key:
        st.session_state.chat = create_chat()
        st.session_state.messages = []
        st.session_state.document_key = current_document_key
        st.session_state.document_loaded = False
        reset_quiz()
        st.session_state.flashcards = []
        st.session_state.flashcard_index = 0
        st.session_state.flashcard_show_answer = False
        st.session_state.flashcards_studied = 0

    # Send document to Gemini only once per selected model/document.
    if not st.session_state.document_loaded:
        with st.spinner("📚 Reading your study material..."):
            file_bytes = uploaded_file.getvalue()

            file_part = types.Part.from_bytes(
                data=file_bytes,
                mime_type=uploaded_file.type,
            )

            document_prompt = """
Read and understand the uploaded study material.

Use this material as the main context for future
questions in this conversation.

Remember the important concepts, definitions,
examples, tables and questions contained in it.

Do not invent information that is not supported
by the uploaded material.
"""

            success, error_message = send_document_to_gemini(
                file_part,
                document_prompt,
            )

            if success:
                st.session_state.document_loaded = True
                st.success("✅ Study material loaded successfully.")
            else:
                st.error(error_message)


# ============================================================
# DISPLAY CHAT HISTORY
# ============================================================

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# ============================================================
# SCORE
# ============================================================

show_score()


# ============================================================
# EXPLAIN
# ============================================================

if explain_button:
    if not uploaded_file:
        st.warning("Please upload a study material first.")
    elif not st.session_state.document_loaded:
        st.warning("The study material is still loading.")
    else:
        prompt = """
Explain the uploaded study material in simple
college-student language.

Cover:

1. Main concepts
2. Important definitions
3. Important points
4. Examples
5. Exam-important information

Use only the uploaded study material.
"""

        with st.chat_message("assistant"):
            with st.spinner("📖 Explaining..."):
                answer = send_to_gemini(prompt)
                st.markdown(answer)
                add_assistant_message(answer)


# ============================================================
# SUMMARIZE
# ============================================================

if summarize_button:
    if not uploaded_file:
        st.warning("Please upload a study material first.")
    elif not st.session_state.document_loaded:
        st.warning("The study material is still loading.")
    else:
        prompt = """
Summarize the uploaded study material.

Give:

- Key concepts
- Important definitions
- Main points
- Short exam revision notes

Keep the summary clear and concise.

Use only information from the uploaded material.
"""

        with st.chat_message("assistant"):
            with st.spinner("📝 Creating summary..."):
                answer = send_to_gemini(prompt)
                st.markdown(answer)
                add_assistant_message(answer)


# ============================================================
# MCQs
# ============================================================

if mcq_button:
    if not uploaded_file:
        st.warning("Please upload a study material first.")
    elif not st.session_state.document_loaded:
        st.warning("The study material is still loading.")
    else:
        prompt = """
Create 5 multiple-choice questions from the
uploaded study material.

For every question provide:

1. Question
2. Four options: A, B, C, D
3. Correct answer
4. Short explanation

Questions must be based only on the uploaded material.
"""

        with st.chat_message("assistant"):
            with st.spinner("❓ Generating MCQs..."):
                answer = send_to_gemini(prompt)
                st.markdown(answer)
                add_assistant_message(answer)


# ============================================================
# START QUIZ
# ============================================================

if quiz_button:
    if not uploaded_file:
        st.warning("Please upload a study material first.")
    elif not st.session_state.document_loaded:
        st.warning("The study material is still loading.")
    else:
        with st.chat_message("assistant"):
            with st.spinner("🎯 Preparing your quiz..."):
                answer = start_quiz()
                st.markdown(answer)
                add_assistant_message(answer)


# ============================================================
# BONUS QUESTION
# ============================================================

if bonus_button:
    if not uploaded_file:
        st.warning("Please upload a study material first.")
    elif not st.session_state.document_loaded:
        st.warning("The study material is still loading.")
    else:
        with st.chat_message("assistant"):
            with st.spinner("🎁 Preparing bonus question..."):
                answer = generate_bonus_question()
                st.markdown(answer)
                add_assistant_message(answer)


# ============================================================
# FLASHCARDS
# ============================================================

if flashcard_button:
    if not uploaded_file:
        st.warning("Please upload a study material first.")
    elif not st.session_state.document_loaded:
        st.warning("The study material is still loading.")
    else:
        with st.spinner("🃏 Generating flashcards..."):
            cards = generate_flashcards()

        if cards:
            st.session_state.flashcards = cards
            st.session_state.flashcard_index = 0
            st.session_state.flashcard_show_answer = False
            st.session_state.flashcards_studied = 1
            st.success(f"✅ {len(cards)} flashcards generated.")
        else:
            st.error("⚠️ Could not generate flashcards. Please try again.")


# Always display the current flashcard set when available.
if st.session_state.flashcards:
    show_flashcards()


# ============================================================
# PERFORMANCE DASHBOARD
# ============================================================

if performance_button:
    show_performance_dashboard()


# ============================================================
# SHOW SCORE BUTTON
# ============================================================

if score_button:
    percentage = (
        st.session_state.quiz_correct / st.session_state.quiz_total * 100
        if st.session_state.quiz_total > 0
        else 0
    )

    st.sidebar.success(
        f"🎯 Score: {st.session_state.quiz_correct}/"
        f"{st.session_state.quiz_total} ({percentage:.0f}%)"
    )


# ============================================================
# NORMAL QUESTION / QUIZ ANSWER
# ============================================================

question = st.chat_input(
    "Answer the quiz question or ask about your study material..."
)

if question:
    with st.chat_message("user"):
        st.markdown(question)

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question,
        }
    )

    with st.chat_message("assistant"):
        with st.spinner(
            "🧠 Checking your answer..."
            if st.session_state.quiz_active
            else "🔍 Thinking about your study material..."
        ):
            if st.session_state.quiz_active:
                answer, result = evaluate_quiz_answer(question)

                if result is True:
                    st.success("✅ Correct!")
                elif result is False:
                    st.error("❌ Incorrect.")

                st.markdown(answer)
                add_assistant_message(answer)
            else:
                answer = send_to_gemini(question)
                st.markdown(answer)
                add_assistant_message(answer)

    st.rerun()
