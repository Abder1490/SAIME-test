import streamlit as st
import json
import tempfile
import fitz
from docx import Document
from openai import OpenAI

# ─── CONFIGURATION ──────────────────────────────────────
CLE_API = st.secrets["CLE_API"]
client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=CLE_API)

# ─── FONCTIONS ──────────────────────────────────────────
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

# ─── INTERFACE ──────────────────────────────────────────
st.set_page_config(page_title="SAIME HEC", layout="wide")
st.title("🎓 SAIME")

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
            
            # Prompt ordonné de manière stricte
            prompt = f"""Tu es l'IA SAIME de HEC Montréal. Analyse l'équivalence entre le cours HEC et le cours partenaire.
            COURS CIBLE: {cours_hec}
            TEXTE HEC: {t_h[:3000]}
            TEXTE PARTENAIRE: {t_p[:3000]}
            
            INSTRUCTIONS STRICTES:
            1. NE PRENDS PAS EN COMPTE les codes techniques (ex: 3-0-1-...) comme étant des crédits ou des unités.
            2. Si une information est absente d'un document, écris exactement "Information manquante".
            3. Respecte rigoureusement les options imposées pour les champs énumérés ci-dessous.

            Génère un objet JSON unique contenant EXCLUSIVEMENT les clés suivantes dans cet ordre exact :
            - "code_cours_partenaire": [code extrait ou "Information manquante"]
            - "etablissement": [nom de l'établissement ou "Information manquante"]
            - "titre_du_cours": [titre exact du cours partenaire ou "Information manquante"]
            - "langue": [Français / Anglais / Espagnol / Autre / "Information manquante"]
            - "credits": [valeur numérique ou "Information manquante"]
            - "unite": [ECTS / UDC / Heures / "Information manquante"]
            - "cours_hec_vise": "{cours_hec}"
            - "pourcentage_equivalence": [nombre entier entre 0 et 100]
            - "statut": [Équivalent / Non équivalent / Non éligible / Info manquante / En attente]
            - "ecarts_themes_manquants": [Liste de chaînes de caractères. Si aucun écart, mettre une liste vide []]
            - "approche_pedagogique": [Format strict: "Compatible — [justification]" ou "Non compatible — [justification]" ou "Information manquante"]
            - "cohorte_version": [si applicable, sinon "Information manquante"]
            - "commentaires": [note pour le validateur en 2-3 phrases]
            """
            
            res = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            data = json.loads(res.choices[0].message.content)
            
            tab1, tab2 = st.tabs(["📌 Résultat de l'évaluation", "⚙️ Données brutes (JSON)"])
            
            with tab1:
                st.markdown(f"""
**CODE COURS PARTENAIRE :** {data.get('code_cours_partenaire', 'Information manquante')}  
**ÉTABLISSEMENT :** {data.get('etablissement', 'Information manquante')}  
**TITRE DU COURS :** {data.get('titre_du_cours', 'Information manquante')}  
**LANGUE :** {data.get('langue', 'Information manquante')}  
**CRÉDITS :** {data.get('credits', 'Information manquante')}  
**UNITÉ :** {data.get('unite', 'Information manquante')}  
**COURS HEC VISÉ :** {data.get('cours_hec_vise', cours_hec)}  
**% ÉQUIVALENCE :** {data.get('pourcentage_equivalence', 0)}%  
**STATUT :** {data.get('statut', 'Information manquante')}  
""")
                
                st.markdown("**ÉCARTS / THÈMES MANQUANTS :**")
                ecarts = data.get('ecarts_themes_manquants', [])
                if ecarts:
                    for ecart in ecarts:
                        st.markdown(f"- {ecart}")
                else:
                    st.markdown("- Aucun écart identifié")
                
                st.markdown(f"""
**APPROCHE PÉDAGOGIQUE :** {data.get('approche_pedagogique', 'Information manquante')}  
**COHORTE / VERSION :** {data.get('cohorte_version', 'Information manquante')}  
**COMMENTAIRES :** {data.get('commentaires', 'Information manquante')}
""")
            
            with tab2:
                st.json(data)
                st.download_button(
                    label="📥 Télécharger le rapport JSON",
                    data=json.dumps(data, indent=4, ensure_ascii=False),
                    file_name="resultat_equivalence.json",
                    mime="application/json"
                )
    else:
        st.error("Veuillez remplir tous les champs.")
