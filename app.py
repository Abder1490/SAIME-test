import streamlit as st
import json
import tempfile
import fitz  # PyMuPDF
from docx import Document
from openai import OpenAI

# ─── CONFIGURATION ──────────────────────────────────────
# Assurez-vous que CLE_API est dans vos secrets Streamlit Cloud
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

# ─── PROMPT ──────────────────────────────────────────────
def construire_prompt(texte_hec, texte_p, cours_hec_nom):
    return f"""Tu es l'IA SAIME de HEC Montréal. Analyse l'équivalence.
COURS CIBLE: {cours_hec_nom}
TEXTE HEC: {texte_hec[:3000]}
TEXTE PARTENAIRE: {texte_p[:3000]}

Réponds UNIQUEMENT en JSON avec ces clés :
"titre_partenaire", "etablissement", "credits", "unite", "pourcentage", "statut", "analyse_detaillee", "ecarts" (liste).
"""

# ─── INTERFACE STREAMLIT ─────────────────────────────────
st.set_page_config(page_title="SAIME HEC", layout="wide")

st.title("🎓 SAIME")
st.markdown("### Analyse des équivalences de cours")

col1, col2 = st.columns(2)
with col1:
    cours_hec = st.text_input("📚 Cours HEC de référence", "COMP 10903 - Comptabilité financière")
    f_hec = st.file_uploader("Téléverser le Plan HEC", type=["pdf", "docx"])
with col2:
    f_p = st.file_uploader("🌎 Plan(s) de cours partenaire(s)", type=["pdf", "docx"])

if st.button("🚀 LANCER L'ANALYSE"):
    if f_hec and f_p:
        with st.spinner("Analyse en cours..."):
            t_h = lire_document(sauver_temp(f_hec))
            t_p = lire_document(sauver_temp(f_p))
            
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": construire_prompt(t_h, t_p, cours_hec)}],
                response_format={"type": "json_object"}
            )
            data = json.loads(res.choices[0].message.content)
            
            # --- AFFICHAGE NÉCÉSSAIRE (Markdown simple) ---
            st.markdown("---")
            st.subheader("📌 Résultat de l'évaluation")
            st.markdown(f"""
- **CODE COURS PARTENAIRE :** {data.get('titre_partenaire', 'N/A')}
- **ÉTABLISSEMENT :** {data.get('etablissement', 'N/A')}
- **CRÉDITS :** {data.get('credits', 'N/A')}
- **UNITÉ :** {data.get('unite', 'N/A')}
- **COURS HEC VISÉ :** {cours_hec}
- **% ÉQUIVALENCE :** {data.get('pourcentage', 0)}%
- **STATUT :** {data.get('statut', 'N/A')}
- **ANALYSE :** {data.get('analyse_detaillee', 'N/A')}
""")
            st.markdown("**ÉCARTS / THÈMES MANQUANTS :**")
            for ecart in data.get('ecarts', []):
                st.markdown(f"- {ecart}")
    else:
        st.error("Veuillez téléverser les documents nécessaires.")
