import streamlit as st
import edge_tts
from pydub import AudioSegment
import asyncio
import io
import re
import os
import traceback
import docx
from pypdf import PdfReader
from deep_translator import GoogleTranslator
from streamlit_mic_recorder import speech_to_text

# ==========================================
# 1. పేజీ సెట్టింగ్స్
# ==========================================
st.set_page_config(
    page_title="ఆధ్యాత్మిక వాయిస్ & అనువాదక యంత్రం", 
    layout="wide", 
    page_icon="🕉️"
)

st.header("🔱 ఆధ్యాత్మిక వాయిస్ & భాషా అనువాద వ్యవస్థ")
st.caption("సింపుల్ వెర్షన్ - లైవ్ ఎర్రర్ ట్రాకర్ తో")

# Session State
if "voice_input_text" not in st.session_state:
    st.session_state.voice_input_text = ""
if "translated_text_val" not in st.session_state:
    st.session_state.translated_text_val = ""


# ==========================================
# 2. హెల్పర్ ఫంక్షన్స్ (Direct File Stream Fix)
# ==========================================

async def generate_voice_file(text, voice, output_filename):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_filename)


def split_text_into_chunks(text, max_chars=300):
    # టెక్స్ట్‌ను క్లీన్ చేసి కేవలం వాక్యాలను మాత్రమే తీసుకోవడం
    clean_text = re.sub(r'\s+', ' ', text).strip()
    sentences = re.split(r'(?<=[.!?\n।])\s+', clean_text)
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
    return [c.strip() for c in chunks if len(c.strip()) > 1]


def extract_text_from_file(uploaded_file):
    extracted = ""
    if uploaded_file.name.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        extracted = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    elif uploaded_file.name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        pdf_text = [page.extract_text() for page in reader.pages if page.extract_text()]
        extracted = "\n".join(pdf_text)
    elif uploaded_file.name.endswith(".txt"):
        extracted = uploaded_file.read().decode("utf-8")
    return extracted


# ==========================================
# 3. ఇన్‌పుట్, మైక్రోఫోన్ & ఫైల్
# ==========================================
st.divider()
col_file, col_mic = st.columns([0.5, 0.5])

with col_file:
    uploaded_file = st.file_uploader("📁 మీ ఫైల్‌ను అప్‌లోడ్ చేయండి (.docx, .pdf, .txt):", type=["docx", "pdf", "txt"])

with col_mic:
    st.markdown("**🎙️ మైక్రోఫోన్ ద్వారా మాట్లాడండి:**")
    mic_lang = st.selectbox("మాట్లాడే భాష:", options=["తెలుగు (Telugu)", "హిందీ (Hindi)", "ఇంగ్లీష్ (English)"])
    mic_code_map = {"తెలుగు (Telugu)": "te-IN", "హిందీ (Hindi)": "hi-IN", "ఇంగ్లీష్ (English)": "en-IN"}
    
    spoken_text = speech_to_text(
        start_prompt="🎙️ మాట్లాడటం ప్రారంభించండి",
        stop_prompt="⏹️ ఆపండి",
        language=mic_code_map[mic_lang],
        use_container_width=True,
        key='speech_recorder'
    )
    if spoken_text:
        st.session_state.voice_input_text += " " + spoken_text

file_extracted_text = ""
if uploaded_file is not None:
    try:
        file_extracted_text = extract_text_from_file(uploaded_file)
        st.success(f"✅ ఫైల్ లోడ్ అయింది!")
    except Exception as fe:
        st.error(f"ఫైల్ చదవడంలో లోపం: {fe}")

initial_text_val = file_extracted_text if file_extracted_text else st.session_state.voice_input_text

user_text = st.text_area("ఆడియోగా మార్చాలనుకుంటున్న టెక్స్ట్:", value=initial_text_val, height=140)


# ==========================================
# 4. అనువాదం (Translation)
# ==========================================
if user_text.strip():
    st.markdown("##### 🌐 భాషా అనువాదం (Translator)")
    col_tr1, col_tr2 = st.columns([0.7, 0.3])
    with col_tr1:
        target_trans_lang = st.selectbox("ఏ భాషలోకి మార్చాలి?:", options=["తెలుగు (Telugu)", "హిందీ (Hindi)", "ఇంగ్లీష్ (English)"])
    with col_tr2:
        st.write("")
        st.write("")
        if st.button("🔄 అనువదించు (Translate)", use_container_width=True):
            try:
                lang_code_map = {"తెలుగు (Telugu)": "te", "హిందీ (Hindi)": "hi", "ఇంగ్లీష్ (English)": "en"}
                t = GoogleTranslator(source='auto', target=lang_code_map[target_trans_lang]).translate(user_text)
                st.session_state["translated_text_val"] = t
                st.success("✅ అనువాదం పూర్తయింది!")
            except Exception as tr_err:
                st.error(f"అనువాదంలో లోపం: {tr_err}")

    if st.session_state["translated_text_val"]:
        st.text_area("అనువాదం అయిన టెక్స్ట్:", value=st.session_state["translated_text_val"], height=100)


