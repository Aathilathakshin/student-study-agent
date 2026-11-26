import streamlit as st
from google import genai
from pypdf import PdfReader

# ---------------- PAGE SETUP ----------------
st.set_page_config(
    page_title="Student Study Assistant",
    page_icon="📚",
    layout="centered"
)

st.title("📚 Student Study Assistant AI Agent")
st.caption("Ask questions, learn concepts, and study from your notes.")

# ---------------- API KEY ----------------
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error(
        "GEMINI_API_KEY missing. Streamlit Cloud → Manage app → "
        "Settings → Secrets-la API key add pannunga."
    )
    st.stop()

client = genai.Client(api_key=api_key)

# ---------------- SESSION STATE ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "notes_text" not in st.session_state:
    st.session_state.notes_text = ""

if "notes_name" not in st.session_state:
    st.session_state.notes_name = ""

# ---------------- STUDY MODE ----------------
study_mode = st.selectbox(
    "Choose study mode",
    [
        "Normal answer",
        "Explain simply",
        "Give examples",
        "Quiz me"
    ]
)

# ---------------- NOTES UPLOAD ----------------
st.subheader("📄 Study notes")

uploaded_file = st.file_uploader(
    "Upload PDF or TXT notes",
    type=["pdf", "txt"]
)

if uploaded_file is not None:
    try:
        if uploaded_file.name.lower().endswith(".pdf"):
            pdf_reader = PdfReader(uploaded_file)
            extracted_text = "\n".join(
                page.extract_text() or ""
                for page in pdf_reader.pages
            )
        else:
            extracted_text = uploaded_file.getvalue().decode(
                "utf-8",
                errors="ignore"
            )

        if extracted_text.strip():
            st.session_state.notes_text = extracted_text
            st.session_state.notes_name = uploaded_file.name
            st.success(f"Notes loaded: {uploaded_file.name}")
        else:
            st.warning(
                "Text extract panna mudiyala. Scanned/image-only PDF-na "
                "OCR thevai padalaam."
            )

    except Exception as error:
        st.error("Notes file read panna mudiyala.")
        st.caption(str(error))

if st.session_state.notes_text:
    st.caption(f"Current notes: {st.session_state.notes_name}")

    if st.button("Remove uploaded notes"):
        st.session_state.notes_text = ""
        st.session_state.notes_name = ""
        st.rerun()

# ---------------- DISPLAY CHAT HISTORY ----------------
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ---------------- CHAT INPUT ----------------
question = st.chat_input("Type your study question here...")

if question:
    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    with st.chat_message("user"):
        st.markdown(question)

    # Previous messages only; current question is added below
    chat_history = []

    for message in st.session_state.messages[:-1]:
        role = "user" if message["role"] == "user" else "model"
        chat_history.append({
            "role": role,
            "parts": [{"text": message["content"]}]
        })

    # Study mode instructions
    mode_instructions = {
        "Normal answer": "Answer clearly and accurately.",
        "Explain simply": (
            "Explain in beginner-friendly language. "
            "Break difficult ideas into simple steps."
        ),
        "Give examples": (
            "Explain the topic and include a simple, relevant example."
        ),
        "Quiz me": (
            "Create a short quiz about the topic. Ask one question at a time. "
            "Wait for the user's answer before revealing the answer."
        )
    }

    # Include uploaded notes when available
    notes_context = ""

    if st.session_state.notes_text:
        notes_context = (
            "\n\nUse the following uploaded study notes as the main source. "
            "Answer based on these notes. If the notes do not contain the "
            "answer, say that the uploaded notes do not specify it.\n\n"
            f"NOTES:\n{st.session_state.notes_text}"
        )

    current_prompt = (
        f"Study mode: {study_mode}\n"
        f"Instructions: {mode_instructions[study_mode]}\n"
        f"{notes_context}\n\n"
        f"Student's question: {question}"
    )

    chat_history.append({
        "role": "user",
        "parts": [{"text": current_prompt}]
    })

    # ---------------- GEMINI RESPONSE ----------------
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=chat_history
                )

                answer = response.text

                if not answer:
                    answer = "I couldn't generate a response. Please try again."

                st.markdown(answer)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer
                })

            except Exception as error:
                error_message = str(error)

                if "503" in error_message or "UNAVAILABLE" in error_message:
                    st.warning(
                        "Gemini is busy right now. Please wait a little and try again."
                    )
                else:
                    st.error(
                        "Gemini API error. Please check your API key or model name."
                    )
                    st.caption(error_message)

# ---------------- CLEAR CHAT ----------------
if st.session_state.messages:
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()
