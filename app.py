import streamlit as st
from google import genai
from pypdf import PdfReader
from datetime import date

# ---------------- PAGE SETUP ----------------
st.set_page_config(
    page_title="Student Study Assistant",
    page_icon="📚",
    layout="centered"
)

st.title("📚 Student Study Assistant AI Agent")
st.caption("Ask questions, learn concepts, and plan your study sessions.")

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
MODEL_NAME = "gemini-3.8-flash"

# ---------------- SESSION STATE ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "notes_text" not in st.session_state:
    st.session_state.notes_text = ""

if "notes_name" not in st.session_state:
    st.session_state.notes_name = ""

if "notes_summary" not in st.session_state:
    st.session_state.notes_summary = ""

if "study_plan" not in st.session_state:
    st.session_state.study_plan = ""

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
        "Ask one quiz question at a time. Wait for the student's answer "
        "before revealing the answer."
    )
}

# ---------------- SUBJECT ----------------
subject_name = st.text_input(
    "Subject name",
    placeholder="Example: Operating Systems"
)

# ---------------- NOTES UPLOAD ----------------
st.subheader("📄 Study Notes")

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
            if (
                uploaded_file.name != st.session_state.notes_name
                or extracted_text != st.session_state.notes_text
            ):
                st.session_state.notes_text = extracted_text
                st.session_state.notes_name = uploaded_file.name
                st.session_state.notes_summary = ""

            st.success(f"Notes loaded: {uploaded_file.name}")
        else:
            st.warning(
                "PDF-la extract panna text kidaikkala. "
                "Scanned/image-only PDF-na OCR thevai padalaam."
            )

    except Exception as error:
        st.error("Notes file read panna mudiyala.")
        st.caption(str(error))

if st.session_state.notes_text:
    st.caption(f"Current notes: {st.session_state.notes_name}")

    if st.button("Remove uploaded notes"):
        st.session_state.notes_text = ""
        st.session_state.notes_name = ""
        st.session_state.notes_summary = ""
        st.rerun()

# ---------------- NOTES SUMMARY ----------------
if st.session_state.notes_text:
    if st.button("Summarize uploaded notes"):
        with st.spinner("Preparing your summary..."):
            try:
                summary_response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=(
                        f"Subject: {subject_name or 'Study notes'}\n\n"
                        "Summarize these notes in simple language. "
                        "Use headings and bullet points. Keep important "
                        "terms and facts from the notes. Do not add "
                        "unsupported details.\n\n"
                        f"NOTES:\n{st.session_state.notes_text}"
                    )
                )

                st.session_state.notes_summary = (
                    summary_response.text
                    or "Summary couldn't be generated."
                )

            except Exception as error:
                if "503" in str(error) or "UNAVAILABLE" in str(error):
                    st.warning(
                        "Gemini is busy right now. Please wait and try again."
                    )
                else:
                    st.error("Summary generate panna mudiyala.")
                    st.caption(str(error))

    if st.session_state.notes_summary:
        st.subheader("📝 Notes Summary")
        st.markdown(st.session_state.notes_summary)

        st.download_button(
            label="Download summary as TXT",
            data=st.session_state.notes_summary,
            file_name="study_notes_summary.txt",
            mime="text/plain"
        )

# ---------------- STUDY PLANNER ----------------
st.divider()
st.subheader("🗓️ Study Planner")

with st.form("study_planner_form"):
    planner_subject = st.text_input(
        "Planner subject",
        placeholder="Example: Operating Systems"
    )

    exam_date = st.date_input(
        "Exam date",
        min_value=date.today()
    )

    daily_hours = st.number_input(
        "Available study time per day (hours)",
        min_value=0.5,
        max_value=12.0,
        value=2.0,
        step=0.5
    )

    topics = st.text_area(
        "Topics to study",
        placeholder="Enter topics, one per line"
    )

    create_plan = st.form_submit_button("Create study plan")

if create_plan:
    if not planner_subject.strip() or not topics.strip():
        st.warning("Subject and topics enter pannunga.")
    elif exam_date < date.today():
        st.warning("Future exam date select pannunga.")
    else:
        with st.spinner("Creating your study plan..."):
            try:
                plan_prompt = f"""
Create a practical day-wise study plan for a student.

Subject: {planner_subject}
Exam date: {exam_date}
Today's date: {date.today()}
Available study time per day: {daily_hours} hours

Topics to cover:
{topics}

Instructions:
- Plan only for the days before the exam.
- Divide the topics across the available days.
- Include daily study time and a short revision session.
- Use a table with Day, Topics, and Study Tasks.
- Do not add topics the student did not provide.
- If the exam is today, create a one-day revision plan.
"""

                plan_response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=plan_prompt
                )

                st.session_state.study_plan = (
                    plan_response.text
                    or "Study plan couldn't be generated."
                )

            except Exception as error:
                if "503" in str(error) or "UNAVAILABLE" in str(error):
                    st.warning(
                        "Gemini is busy right now. Please wait and try again."
                    )
                else:
                    st.error("Study plan generate panna mudiyala.")
                    st.caption(str(error))

if st.session_state.study_plan:
    st.markdown("### 📅 Your Study Plan")
    st.markdown(st.session_state.study_plan)

    st.download_button(
        label="Download study plan",
        data=st.session_state.study_plan,
        file_name="study_plan.txt",
        mime="text/plain"
    )

# ---------------- CHAT HISTORY ----------------
st.divider()
st.subheader("💬 Study Chat")

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

    # Prepare previous chat messages
    chat_history = []

    for message in st.session_state.messages[:-1]:
        role = "user" if message["role"] == "user" else "model"

        chat_history.append({
            "role": role,
            "parts": [{"text": message["content"]}]
        })

    # Add uploaded notes to the current prompt
    notes_context = ""

    if st.session_state.notes_text:
        notes_context = (
            f"Subject: {subject_name or 'Not specified'}\n"
            "Use the uploaded notes as the main source. "
            "If the notes do not contain the answer, say so. "
            "Do not invent details.\n\n"
            f"UPLOADED NOTES:\n{st.session_state.notes_text}\n\n"
        )

    current_prompt = (
        f"Study mode: {study_mode}\n"
        f"Instructions: {mode_instructions[study_mode]}\n\n"
        f"{notes_context}"
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
                    model=MODEL_NAME,
                    contents=chat_history
                )

                answer = response.text or (
                    "I couldn't generate a response. Please try again."
                )

                st.markdown(answer)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer
                })

            except Exception as error:
                if "503" in str(error) or "UNAVAILABLE" in str(error):
                    st.warning(
                        "Gemini is busy right now. Please wait and try again."
                    )
                else:
                    st.error(
                        "Gemini API error. Please check your API key or model name."
                    )
                    st.caption(str(error))

# ---------------- CLEAR CHAT ----------------
if st.session_state.messages:
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()
