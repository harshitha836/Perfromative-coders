import streamlit as st
from groq import Groq
from dotenv import load_dotenv
import os
import PyPDF2
import pandas as pd

# ---------------- Load API key ----------------
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

# ---------------- Streamlit setup ----------------
st.set_page_config(page_title="Travel Insurance Chatbot", page_icon="🧳")
st.title("🧳 Your Travel Insurance Companion")

# ---------------- Session State ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

if "custom_pdfs" not in st.session_state:
    st.session_state.custom_pdfs = {}

if "destination_list" not in st.session_state:
    st.session_state.destination_list = ""

if "weather_forecast" not in st.session_state:
    st.session_state.weather_forecast = ""

# ---------------- Display previous messages ----------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------- PDF Upload ----------------
uploaded_file = st.file_uploader("📄 Upload a PDF (optional)", type=["pdf"])
if uploaded_file:
    pdf_reader = PyPDF2.PdfReader(uploaded_file)
    pdf_text = "\n".join([page.extract_text() or "" for page in pdf_reader.pages])
    st.session_state.pdf_text = pdf_text.strip()
    st.success("PDF uploaded and text extracted!")

# ---------------- Preload Multiple Custom PDFs ----------------
custom_pdf_files = [
    "Scootsurance QSR022206_updated.pdf",
    "TravelEasy Policy QTD032212.pdf",
    "TravelEasy Pre-Ex Policy QTD032212-PX.pdf"
]

for pdf_file in custom_pdf_files:
    if os.path.exists(pdf_file) and pdf_file not in st.session_state.custom_pdfs:
        reader = PyPDF2.PdfReader(pdf_file)
        text = "\n".join([page.extract_text() or "" for page in reader.pages])
        st.session_state.custom_pdfs[pdf_file] = text.strip()
        st.info(f"{pdf_file} loaded!")

# ---------------- Load Destination List ----------------
excel_path = "Scoot_SG_destination_list.xlsx"
if os.path.exists(excel_path) and not st.session_state.destination_list:
    df = pd.read_excel(excel_path)
    destinations = df[["Region", "Country", "Country Code"]].dropna()
    dest_text = destinations.to_string(index=False)
    st.session_state.destination_list = f"Here is the list of travel destinations supported:\n{dest_text}"
    st.info("Destination list loaded!")

# ---------------- Load Weather Forecast ----------------
if not st.session_state.weather_forecast:
    st.session_state.weather_forecast = (
        "🌦️ Singapore's weather in November 2025 is expected to be warm and wet, with frequent thundery showers "
        "especially in the afternoons and occasional gusty winds from Sumatra squalls. Temperatures will range from 33°C to 35°C. "
        "Rainfall is forecast to be below average, but travelers should still prepare for wet conditions on most days."
    )

# ---------------- Initial Friendly Prompt ----------------
if not st.session_state.messages:
    intro = (
        "Hey there! 😊 Planning a trip soon?\n\n"
        "I’m here to help you sort out your travel insurance. Just tell me:\n"
        "- Where you're headed\n"
        "- Your age\n"
        "- How long you'll be away\n"
        "- Whether you plan to rent a vehicle\n"
        "- And if you'd like to check past natural disaster history for your destination\n\n"
        "I'll also factor in the latest weather forecast to help you choose the best coverage. Here's what I found:\n\n"
        f"{st.session_state.weather_forecast}"
    )
    st.chat_message("assistant").markdown(intro)
    st.session_state.messages.append({"role": "assistant", "content": intro})

# ---------------- Chat Input ----------------
if prompt := st.chat_input("Tell me about your trip..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    messages_for_groq = st.session_state.messages.copy()

    # Inject uploaded PDF content
    if st.session_state.pdf_text:
        messages_for_groq.insert(0, {
            "role": "system",
            "content": f"The user uploaded a PDF. Here is the content:\n{st.session_state.pdf_text}"
        })

    # Inject custom PDFs
    for filename, content in st.session_state.custom_pdfs.items():
        messages_for_groq.insert(0, {
            "role": "system",
            "content": f"Travel insurance policy data from {filename}:\n{content}"
        })

    # Inject destination list
    if st.session_state.destination_list:
        messages_for_groq.insert(0, {
            "role": "system",
            "content": st.session_state.destination_list
        })

    # Inject weather forecast
    messages_for_groq.insert(0, {
        "role": "system",
        "content": f"Latest weather forecast:\n{st.session_state.weather_forecast}"
    })

    # System instructions
    messages_for_groq.insert(0, {
        "role": "system",
        "content": (
            "You are a friendly travel insurance advisor. Only answer questions related to travel insurance. "
            "Use the provided policy documents, destination list, and weather forecast to guide your responses. "
            "Prompt the user for:\n"
            "- Destination, age, and trip duration\n"
            "- Whether they plan to rent a vehicle\n"
            "- If they want to check past natural disaster history\n\n"
            "Based on their answers, suggest relevant insurance policies from Scootsurance or TravelEasy. "
            "Once they choose a policy, recommend useful add-ons like hospital income, rental car coverage, or COVID-19 benefits. "
            "If the user declines add-ons, gently follow up with:\n"
            "'Are you sure? These extras can really help if things don’t go as planned.'\n"
            "If they still say no, respect their choice and proceed with confirming their selected coverage.\n\n"
            "Keep the tone warm, conversational, and helpful throughout."
        )
    })

    # Generate response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages_for_groq,
            stream=True,
        )

        for chunk in response:
            if hasattr(chunk.choices[0].delta, "content"):
                full_response += chunk.choices[0].delta.content or ""
                message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})