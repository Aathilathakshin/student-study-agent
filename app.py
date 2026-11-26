import streamlit as st
from google import genai

# Page setup
st.set_page_config(
    page_title="Student Study Assistant",
    page_icon="📚",
    layout="centered"
)

st.title("📚 Student Study Assistant AI Agent")
st.caption("Ask questions, understand concepts, and get help with your studies.")

# Get API key from Streamlit Secrets
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error(
        "GEMINI_API_KEY missing. Streamlit Cloud → Manage app → "
        "Settings → Secrets-la API key add pannunga."
    )
    st.stop()

# Create Gemini client
client = genai.Client(api_key=api_key)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Study mode selector
study_mode = st.selectbox(
    "Choose study mode",
    [
        "Normal answer",
        "Explain simply",
        "Give examples",
        "Quiz me"
    ]
)

# Display previous chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
question = st.chat_input("Type your study question here...")

if question:
    # Display and store the user's question
    st.session_state.messages.append({
        "role": "user",
        "content": question
    })

    with st.chat_message("user"):
        st.markdown(question)

    # Prepare previous conversation for Gemini
    chat_history = []

    for message in st.session_state.messages[:-1]:
        role = "user" if message["role"] == "user" else "model"

        chat_history.append({
            "role": role,
            "parts": [{"text": message["content"]}]
        })

    # Add current question with selected study mode
    mode_instructions = {
        "Normal answer": "Answer clearly and accurately.",
        "Explain simply": "Explain in beginner-friendly, simple language. Break down difficult ideas into steps.",
        "Give examples": "Explain the topic and include a simple, relevant example.",
        "Quiz me": "Create a short quiz about the topic. Ask one question at a time and wait for the user's answer. Do not reveal the answer immediately."
    }

    current_prompt = (
        f"Study mode: {study_mode}.\n"
        f"{mode_instructions[study_mode]}\n\n"
        f"User's question: {question}"
    )

    chat_history.append({
        "role": "user",
        "parts": [{"text": current_prompt}]
    })

    # Generate response
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

                # Save assistant response
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

# Clear chat button
if st.session_state.messages:
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()
