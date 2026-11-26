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

# Gemini API key
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    st.error(
        "GEMINI_API_KEY missing. Streamlit Cloud → Manage app → "
        "Settings → Secrets-la API key add pannunga."
    )
    st.stop()

# Gemini client
client = genai.Client(api_key=api_key)

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
question = st.chat_input("Type your study question here...")

if question:
    # Show user question
    st.session_state.messages.append(
        {"role": "user", "content": question}
    )

    with st.chat_message("user"):
        st.markdown(question)

    # Get Gemini response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=question
                )

                answer = response.text or "I couldn't generate a response. Please try again."
                st.markdown(answer)

                st.session_state.messages.append(
                    {"role": "assistant", "content": answer}
                )

            except Exception as error:
                st.error("Gemini API error. Please check your API key and model name.")
                st.caption(str(error))

# Clear chat button
if st.session_state.messages:
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()
