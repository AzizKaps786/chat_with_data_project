import os
import streamlit as st
from dotenv import load_dotenv

from agent import DataAnalysisAgent
from utils.file_handler import load_file

load_dotenv()

st.set_page_config(page_title="Chat With Your Data", page_icon="📊", layout="wide")

st.markdown("""
<style>
    .suggestion-box {
        background: #1e2a3a;
        border-left: 3px solid #00ff9f;
        padding: 10px;
        border-radius: 5px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Chat With Your Data")
st.caption("Upload any dataset and analyze it through conversation")

if "agent" not in st.session_state:
    st.session_state.agent = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "df" not in st.session_state:
    st.session_state.df = None
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

with st.sidebar:
    st.header("📁 Upload Data")

    if not os.getenv("GROQ_API_KEY"):
        st.warning("Add GROQ_API_KEY in your .env file before chatting.")

    uploaded_file = st.file_uploader("Choose file", type=["csv", "xlsx", "xls", "json"])

    if uploaded_file:
        df = load_file(uploaded_file)
        if df is not None:
            st.session_state.df = df
            st.session_state.agent = DataAnalysisAgent(df)
            st.session_state.messages = []
            st.success(f"✅ Loaded {len(df):,} rows")

            st.subheader("Preview")
            st.dataframe(df.head(), use_container_width=True)

            st.subheader("Quick Info")
            st.write(f"**Rows:** {df.shape[0]:,}")
            st.write(f"**Columns:** {df.shape[1]:,}")
            st.write(f"**Missing values:** {int(df.isnull().sum().sum()):,}")

    if st.session_state.df is not None:
        st.subheader("💡 Try Asking")
        questions = [
            "Give me an overview of this data",
            "Show distribution of numeric columns",
            "Find correlations in the data",
            "Show me top 10 records",
            "Are there any anomalies?",
        ]
        for q in questions:
            if st.button(q, use_container_width=True):
                st.session_state.pending_question = q

if st.session_state.df is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style='text-align:center; padding:50px'>
            <h2>👈 Upload your data to start</h2>
            <p>Supports CSV, Excel, and JSON</p>
            <br>
            <p>Then ask questions like:</p>
            <p><i>"Show me the trend over time"</i></p>
            <p><i>"Which category has most sales?"</i></p>
            <p><i>"Why did revenue drop in March?"</i></p>
        </div>
        """, unsafe_allow_html=True)
else:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message.get("fig") is not None:
                st.plotly_chart(message["fig"], use_container_width=True)
            if message.get("content"):
                st.write(message["content"])
            if message.get("suggestion"):
                st.markdown(f"""
                <div class='suggestion-box'>
                💡 Try next: <i>{message['suggestion']}</i>
                </div>
                """, unsafe_allow_html=True)
            if message.get("code"):
                with st.expander("Show generated code"):
                    st.code(message["code"], language="python")

    user_input = st.chat_input("Ask anything about your data...")

    if st.session_state.pending_question:
        user_input = st.session_state.pending_question
        st.session_state.pending_question = None

    if user_input:
        with st.chat_message("user"):
            st.write(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                response = st.session_state.agent.chat(user_input)

            if response["success"]:
                if response.get("fig") is not None:
                    st.plotly_chart(response["fig"], use_container_width=True)
                if response.get("insight"):
                    st.write(response["insight"])
                if response.get("suggestion"):
                    st.markdown(f"""
                    <div class='suggestion-box'>
                    💡 Try next: <i>{response['suggestion']}</i>
                    </div>
                    """, unsafe_allow_html=True)
                with st.expander("Show generated code"):
                    st.code(response.get("code", ""), language="python")
            else:
                st.error("Could not analyze. Try rephrasing the question.")
                with st.expander("Technical error"):
                    st.code(response.get("error", ""))

        st.session_state.messages.append({
            "role": "assistant",
            "fig": response.get("fig"),
            "content": response.get("insight") if response.get("success") else "Could not analyze. Try rephrasing the question.",
            "suggestion": response.get("suggestion"),
            "code": response.get("code"),
        })
