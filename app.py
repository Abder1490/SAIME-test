import streamlit as st
import json
import os
import tempfile
import fitz  # PyMuPDF
from docx import Document
from openai import OpenAI

# ─── CONFIGURATION ──────────────────────────────────────
# Assurez-vous que CLE_API est bien dans vos secrets Streamlit Cloud
CLE_API = st.secrets["CLE_API"]
client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=CLE_API)

# ─── FONCTIONS LOGIQUES ──────────────────────────────────
def lire_document(chemin):
    if chemin.lower().endswith(".pdf"):
        doc = fitz.open(chemin)
        return "\n".join(page.get_text() for page in doc)
    doc = Document(chemin)
    return "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])

def sauver_temp(f):
    suffix = "." + f.name.split(".")[-1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(f.read())
    tmp.close()
    return tmp.name

# ─── DESIGN & UI COMPONENT ───────────────────────────────
def render_report(data):
    """Génère un rapport HTML ultra-pro pour l'utilisateur final"""
    pct = data.get("pourcentage", 0)
    statut = data.get("statut", "En attente")
    color = "#26d07c" if "Équivalent" in statut else "#ff585d" if "Non" in statut else "#f3d03e"
    
    html = f"""
    <div style="background: white; padding: 30px; border-radius: 15px; border-left: 10px solid #002855; box-shadow: 0 10px 30px rgba(0,0,0,0.1); font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <h2 style="margin: 0; color: #002855;">📄 Rapport d'Équivalence</h2>
            <span style="background: {color}; color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 14px;">{statut.upper()}</span>
        </div>
        
        <div style="background: #f8fafc; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
            <p style="margin: 5px 0;"><strong>Cours Partenaire :</strong> {data.get('titre_partenaire', 'N/A')}</p>
            <p style="margin: 5px 0;"><strong>Établissement :</strong> {data.get('etablissement', 'N/A')}</p>
            <p style="margin: 5px 0;"><strong>Crédits :</strong> {data.get('credits', 'N/A')} ({data.get('unite', 'N/A')})</p>
        </div>

        <div style="margin-bottom: 25px;">
            <p style="margin-bottom: 10px; font-weight: bold; color: #002855;">Indice de correspondance : {pct}%</p>
            <div style="background: #e2e8f0; border-radius: 10px; height: 12px; width: 100%;">
                <div style="background: linear-gradient(90deg, #002855, #00aec7); width: {pct}%; height: 100%; border-radius: 10px;"></div>
            </div>
        </div>

        <h3 style="color: #002855; border-bottom: 2px solid #eee; padding-bottom: 10px;">🔍 Analyse du Contenu</h3>
        <p style="line-height: 1.6;">{data.get('analyse_detaillee', '')}</p>
        
        <div style="margin-top: 20px; padding: 15px; background: #fff5f5; border-radius: 10px; border: 1px solid #fed7d7;">
            <strong style="color: #c53030;">⚠️ Écarts identifiés :</strong>
            <ul style="margin-top: 10px; color: #c53030;">
                {"".join([f"<li>{item}</li>" for item in data.get('ecarts', [])])}
            </ul>
        </div>
        
        <div style="margin-top: 20px; font-style: italic; color: #64748b; font-size: 13px;">
            Note : Cette analyse a été générée par l'IA SAIME pour support à la décision.
        </div>
    </div>
    """
    return html

# ─── PROMPT ──────────────────────────────────────────────
def construire_prompt(texte_hec, texte_p, cours_hec_nom):
    return f"""Tu es l'IA SAIME de HEC Montréal. Analyse l'équivalence.
COURS CIBLE: {cours_hec_nom}
TEXTE HEC: {texte_hec[:3000]}
TEXTE PARTENAIRE: {texte_p[:3000]}

Réponds UNIQUEMENT en JSON avec ces clés :
"titre_partenaire", "etablissement", "credits", "unite", "pourcentage" (nombre), "statut", "analyse_detaillee", "ecarts" (liste).
"""

# ─── INTERFACE STREAMLIT ─────────────────────────────────
st.set_page_config(page_title="SAIME HEC", layout="wide")

# CSS Custom pour cacher les éléments Streamlit "moches" et embellir
st.markdown("""
    <style>
    .main { background: #f0f2f6; }
    .stButton>button { background: #002855; color: white; border-radius: 12px; height: 3em; font-weight: bold; border: none; transition: 0.3s; }
    .stButton>button:hover { background: #00aec7; transform: translateY(-2px); }
    .upload-card { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.title("🎓 SAIME")
st.markdown("### Interface d'Analyse Intelligente des Équivalences")

with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="upload-card">', unsafe_allow_html=True)
        cours_hec = st.text_input("📚 Cours HEC de référence", "COMP 10903 - Comptabilité financière")
        f_hec = st.file_uploader("Téléverser le Plan HEC", type=["pdf", "docx"])
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="upload-card">', unsafe_allow_html=True)
        st.write("") # Spacer
        st.write("") 
        f_p = st.file_uploader("🌎 Plan(s) de cours partenaire(s)", type=["pdf", "docx"])
        st.markdown('</div>', unsafe_allow_html=True)

if st.button("🚀 LANCER L'ANALYSE"):
    if f_hec and f_p:
        with st.spinner("Analyse des concepts pédagogiques en cours..."):
            t_h = lire_document(sauver_temp(f_hec))
            t_p = lire_document(sauver_temp(f_p))
            
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": construire_prompt(t_h, t_p, cours_hec)}],
                response_format={"type": "json_object"}
            )
            data = json.loads(res.choices[0].message.content)
            
            st.markdown(render_report(data), unsafe_allow_html=True)
    else:
        st.error("Veuillez téléverser les documents nécessaires.")
