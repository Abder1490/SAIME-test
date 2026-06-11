import streamlit as st
import json
import os
import tempfile
import fitz  # PyMuPDF
from docx import Document
from datetime import date
from openai import OpenAI

# ─── CONFIGURATION BACK-END ──────────────────────────────────────
# Clé API Groq (Back-end seulement, invisible pour l'utilisateur)
CLE_API = "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" 

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=CLE_API
)

# ─── LOGIQUE D'EXTRACTION ────────────────────────────────────────

def lire_word(chemin):
    doc = Document(chemin)
    texte = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    for tab in doc.tables:
        for row in tab.rows:
            texte.append(" ".join(c.text.strip() for c in row.cells))
    return "\n".join(texte)

def lire_pdf(chemin):
    doc = fitz.open(chemin)
    return "\n".join(page.get_text() for page in doc)

def lire_document(chemin):
    if chemin.lower().endswith(".pdf"): return lire_pdf(chemin)
    return lire_word(chemin)

def sauver_temp(f):
    suffix = "." + f.name.split(".")[-1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(f.read())
    tmp.close()
    return tmp.name

# ─── PROMPT ET ANALYSE ───────────────────────────────────────────

def construire_prompt(texte_hec, liste_partenaires, cours_hec_nom):
    docs_p = "\n".join([f"DOC {i+1} ({n}): {t[:3000]}" for i, (n, t) in enumerate(liste_partenaires)])
    return f"""Tu es un expert académique pour HEC Montréal. Analyse l'équivalence.
COURS CIBLE HEC : {cours_hec_nom}
CONTENU HEC : {texte_hec[:3000]}
PLANS PARTENAIRES : {docs_p}

Réponds UNIQUEMENT en JSON avec :
1. "bullet_points" : un texte formaté EXACTEMENT selon ce modèle :
**CODE COURS PARTENAIRE :** [valeur]
**ÉTABLISSEMENT :** [valeur]
**TITRE DU COURS :** [valeur]
**LANGUE :** [valeur]
**CRÉDITS :** [valeur]
**UNITÉ :** [valeur]
**COURS HEC VISÉ :** {cours_hec_nom}
**% ÉQUIVALENCE :** [nombre]%
**STATUT :** [Équivalent/Non équivalent/etc.]
**ÉCARTS / THÈMES MANQUANTS :**
- [thème 1]
**APPROCHE PÉDAGOGIQUE :** [valeur]
**COHORTE / VERSION :** [valeur]
**COMMENTAIRES :** [2-3 phrases]

2. "json_sharepoint" : l'objet structuré correspondant.
"""

# ─── INTERFACE (UX AMÉLIORÉE) ────────────────────────────────────

st.set_page_config(page_title="SAIME — HEC Montréal", layout="wide")

# CSS pour le bleu HEC et clean UI
st.markdown("""
    <style>
    .stApp { background-color: #002855; color: white; }
    .stMarkdown, p, h1, h2, h3, label { color: white !important; }
    div.stButton > button { width: 100%; background-color: #003DA5; color: white; border: 1px solid white; }
    .result-box { background-color: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; border: 1px solid #00aec7; }
    </style>
""", unsafe_allow_html=True)

# En-tête sans erreur d'image
col_l, col_t = st.columns([1, 5])
with col_l: st.markdown('<div style="font-size:35px;">🎓</div>', unsafe_allow_html=True)
with col_t: st.title("SAIME — HEC Montréal")

st.divider()

c1, c2 = st.columns(2)
with c1:
    hec_nom = st.text_input("Code & Titre HEC", value="COMP 10903 - Comptabilité financière")
    f_hec = st.file_uploader("Plan HEC", type=["pdf", "docx"])
with c2:
    f_p = st.file_uploader("Plan(s) Partenaire(s)", type=["pdf", "docx"], accept_multiple_files=True)

if f_hec and f_p:
    if st.button("🔍 Lancer l'analyse intelligente", type="primary"):
        try:
            with st.status("Analyse en cours...", expanded=True) as s:
                s.write("Lecture des fichiers...")
                t_h = lire_document(sauver_temp(f_hec))
                t_ps = [(f.name, lire_document(sauver_temp(f))) for f in f_p]
                
                s.write("IA en action...")
                res = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": construire_prompt(t_h, t_ps, hec_nom)}],
                    response_format={"type": "json_object"}
                )
                data = json.loads(res.choices[0].message.content)
                s.update(label="Analyse complétée !", state="complete")
            
            t1, t2 = st.tabs(["📌 Résultat de l'analyse", "⚙️ Format SharePoint"])
            with t1:
                st.markdown(f'<div class="result-box">{data["bullet_points"]}</div>', unsafe_allow_html=True)
            with t2:
                st.json(data["json_sharepoint"])
        except Exception as e:
            st.error(f"Erreur : {e}")