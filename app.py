import streamlit as st
from google import genai
from supabase import create_client
from pypdf import PdfReader
from io import BytesIO
from datetime import date

st.set_page_config(
    page_title="Student Study Assistant",
    page_icon="📚",
    layout="wide"
)

# ---------------- CONFIG ----------------
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")
GEMINI_MODEL = st.secrets.get("GEMINI_MODEL", "gemini-3.8-flash")

if not GEMINI_API_KEY:
    st.error("Gemini API key missing. Add GEMINI_API_KEY in Streamlit Secrets.")
    st.stop()

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase URL/key missing. Add SUPABASE_URL and SUPABASE_KEY in Streamlit Secrets.")
    st.stop()

try:
    gemini = genai.Client(api_key=GEMINI_API_KEY)
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"Connection setup failed: {e}")
    st.stop()


# ---------------- HELPERS ----------------
def ask_gemini(prompt):
    response = gemini.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )
    return response.text or "I couldn't generate an answer. Please try again."


def load_progress(user_id):
    result = (
        supabase.table("study_progress")
        .select("id, topic, completed")
        .eq("user_id", user_id)
        .order("id")
        .execute()
    )
    return result.data or []


def save_topic(user_id, topic):
    supabase.table("study_progress").insert({
        "user_id": user_id,
        "topic": topic,
        "completed": False
    }).execute()


def update_topic(user_id, row_id, completed):
    supabase.table("study_progress").update({
        "completed": completed
    }).eq("id", row_id).eq("user_id", user_id).execute()


def delete_user_progress(user_id):
    supabase.table("study_progress").delete().eq(
        "user_id", user_id
    ).execute()


# ---------------- SESSION STATE ----------------
if "user" not in st.session_state:
    st.session_state.user = None

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# ---------------- AUTH ----------------
st.title("📚 Student Study Assistant AI")

if not st.session_state.user:
    st.subheader("Login / Create account")

    auth_tab1, auth_tab2 = st.tabs(["Login", "Sign up"])

    with auth_tab1:
        with st.form("login_form"):
            login_email = st.text_input("Email", key="login_email")
            login_password = st.text_input(
                "Password", type="password", key="login_password"
            )
            login_submit = st.form_submit_button("Login")

        if login_submit:
            try:
                auth_result = supabase.auth.sign_in_with_password({
                    "email": login_email.strip(),
                    "password": login_password
                })

                st.session_state.user = auth_result.user
                st.session_state.access_token = auth_result.session.access_token
                st.session_state.refresh_token = auth_result.session.refresh_token
                st.rerun()
            except Exception:
                st.error("Login failed. Check your email/password, or verify your email.")

    with auth_tab2:
        with st.form("signup_form"):
            signup_email = st.text_input("Email", key="signup_email")
            signup_password = st.text_input(
                "Create password", type="password", key="signup_password"
            )
            signup_submit = st.form_submit_button("Create account")

        if signup_submit:
            try:
                signup_result = supabase.auth.sign_up({
                    "email": signup_email.strip(),
                    "password": signup_password
                })

                if signup_result.session:
                    st.session_state.user = signup_result.user
                    st.session_state.access_token = signup_result.session.access_token
                    st.session_state.refresh_token = signup_result.session.refresh_token
                    st.success("Account created!")
                    st.rerun()
                else:
                    st.success("Account created. Verify your email, then log in.")
            except Exception as e:
                st.error(f"Sign up failed: {e}")

    st.stop()


# Restore Supabase session for this app session
try:
    supabase.auth.set_session(
        st.session_state.access_token,
        st.session_state.refresh_token
    )
except Exception:
    st.session_state.user = None
    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.warning("Session expired. Please log in again.")
    st.rerun()

user_id = str(st.session_state.user.id)

with st.sidebar:
    st.write("Logged in as")
    st.caption(st.session_state.user.email)

    if st.button("Log out"):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass

        st.session_state.user = None
        st.session_state.access_token = None
        st.session_state.refresh_token = None
        st.session_state.chat_history = []
        st.rerun()


# ---------------- MAIN TABS ----------------
chat_tab, notes_tab, planner_tab, progress_tab = st.tabs([
    "💬 AI Study Chat",
    "📄 Notes Q&A",
    "🗓️ Study Planner",
    "📊 Progress Tracker"
])


# ---------------- AI STUDY CHAT ----------------
with chat_tab:
    st.subheader("Ask your study questions")

    study_mode = st.selectbox(
        "Choose a mode",
        [
            "Normal answer",
            "Explain simply",
            "Give examples",
            "Quiz me"
        ]
    )

    for item in st.session_state.chat_history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])

    question = st.chat_input("Ask a study question...")

    if question:
        st.session_state.chat_history.append({
            "role": "user",
            "content": question
        })

        mode_instructions = {
            "Normal answer": "Answer clearly and accurately.",
            "Explain simply": "Explain in simple beginner-friendly language.",
            "Give examples": "Explain and include a simple example.",
            "Quiz me": "Create a short quiz on this topic. Ask one question at a time."
        }

        prompt = (
            "You are a helpful student study assistant. "
            f"{mode_instructions[study_mode]}\n\n"
            f"Student question: {question}"
        )

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    answer = ask_gemini(prompt)
                    st.markdown(answer)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": answer
                    })
                except Exception as e:
                    st.error(f"Gemini request failed: {e}")


