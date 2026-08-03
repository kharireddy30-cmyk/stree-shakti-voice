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
# 1. పేజీ సెట్టింగ్స్ & పర్మనెంట్ స్టేట్స్
# ==========================================
st.set_page_config(
    page_title="ఆధ్యాత్మిక వాయిస్ & అనువాదక యంత్రం", 
    layout="wide", 
    page_icon="🕉️"
)

st.header("🔱 ఆధ్యాత్మిక వాయిస్ & భాషా అనువాద వ్యవస్థ")
st.caption("అనువాదం, ఫైల్ ప్రొటెక్షన్, లైవ్ మైక్రోఫోన్ & ఆడియో కన్వర్షన్ - పర్ఫెక్ట్ కనెక్షన్")

# సెషన్ స్టేట్స్
if "main_text" not in st.session_state:
    st.session_state.main_text = ""
if "translated_text" not in st.session_state:
    st.session_state.translated_text = ""
if "audio_bytes_data" not in st.session_state:
    st.session_state.audio_bytes_data = None
if "last_mic_text" not in st.session_state:
    st.session_state.last_mic_text = ""


# ==========================================
# 2. కోర్ హెల్పర్ ఫంక్షన్లు
# ==========================================

async def generate_voice_file(text, voice, output_filename):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_filename)


def split_text_into_chunks(text, max_chars=300):
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


def safe_translate_text(text, target_lang_code):
    if not text or not text.strip():
        return ""
    
    paragraphs = text.split("\n")
    translated_paras = []
    translator = GoogleTranslator(source='auto', target=target_lang_code)

    for p in paragraphs:
        p_clean = p.strip()
        if p_clean:
            try:
                if len(p_clean) > 1200:
                    sub_chunks = split_text_into_chunks(p_clean, max_chars=1000)
                    sub_trans = []
                    for sc in sub_chunks:
                        if sc.strip():
                            res = translator.translate(sc)
                            if res and isinstance(res, str):
                                sub_trans.append(res)
                    translated_paras.append(" ".join(sub_trans))
                else:
                    res = translator.translate(p_clean)
                    if res and isinstance(res, str):
                        translated_paras.append(res)
                    else:
                        translated_paras.append(p_clean)
            except Exception:
                translated_paras.append(p_clean)
        else:
            translated_paras.append("")

    return "\n".join(translated_paras)


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


def translate_docx_file(uploaded_file, target_lang_code):
    doc = docx.Document(uploaded_file)
    translator = GoogleTranslator(source='auto', target=target_lang_code)

    for p in doc.paragraphs:
        if p.text.strip():
            try:
                translated_p = translator.translate(p.text)
                if translated_p and isinstance(translated_p, str):
                    p.text = translated_p
            except Exception:
                pass

    output_stream = io.BytesIO()
    doc.save(output_stream)
    output_stream.seek(0)
    return output_stream.getvalue()


# ==========================================
# 3. ఇన్‌పుట్ విభాగం (ఫైల్ అప్‌లోడ్ & మైక్రోఫోన్)
# ==========================================
st.divider()
col_file, col_mic = st.columns([0.5, 0.5])

uploaded_file = None
with col_file:
    uploaded_file = st.file_uploader("📁 మీ ఫైల్‌ను అప్‌లోడ్ చేయండి (.docx, .pdf, .txt):", type=["docx", "pdf", "txt"])
    if uploaded_file is not None:
        try:
            f_text = extract_text_from_file(uploaded_file)
            if f_text and f_text != st.session_state.main_text:
                st.session_state.main_text = f_text
                st.success(f"✅ '{uploaded_file.name}' లోడ్ అయింది!")
        except Exception as fe:
            st.error(f"ఫైల్ చదవడంలో లోపం: {fe}")

with col_mic:
    st.markdown("**🎙️ మైక్రోఫోన్ ద్వారా మాట్లాడండి (Live Voice Typing):**")
    mic_lang = st.selectbox("మాట్లాడే భాష:", options=["తెలుగు (Telugu)", "హిందీ (Hindi)", "ఇంగ్లీష్ (English)"])
    mic_code_map = {"తెలుగు (Telugu)": "te-IN", "హిందీ (Hindi)": "hi-IN", "ఇంగ్లీష్ (English)": "en-IN"}
    
    spoken_result = speech_to_text(
        start_prompt="🎙️ మాట్లాడటం ప్రారంభించండి (Start)",
        stop_prompt="⏹️ ఆపండి (Stop)",
        language=mic_code_map[mic_lang],
        use_container_width=True,
        key='perfect_mic_recorder'
    )
    
    if spoken_result and spoken_result != st.session_state.last_mic_text:
        st.session_state.main_text += " " + spoken_result
        st.session_state.last_mic_text = spoken_result
        st.rerun()

# ప్రధాన టెక్స్ట్ ఏరియా
user_input_text = st.text_area(
    "ఆడియోగా మార్చాలనుకుంటున్న టెక్స్ట్:", 
    value=st.session_state.main_text, 
    height=140
)

if user_input_text != st.session_state.main_text:
    st.session_state.main_text = user_input_text