# ==========================================
# 5. ఆడియో ఎంపికలు & క్రియేషన్
# ==========================================
st.divider()
col_lang, col_voice = st.columns([0.5, 0.5])

with col_lang:
    selected_lang = st.selectbox("🌐 ఆడియో భాష:", options=["తెలుగు (Telugu)", "హిందీ (Hindi)", "ఇంగ్లీష్ (English)"])

with col_voice:
    if "తెలుగు" in selected_lang:
        voice_option = st.radio("🎙️ స్వరం:", options=["👨 మోహన్ (పురుష)", "👩 శ్రుతి (స్త్రీ)"], horizontal=True)
    elif "హిందీ" in selected_lang:
        voice_option = st.radio("🎙️ స్వరం:", options=["👨 మధుర్ (పురుష)", "👩 స్వర్ణ (స్త్రీ)"], horizontal=True)
    else:
        voice_option = st.radio("🎙️ స్వరం:", options=["👨 ప్రభాత్ (పురుష)", "👩 నీరజ (స్త్రీ)"], horizontal=True)

convert_btn = st.button("🔊 ఆడియో క్రియేట్ చేయి", type="primary", use_container_width=True)


# ==========================================
# 6. ఆడియో జనరేషన్
# ==========================================
if convert_btn:
    if user_text.strip():
        with st.spinner("ఆడియో ప్రాసెస్ అవుతోంది... దయచేసి వేచి ఉండండి..."):
            try:
                clean_txt = re.sub(r'[*#_~`]', '', user_text.strip())
                
                voice_map = {
                    "👨 మోహన్ (పురుష)": "te-IN-MohanNeural",
                    "👩 శ్రుతి (స్త్రీ)": "te-IN-ShrutiNeural",
                    "👨 మధుర్ (పురుష)": "hi-IN-MadhurNeural",
                    "👩 స్వర్ణ (స్త్రీ)": "hi-IN-SwaraNeural",
                    "👨 ప్రభాత్ (పురుష)": "en-IN-PrabhatNeural",
                    "👩 నీరజ (స్త్రీ)": "en-IN-NeerjaNeural"
                }
                selected_voice = voice_map[voice_option]

                text_chunks = split_text_into_chunks(clean_txt, max_chars=300)
                
                debug_logs = []
                speech_sound = AudioSegment.empty()

                for i, chunk in enumerate(text_chunks):
                    temp_file = f"temp_{i}.mp3"
                    try:
                        # 🛠️ డైరెక్ట్ ఫైల్‌కి సేవ్ చేసి ఆడియో రీడ్ చేసే గ్యారెంటీ లాజిక్
                        asyncio.run(generate_voice_file(chunk, selected_voice, temp_file))
                        
                        if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                            chunk_sound = AudioSegment.from_file(temp_file)
                            speech_sound += chunk_sound
                            os.remove(temp_file) # తాత్కాలిక ఫైల్ ని తొలగించడం
                        else:
                            debug_logs.append(f"Chunk {i+1}: ఫైల్ ఖాళీగా క్రియేట్ అయింది.")
                    except Exception as chunk_ex:
                        debug_logs.append(f"Chunk {i+1} Error: {str(chunk_ex)}")

                # BGM మిక్సింగ్
                if len(speech_sound) > 0:
                    final_sound = speech_sound
                    if os.path.exists("bgm.mp3"):
                        try:
                            bgm_sound = AudioSegment.from_file("bgm.mp3")
                            if len(bgm_sound) < len(speech_sound):
                                bgm_sound = bgm_sound * ((len(speech_sound) // len(bgm_sound)) + 1)
                            bgm_sound = bgm_sound[:len(speech_sound)] - 15
                            final_sound = speech_sound.overlay(bgm_sound)
                        except Exception as bgm_ex:
                            st.warning(f"BGM మిక్సింగ్ సమస్య: {bgm_ex}")

                    final_fp = io.BytesIO()
                    final_sound.export(final_fp, format="mp3")
                    audio_bytes = final_fp.getvalue()

                    st.success("🎉 ఆడియో విజయవంతంగా సిద్ధమైంది!")
                    st.audio(audio_bytes, format="audio/mp3")
                    st.download_button("📥 MP3 డౌన్‌లోడ్", data=audio_bytes, file_name="spiritual_audio.mp3", mime="audio/mp3")
                else:
                    st.error("❌ ఆడియో డేటా ఏదీ జనరేట్ కాలేదు!")
                    st.write("🔍 **లైవ్ డెబగ్ లాగ్స్:**")
                    for log in debug_logs:
                        st.code(log)

            except Exception as e:
                st.error("❌ ఆడియో సిస్టమ్‌లో లోపం వచ్చింది:")
                st.code(traceback.format_exc())
    else:
        st.warning("దయచేసి టెక్స్ట్ ఎంటర్ చేయండి.")
