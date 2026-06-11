import streamlit as st
import json
import os
import tempfile
import fitz  # PyMuPDF
from docx import Document
from openai import OpenAI

# ─── CONFIGURATION ──────────────────────────────────────
import streamlit as st
CLE_API = st.secrets["CLE_API"]
client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=CLE_API)

# ─── FONCTIONS LOGIQUES (Extraction) ────────────────────────
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

# ─── PROMPT AMÉLIORÉ (Formatage propre) ────────────────────
def construire_prompt(texte_hec, texte_p, cours_hec_nom):
    return f"""Tu es un expert HEC. Analyse l'équivalence.
COURS CIBLE: {cours_hec_nom}
TEXTE HEC: {texte_hec[:3000]}
TEXTE PARTENAIRE: {texte_p[:3000]}

Réponds UNIQUEMENT en JSON avec une clé "resultat" contenant le texte formaté comme suit (utilise des tirets pour les listes) :
**CODE COURS PARTENAIRE :** ...
**ÉTABLISSEMENT :** ...
**TITRE DU COURS :** ...
**LANGUE :** ...
**CRÉDITS :** ...
**UNITÉ :** ...
**COURS HEC VISÉ :** ...
**% ÉQUIVALENCE :** ...
**STATUT :** ...
**ÉCARTS / THÈMES MANQUANTS :**
- Thème 1
- Thème 2
**APPROCHE PÉDAGOGIQUE :** ...
**COHORTE / VERSION :** ...
**COMMENTAIRES :** ...
"""

# ─── INTERFACE MODERNE (UI) ────────────────────────────────
st.set_page_config(page_title="SAIME", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #e1e4e8; }
    </style>
""", unsafe_allow_html=True)

st.title("🎓 SAIME")
st.subheader("Système d'analyse des équivalences")

with st.container():
    c1, c2 = st.columns(2)
    cours_hec = c1.text_input("Cours HEC visé", "COMP 10903 - Comptabilité financière")
    f_hec = c1.file_uploader("Fichier HEC", type=["pdf", "docx"])
    f_p = c2.file_uploader("Fichier Partenaire", type=["pdf", "docx"])

if st.button("🚀 Analyser l'équivalence", type="primary"):
    if f_hec and f_p:
        with st.spinner("Analyse approfondie en cours..."):
            t_h = lire_document(sauver_temp(f_hec))
            t_p = lire_document(sauver_temp(f_p))
            
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": construire_prompt(t_h, t_p, cours_hec)}],
                response_format={"type": "json_object"}
            )
            data = json.loads(res.choices[0].message.content)
            
            st.markdown("---")
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(data["resultat"])
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning("Veuillez téléverser les deux fichiers.")
