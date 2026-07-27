import streamlit as st
import edge_tts
import asyncio
import io
import uuid
import re
import docx
from pypdf import PdfReader

# ==========================================
# 1. పేజీ సెట్టింగ్స్ & కాన్ఫిగరేషన్
# ==========================================
st.set_page_config(
    page_title="స్త్రీ శక్తి - ఆడియో వాయిస్ కన్వర్టర్", 
    layout="wide", 
    page_icon="🌸"
)

# Session State ఇనిషియలైజేషన్
if "chat_history" not in st.session_state:
    st.session_state.chat_history = {}  
if "current_chat_id" not in st.session_state:
    initial_id = str(uuid.uuid4())
    st.session_state.chat_history[initial_id] = {"title": "కొత్త ఆడియో నోట్", "messages": []}
    st.session_state.current_chat_id = initial_id

if "rename_id" not in st.session_state:
    st.session_state.rename_id = None


# ==========================================
# 2. హెల్పర్ ఫంక్షన్స్ (Core TTS Engine)
# ==========================================

# Edge-TTS Async Chunk Generator
async def generate_voice_chunk(text, voice, pitch_val, rate_val):
    communicate = edge_tts.Communicate(text, voice, pitch=pitch_val, rate=rate_val)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    return audio_data


# Auto-Chunking Logic (Smart Text Splitter)
def split_text_into_chunks(text, max_chars=400):
    sentences = re.split(r'(?<=[.!?\n।])\s+', text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_chars:
            current_chunk += sentence + " "
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
            
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
        
    return chunks


# File Text Extractor (.docx, .pdf, .txt)
def extract_text_from_file(uploaded_file):
    extracted = ""
    if uploaded_file.name.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        extracted = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    elif uploaded_file.name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        pdf_text = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                pdf_text.append(t)
        extracted = "\n".join(pdf_text)
    elif uploaded_file.name.endswith(".txt"):
        extracted = uploaded_file.read().decode("utf-8")
    return extracted


# Word Counter & Duration Estimator
def get_text_analytics(text, speed_factor=0.85):
    words = text.split()
    word_count = len(words)
    words_per_minute = 130 * speed_factor
    estimated_minutes = word_count / words_per_minute if words_per_minute > 0 else 0
    return word_count, round(estimated_minutes, 1)


# ==========================================
# 3. సైడ్ బార్
# ==========================================
with st.sidebar:
    st.title("🌸 స్త్రీ శక్తి ఆడియో నోట్స్")
    if st.button("➕ కొత్త ఆడియో నోట్", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.chat_history[new_id] = {"title": "కొత్త ఆడియో నోట్", "messages": []}
        st.session_state.current_chat_id = new_id
        st.session_state.rename_id = None
        st.rerun()

    st.divider()
    st.subheader("సేవ్ చేసిన ఆడియో జాబితా")
    
    for chat_id in list(st.session_state.chat_history.keys()):
        if st.session_state.rename_id == chat_id:
            new_title = st.text_input("కొత్త టైటిల్ ఇవ్వండి:", value=st.session_state.chat_history[chat_id]["title"], key=f"input_ren_{chat_id}")
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                if st.button("Save", key=f"save_title_{chat_id}"):
                    st.session_state.chat_history[chat_id]["title"] = new_title
                    st.session_state.rename_id = None
                    st.rerun()
            with col_s2:
                if st.button("Cancel", key=f"cancel_title_{chat_id}"):
                    st.session_state.rename_id = None
                    st.rerun()
        else:
            col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
            with col1:
                btn_label = st.session_state.chat_history[chat_id]["title"]
                if st.button(btn_label, key=f"btn_{chat_id}", use_container_width=True):
                    st.session_state.current_chat_id = chat_id
                    st.rerun()
            with col2:
                if st.button("✏️", key=f"ren_{chat_id}"):
                    st.session_state.rename_id = chat_id
                    st.rerun()
            with col3:
                if st.button("🗑️", key=f"del_{chat_id}"):
                    del st.session_state.chat_history[chat_id]
                    if not st.session_state.chat_history:
                        new_id = str(uuid.uuid4())
                        st.session_state.chat_history[new_id] = {"title": "కొత్త ఆడియో నోట్", "messages": []}
                        st.session_state.current_chat_id = new_id
                    elif st.session_state.current_chat_id == chat_id:
                        st.session_state.current_chat_id = list(st.session_state.chat_history.keys())[0]
                    st.rerun()


# ==========================================
# 4. ప్రధాన స్క్రీన్
# ==========================================
st.header("🌺 స్త్రీ శక్తి - వాయిస్ ఆడియో కన్వర్టర్")
st.caption("మీ టెక్స్ట్ మరియు ఫైల్స్‌ను ఆకర్షణీయమైన స్పష్టమైన వాయిస్‌తో MP3 ఆడియోగా మార్చుకోండి.")

current_chat = st.session_state.chat_history[st.session_state.current_chat_id]
msg_to_delete = None

for idx, m in enumerate(current_chat["messages"]):
    with st.chat_message("assistant", avatar="🌺"):
        st.markdown(m["text"])
        st.caption(
            f"🌐 భాష: {m.get('lang_name', 'తెలుగు')} | "
            f"🎙️ వాయిస్: {m.get('voice_name', 'తెలుగు')} | "
            f"🔊 వేగం: {m.get('speed', 1.0)}x"
        )
        
        if "audio" in m and m["audio"] is not None:
            st.audio(m["audio"], format="audio/mp3")

        c1, c2, _ = st.columns([0.08, 0.18, 0.74])
        with c1:
            if st.button("🗑️", key=f"msg_del_{idx}"):
                msg_to_delete = idx
        with c2:
            if "audio" in m and m["audio"] is not None:
                st.download_button(
                    label="📥 MP3 డౌన్‌లోడ్", 
                    data=m["audio"], 
                    file_name=f"stree_shakti_audio_{idx+1}.mp3", 
                    mime="audio/mp3",
                    key=f"audio_dl_{idx}"
                )

if msg_to_delete is not None:
    current_chat["messages"].pop(msg_to_delete)
    st.rerun()


# ==========================================
# 5. ఇన్‌పుట్ & ఫైల్ అప్‌లోడ్
# ==========================================
st.divider()

uploaded_file = st.file_uploader(
    "📁 మీ ఫైల్‌ను ఇక్కడ అప్‌లోడ్ చేయండి (.docx, .pdf, .txt):", 
    type=["docx", "pdf", "txt"],
    help="వర్డ్ ఫైల్, పీడీఎఫ్ లేదా టెక్స్ట్ ఫైల్‌ని అప్‌లోడ్ చేస్తే ఆటోమేటిక్‌గా టెక్స్ట్ చదవబడుతుంది."
)

file_extracted_text = ""
if uploaded_file is not None:
    try:
        file_extracted_text = extract_text_from_file(uploaded_file)
        st.success(f"✅ '{uploaded_file.name}' ఫైల్ నుండి టెక్స్ట్ విజయవంతంగా లోడ్ అయింది!")
    except Exception as fe:
        st.error(f"ఫైల్ చదవడంలో లోపం వచ్చింది: {fe}")

user_text = st.text_area(
    "ఆడియోగా మార్చాలనుకుంటున్న టెక్స్ట్ (ఫైల్ అప్‌లోడ్ చేయవచ్చు లేదా నేరుగా ఇక్కడ పేస్ట్ చేయవచ్చు):", 
    value=file_extracted_text,
    height=150, 
    placeholder="ఇక్కడ టెక్స్ట్ పేస్ట్ చేయండి..."
)

if user_text.strip():
    w_count, est_mins = get_text_analytics(user_text)
    st.info(f"📊 **మొత్తం పదాలు:** {w_count:,} | ⏱️ **అంచనా ఆడియో సమయం:** ~{est_mins} నిమిషాలు")

col_lang, col_voice, col_speed = st.columns([0.3, 0.35, 0.35])

with col_lang:
    selected_lang = st.selectbox(
        "🌐 భాషను ఎంచుకోండి (Select Language):",
        options=["తెలుగు (Telugu)", "హిందీ (Hindi)", "ఇంగ్లీష్ (English)"]
    )

with col_voice:
    if "తెలుగు" in selected_lang:
        voice_option = st.radio(
            "🎙️ స్వరాన్ని ఎంచుకోండి:",
            options=["👩 శ్రుతి (స్త్రీ)", "👨 మోహన్ (పురుష)"],
            horizontal=True
        )
    elif "హిందీ" in selected_lang:
        voice_option = st.radio(
            "🎙️ స్వరాన్ని ఎంచుకోండి:",
            options=["👩 స్వర్ణ (స్త్రీ - హిందీ)", "👨 మధుర్ (పురుష - హిందీ)"],
            horizontal=True
        )
    else:
        voice_option = st.radio(
            "🎙️ స్వరాన్ని ఎంచుకోండి:",
            options=["👩 నీరజ (స్త్రీ - ఇంగ్లీష్)", "👨 ప్రభాత్ (పురుష - ఇంగ్లీష్)"],
            horizontal=True
        )

with col_speed:
    audio_speed = st.select_slider(
        "🔊 ఆడియో వేగం (Speed):",
        options=[0.75, 0.85, 1.0, 1.15, 1.25, 1.5],
        value=0.85
    )

col_pitch, _ = st.columns([0.5, 0.5])
with col_pitch:
    pitch_custom = st.select_slider(
        "🎚️ వాయిస్ పిచ్ (Pitch Base):",
        options=["సాధారణ (Normal)", "గంభీరం (Deep Base)", "అత్యంత గంభీరం (Heavy Base)"],
        value="సాధారణ (Normal)"
    )


# ==========================================
# 6. ఆడియో జనరేషన్
# ==========================================
convert_btn = st.button("🔊 స్త్రీ శక్తి ఆడియో క్రియేట్ చేయి", type="primary", use_container_width=True)

if convert_btn:
    if user_text.strip():
        with st.spinner("ఆడియో ప్రాసెస్ అవుతోంది... దయచేసి వేచి ఉండండి..."):
            try:
                clean_txt = user_text.replace("*", "").replace("#", "")
                
                voice_map = {
                    "👨 మోహన్ (పురుష)": ("te-IN-MohanNeural", "మోహన్ (తెలుగు)", "తెలుగు"),
                    "👩 శ్రుతి (స్త్రీ)": ("te-IN-ShrutiNeural", "శ్రుతి (తెలుగు)", "తెలుగు"),
                    "👨 మధుర్ (పురుష - హిందీ)": ("hi-IN-MadhurNeural", "మధుర్ (హిందీ)", "హిందీ"),
                    "👩 స్వర్ణ (స్త్రీ - హిందీ)": ("hi-IN-SwaraNeural", "స్వర్ణ (హిందీ)", "హిందీ"),
                    "👨 ప్రభాత్ (పురుష - ఇంగ్లీష్)": ("en-IN-PrabhatNeural", "ప్రభాత్ (ఇంగ్లీష్)", "ఇంగ్లీష్"),
                    "👩 నీరజ (స్త్రీ - ఇంగ్లీష్)": ("en-IN-NeerjaNeural", "నీరజ (ఇంగ్లీష్)", "ఇంగ్లీష్")
                }
                selected_voice_code, voice_label, lang_label = voice_map[voice_option]

                rate_str = f"{int((audio_speed - 1.0) * 100):+d}%"
                
                pitch_val_map = {
                    "సాధారణ (Normal)": "0Hz",
                    "గంభీరం (Deep Base)": "-10Hz" if "పురుష" in voice_option else "-5Hz",
                    "అత్యంత గంభీరం (Heavy Base)": "-18Hz" if "పురుష" in voice_option else "-10Hz"
                }
                pitch_str = pitch_val_map[pitch_custom]

                text_chunks = split_text_into_chunks(clean_txt, max_chars=400)
                
                combined_audio = b""

                for chunk in text_chunks:
                    raw_audio = asyncio.run(generate_voice_chunk(chunk, selected_voice_code, pitch_str, rate_str))
                    combined_audio += raw_audio

                current_chat["messages"].append({
                    "text": user_text,
                    "audio": combined_audio,
                    "speed": audio_speed,
                    "voice_name": voice_label,
                    "lang_name": lang_label
                })

                if len(current_chat["messages"]) == 1 or current_chat["title"] == "కొత్త ఆడియో నోట్":
                    current_chat["title"] = user_text[:20] + ("..." if len(user_text) > 20 else "")

                st.success(f"🎉 స్త్రీ శక్తి {lang_label} ఆడియో సిద్ధమైంది!")
                st.rerun()

            except Exception as e:
                st.error(f"ఆడియో తయారీలో లోపం: {e}")
    else:
        st.warning("దయచేసి టెక్స్ట్ ఎంటర్ చేయండి లేదా ఫైల్ అప్‌లోడ్ చేయండి.")
