import streamlit as st
import json
import tempfile
import fitz  # PyMuPDF
from docx import Document
from openai import OpenAI

# ─── CONFIGURATION ──────────────────────────────────────
# Récupération de la clé depuis les secrets Streamlit
CLE_API = st.secrets["CLE_API"]
client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=CLE_API)

# ─── FONCTIONS UTILITAIRES ──────────────────────────────
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

# ─── INTERFACE UTILISATEUR ──────────────────────────────
st.set_page_config(page_title="SAIME", layout="centered")

st.title("🎓 SAIME")
st.markdown("### Analyse des équivalences de cours")

# Formulaire d'entrée
cours_hec = st.text_input("Code & Titre du cours HEC visé", "COMP 10903 - Comptabilité financière")
f_hec = st.file_uploader("Téléverser le plan de cours HEC (PDF/Word)", type=["pdf", "docx"])
f_p = st.file_uploader("Téléverser le(s) plan(s) de cours partenaire(s)", type=["pdf", "docx"])

if st.button("🚀 Lancer l'analyse"):
    if f_hec and f_p:
        with st.spinner("Analyse en cours..."):
            t_h = lire_document(sauver_temp(f_hec))
            t_p = lire_document(sauver_temp(f_p))
            
            prompt = f"""Tu es un expert académique. Analyse l'équivalence entre le cours HEC et le cours partenaire.
            Cours HEC: {cours_hec}
            Contenu HEC: {t_h[:3000]}
            Contenu Partenaire: {t_p[:3000]}
            
            Réponds EXCLUSIVEMENT en format JSON avec ces clés :
            "code_partenaire", "etablissement", "titre_cours", "langue", "credits", "unite", "pourcentage", "statut", "ecarts" (liste), "approche", "version", "commentaires"
            """
            
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            data = json.loads(res.choices[0].message.content)
            
            # Affichage propre (Bullet Points)
            st.markdown("---")
            st.subheader("📌 Résultat de l'évaluation")
            st.markdown(f"""
- **CODE COURS PARTENAIRE :** {data.get('code_partenaire', 'N/A')}
- **ÉTABLISSEMENT :** {data.get('etablissement', 'N/A')}
- **TITRE DU COURS :** {data.get('titre_cours', 'N/A')}
- **LANGUE :** {data.get('langue', 'N/A')}
- **CRÉDITS :** {data.get('credits', 'N/A')}
- **UNITÉ :** {data.get('unite', 'N/A')}
- **COURS HEC VISÉ :** {cours_hec}
- **% ÉQUIVALENCE :** {data.get('pourcentage', 'N/A')}%
- **STATUT :** {data.get('statut', 'N/A')}
- **APPROCHE PÉDAGOGIQUE :** {data.get('approche', 'N/A')}
- **COHORTE / VERSION :** {data.get('version', 'N/A')}
- **COMMENTAIRES :** {data.get('commentaires', 'N/A')}

**ÉCARTS / THÈMES MANQUANTS :**
            """)
            for ecart in data.get('ecarts', []):
                st.markdown(f"- {ecart}")
                
    else:
        st.warning("Veuillez remplir le cours visé et téléverser les fichiers.")