# ==========================================
# 4. అనువాద విభాగం (Translator Section)
# ==========================================
if st.session_state.main_text.strip() or uploaded_file:
    st.markdown("##### 🌐 భాషా అనువాదం (Language Translator)")
    col_tr1, col_tr2 = st.columns([0.7, 0.3])
    
    with col_tr1:
        target_trans_lang = st.selectbox("ఏ భాషలోకి మార్చాలి?:", options=["తెలుగు (Telugu)", "హిందీ (Hindi)", "ఇంగ్లీష్ (English)"])
        lang_code_map = {"తెలుగు (Telugu)": "te", "హిందీ (Hindi)": "hi", "ఇంగ్లీష్ (English)": "en"}
        t_code = lang_code_map[target_trans_lang]

    with col_tr2:
        st.write("")
        st.write("")
        if st.button("🔄 టెక్స్ట్‌ని అనువదించు (Translate)", use_container_width=True):
            try:
                with st.spinner("అనువాదం జరుగుతోంది..."):
                    t_res = safe_translate_text(st.session_state.main_text, t_code)
                    st.session_state.translated_text = t_res
                    st.success("✅ అనువాదం పూర్తయింది! క్రింద అనువాదాన్ని చూడవచ్చు.")
            except Exception as tr_err:
                st.error(f"అనువాదంలో లోపం: {tr_err}")

    if st.session_state.translated_text:
        st.text_area("అనువాదం అయిన టెక్స్ట్ (Translated Text):", value=st.session_state.translated_text, height=120)
        
        # 🔗 కనెక్షన్ ఫిక్స్: అనువాదమైన టెక్స్ట్‌ను డైరెక్ట్‌గా ఆడియో కోసం ఎంచుకునే బటన్
        if st.button("🎯 ఈ అనువాదమైన టెక్స్ట్‌నే ఆడియోగా మార్చు (Use Translated Text for Audio)"):
            st.session_state.main_text = st.session_state.translated_text
            st.success("✅ అనువాదమైన టెక్స్ట్ ప్రధాన బాక్స్‌లోకి మార్చబడింది!")
            st.rerun()

    if uploaded_file and uploaded_file.name.endswith(".docx"):
        if st.button("📥 ఫోటోలు/సింబల్స్‌తో సహా అనువాద వర్డ్ ఫైల్ (.docx) డౌన్‌లోడ్ చేయి"):
            with st.spinner("ఫైల్ డిజైన్ మరియు ఫోటోలు పాడవకుండా అనువదిస్తోంది..."):
                trans_doc_bytes = translate_docx_file(uploaded_file, t_code)
                st.download_button(
                    label="💾 అనువాద DOCX ఫైల్ డౌన్‌లోడ్ చేయి",
                    data=trans_doc_bytes,
                    file_name=f"translated_{uploaded_file.name}",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )


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
# 6. ఆడియో జనరేషన్ (Smart Dynamic Text Connection Logic)
# ==========================================
if convert_btn:
    # 🔗 స్మార్ట్ చెకింగ్: అనువాదమైన టెక్స్ట్ ఉంటే దాన్ని లేదా సాధారణ టెక్స్ట్‌ని ఎంచుకుంటుంది
    text_to_process = ""
    if st.session_state.translated_text.strip():
        text_to_process = st.session_state.translated_text.strip()
    else:
        text_to_process = st.session_state.main_text.strip()

    if text_to_process:
        with st.spinner("ఆడియో ప్రాసెస్ అవుతోంది... దయచేసి వేచి ఉండండి..."):
            try:
                clean_txt = re.sub(r'[*#_~`]', '', text_to_process)
                
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
                speech_sound = AudioSegment.empty()

                for i, chunk in enumerate(text_chunks):
                    temp_file = f"temp_{i}.mp3"
                    try:
                        asyncio.run(generate_voice_file(chunk, selected_voice, temp_file))
                        if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                            chunk_sound = AudioSegment.from_file(temp_file)
                            speech_sound += chunk_sound
                            os.remove(temp_file)
                    except Exception:
                        pass

                if len(speech_sound) > 0:
                    final_sound = speech_sound
                    if os.path.exists("bgm.mp3"):
                        try:
                            bgm_sound = AudioSegment.from_file("bgm.mp3")
                            if len(bgm_sound) < len(speech_sound):
                                bgm_sound = bgm_sound * ((len(speech_sound) // len(bgm_sound)) + 1)
                            bgm_sound = bgm_sound[:len(speech_sound)] - 15
                            final_sound = speech_sound.overlay(bgm_sound)
                        except Exception:
                            pass

                    final_fp = io.BytesIO()
                    final_sound.export(final_fp, format="mp3")
                    st.session_state.audio_bytes_data = final_fp.getvalue()
                    st.success("🎉 ఆడియో విజయవంతంగా సిద్ధమైంది!")
                else:
                    st.error("❌ ఆడియో డేటా ఏదీ జనరేట్ కాలేదు!")

            except Exception as e:
                st.error("❌ ఆడియో సిస్టమ్‌లో లోపం వచ్చింది:")
                st.code(traceback.format_exc())
    else:
        st.warning("దయచేసి టెక్స్ట్ ఎంటర్ చేయండి లేదా మాట్లాడండి.")

# 📥 స్థిరమైన డిస్‌ప్లే
if st.session_state.audio_bytes_data is not None:
    st.divider()
    st.audio(st.session_state.audio_bytes_data, format="audio/mp3")
    st.download_button(
        label="📥 MP3 ఆడియో ఫైల్‌ని డౌన్‌లోడ్ చేయండి", 
        data=st.session_state.audio_bytes_data, 
        file_name="spiritual_audio.mp3", 
        mime="audio/mp3",
        key="permanent_download_btn"
    )