# ---------------- NOTES Q&A ----------------
with notes_tab:
    st.subheader("Chat with your notes")

    uploaded_file = st.file_uploader(
        "Upload PDF or TXT notes",
        type=["pdf", "txt"],
        key="notes_upload"
    )

    notes_text = ""

    if uploaded_file:
        try:
            if uploaded_file.name.lower().endswith(".pdf"):
                reader = PdfReader(BytesIO(uploaded_file.getvalue()))
                notes_text = "\n".join(
                    page.extract_text() or "" for page in reader.pages
                )
            else:
                notes_text = uploaded_file.getvalue().decode(
                    "utf-8", errors="ignore"
                )

            st.success("Notes loaded.")
            st.download_button(
                "Download extracted notes as TXT",
                data=notes_text,
                file_name="extracted_notes.txt",
                mime="text/plain"
            )
        except Exception as e:
            st.error(f"Could not read this file: {e}")

    if notes_text:
        if st.button("Summarize notes"):
            with st.spinner("Summarizing..."):
                try:
                    summary = ask_gemini(
                        "Summarize these study notes using clear headings and bullet points:\n\n"
                        + notes_text[:25000]
                    )
                    st.markdown(summary)
                except Exception as e:
                    st.error(f"Summary failed: {e}")

        notes_question = st.text_input(
            "Ask a question based on these notes",
            key="notes_question"
        )

        if st.button("Get answer from notes"):
            if notes_question.strip():
                with st.spinner("Finding an answer..."):
                    try:
                        answer = ask_gemini(
                            "Answer using the notes below. If the notes don't contain "
                            "the answer, say so clearly. Don't invent details.\n\n"
                            f"NOTES:\n{notes_text[:25000]}\n\n"
                            f"QUESTION:\n{notes_question}"
                        )
                        st.markdown(answer)
                    except Exception as e:
                        st.error(f"Question failed: {e}")


# ---------------- STUDY PLANNER ----------------
with planner_tab:
    st.subheader("Create a study plan")

    with st.form("planner_form"):
        subject = st.text_input("Subject")
        exam_date = st.date_input(
            "Exam date",
            min_value=date.today()
        )
        daily_hours = st.number_input(
            "Study hours per day",
            min_value=0.5,
            max_value=12.0,
            value=2.0,
            step=0.5
        )
        topics = st.text_area(
            "Topics (one per line)",
            placeholder="Unit 1\nUnit 2\nImportant questions"
        )
        planner_submit = st.form_submit_button("Generate study plan")

    if planner_submit:
        if not subject.strip() or not topics.strip():
            st.warning("Enter the subject and topics first.")
        else:
            with st.spinner("Preparing your plan..."):
                try:
                    plan = ask_gemini(
                        "Create a realistic day-wise study plan for a student. "
                        "Use a table or clear day headings. Include revision and breaks. "
                        f"Subject: {subject}\n"
                        f"Exam date: {exam_date}\n"
                        f"Daily study hours: {daily_hours}\n"
                        f"Topics:\n{topics}"
                    )
                    st.markdown(plan)
                    st.download_button(
                        "Download study plan",
                        data=plan,
                        file_name="study_plan.txt",
                        mime="text/plain"
                    )
                except Exception as e:
                    st.error(f"Planner failed: {e}")


# ---------------- STUDY PROGRESS TRACKER ----------------
with progress_tab:
    st.subheader("Track your study progress")

    with st.form("add_topics_form"):
        topic_text = st.text_area(
            "Add topics (one topic per line)",
            placeholder="Process Management\nMemory Management\nFile Systems"
        )
        add_topics = st.form_submit_button("Save topics")

    if add_topics:
        new_topics = [
            topic.strip()
            for topic in topic_text.splitlines()
            if topic.strip()
        ]

        try:
            existing = load_progress(user_id)
            existing_names = {row["topic"].strip().lower() for row in existing}

            for topic in new_topics:
                if topic.lower() not in existing_names:
                    save_topic(user_id, topic)
                    existing_names.add(topic.lower())

            st.success("Topics saved.")
            st.rerun()
        except Exception as e:
            st.error(f"Could not save topics: {e}")

    try:
        progress_rows = load_progress(user_id)

        if progress_rows:
            completed_count = sum(
                1 for row in progress_rows if row["completed"]
            )
            total_count = len(progress_rows)
            progress_value = completed_count / total_count

            st.progress(progress_value)
            st.write(
                f"Completed: {completed_count} / {total_count} "
                f"({progress_value:.0%})"
            )

            st.divider()
            st.write("Tick topics as you complete them:")

            for row in progress_rows:
                checked = st.checkbox(
                    row["topic"],
                    value=bool(row["completed"]),
                    key=f"topic_{row['id']}"
                )

                if checked != bool(row["completed"]):
                    try:
                        update_topic(user_id, row["id"], checked)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not update progress: {e}")

            if st.button("Delete all my progress"):
                try:
                    delete_user_progress(user_id)
                    st.success("Your progress was deleted.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not delete progress: {e}")
        else:
            st.info("No topics yet. Add topics above to start tracking.")
    except Exception as e:
        st.error(f"Could not load progress: {e}")
