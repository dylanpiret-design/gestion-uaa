import streamlit as st
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import unicodedata
import time
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
import os

# --- CONFIGURATION ---
NOM_OPTION = "Electricien(ne) de maintenance industrielle"
DOMAIN_ECOLE = "@cnddinant.be"
LOGO_PATH = "logo.png"

# Programme
PROGRAMME = {
    "4TQEMI": {
        "UAA 1": "Remplacer des composants électriques défectueux dans la partie opérative des machines de production et hors tableau, et les régler"
    },
    "5TQEMI": {
        "UAA 2": "Remplacer des éléments électriques défectueux dans les tableaux par des éléments équivalents et les régler",
        "UAA 3": "Remplacer des composants mécanique, électrique, électropneumatique et électrohydraulique par des composants équivalents et les régler"
    },
    "6TQEMI": {
        "UAA 4": "Modifier une installation pluritechnologique à prédominance électrique sur base de données directrices",
        "UAA 5": "Effectuer la maintenance préventive d’une installation pluritechnologique pour le champ d'intervention de l’électricien",
        "UAA 6": "Diagnostiquer un dysfonctionnement sur la partie électrique, hydraulique et pneumatique d’une installation pluritechnologique"
    }
}

# Configuration des Open Badges (Badgecraft)
BADGES_CONFIG = {
    "UAA1_SI1": {"titre": "UAA1 SI1", "lien": "https://www.badgecraft.eu/fr/wallet/claim?code=bvcshf", "image": "logo_UAA1_SI1.png"},
    "UAA1_SI2": {"titre": "UAA1 SI2", "lien": "https://www.badgecraft.eu/fr/wallet/claim?code=7kisig", "image": "logo_UAA1_SI2.png"},
    "UAA1_SI3": {"titre": "UAA1 SI3", "lien": "https://www.badgecraft.eu/fr/wallet/claim?code=8nvn99", "image": "logo_UAA1_SI3.png"},
    "UAA1_SI4": {"titre": "UAA1 SI4", "lien": "https://www.badgecraft.eu/fr/wallet/claim?code=4kx8cy", "image": "logo_UAA1_SI4.png"},
    "UAA1_SI5": {"titre": "UAA1 SI5", "lien": "https://www.badgecraft.eu/fr/wallet/claim?code=mzphq6", "image": "logo_UAA1_SI5.png"},
    "UAA1_FINAL": {"titre": "UAA 1", "lien": "https://www.badgecraft.eu/fr/wallet/claim?code=h5vr9v", "image": "logo_UAA1.png"}
}

# --- FONCTIONS UTILITAIRES ---

def clean_text(text):
    return str(text).encode('latin-1', 'replace').decode('latin-1')

def normalize_email_text(text):
    text = unicodedata.normalize('NFD', str(text))
    text = "".join([c for c in text if unicodedata.category(c) != 'Mn'])
    text = text.lower().strip()
    text = text.replace(" ", ".").replace("'", "").replace("..", ".")
    return text

def get_latest_results(df_eleve):
    if df_eleve.empty: return df_eleve
    df_eleve = df_eleve.copy()
    df_eleve['Date_Epreuve'] = pd.to_datetime(df_eleve['Date_Epreuve'], errors='coerce')
    df_sorted = df_eleve.sort_values(by="Date_Epreuve", ascending=False)
    df_latest = df_sorted.drop_duplicates(subset=["Code_UAA"], keep="first")
    return df_latest.sort_values(by="Code_UAA")

def colorer_lignes(row):
    if 'Réussite' in str(row['Resultat']):
        return ['background-color: #d4edda; color: #155724'] * len(row)
    elif 'Echec' in str(row['Resultat']):
        return ['background-color: #f8d7da; color: #721c24'] * len(row)
    return [''] * len(row)

def get_student_substeps(df, nom_eleve):
    state = {"UAA1_SI1": False, "UAA1_SI2": False, "UAA1_SI3": False, "UAA1_SI4": False, "UAA1_SI5": False}
    if df.empty or not nom_eleve: return state
    df_eleve = df[df["Nom_Prenom"] == nom_eleve]
    for col in state.keys():
        if col in df_eleve.columns and (df_eleve[col] == "Oui").any():
            state[col] = True
    return state

# --- GESTION DES DONNÉES GOOGLE SHEETS ---

def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        # On utilise "Data" comme dans ton code original
        df = conn.read(worksheet="Data", ttl=0)
        if df.empty:
             return pd.DataFrame(columns=["Nom_Prenom", "Classe", "Code_UAA", "Description_UAA", "Date_Epreuve", "Resultat", "Statut", "UAA1_SI1", "UAA1_SI2", "UAA1_SI3", "UAA1_SI4", "UAA1_SI5"])
        df = df.dropna(how="all")
        df['Date_Epreuve'] = pd.to_datetime(df['Date_Epreuve'], errors='coerce')
        if 'Statut' not in df.columns: df['Statut'] = 'Actif'
        else: df['Statut'] = df['Statut'].fillna('Actif')
        return df
    except Exception:
        return pd.DataFrame()

def save_data(df):
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_to_save = df.copy()
    colonnes_obligatoires = ["Nom_Prenom", "Classe", "Code_UAA", "Description_UAA", "Date_Epreuve", "Resultat", "Statut", 
                             "UAA1_SI1", "UAA1_SI2", "UAA1_SI3", "UAA1_SI4", "UAA1_SI5"]
    for col in colonnes_obligatoires:
        if col not in df_to_save.columns:
            df_to_save[col] = ""
    df_to_save = df_to_save[colonnes_obligatoires]
    df_to_save = df_to_save.fillna("")
    df_to_save = df_to_save.astype(str)
    try:
        conn.update(worksheet="Data", data=df_to_save)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Erreur d'écriture Google Sheets : {e}")
        st.stop()

# --- CLASSE PDF & MAILS ---

class PDF(FPDF):
    def header(self):
        try: self.image(LOGO_PATH, x=10, y=8, w=30)
        except: pass 
        self.ln(20)
    def footer(self):
        self.set_y(-55)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(2)
        self.set_font("Arial", 'B', 8)
        self.cell(0, 4, clean_text("Rappel du cursus complet (UAA) :"), 0, 1, 'L')
        self.set_font("Arial", 'I', 7)
        self.set_text_color(80, 80, 80)
        for annee, uaas in PROGRAMME.items():
            for code, desc in uaas.items():
                desc_courte = desc[:110] + "..." if len(desc) > 110 else desc
                self.cell(0, 3.5, clean_text(f"[{annee}] {code} : {desc_courte}"), 0, 1, 'L')
        self.set_y(-10)
        self.set_font("Arial", 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_pdf(nom_eleve, df_eleve_filtered):
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_y(30)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, clean_text(f"Suivi des UAA - {nom_eleve}"), ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 10, clean_text(f"Date : {datetime.now().strftime('%d/%m/%Y')}"), ln=True)
    pdf.ln(2)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 9)
    col_w = [15, 15, 115, 20, 25]
    for h, w in zip(["Annee", "UAA", "Description", "Resultat", "Date"], col_w):
        pdf.cell(w, 10, clean_text(h), 1, 0, 'C', 1)
    pdf.ln()
    pdf.set_font("Arial", '', 8)
    for _, row in df_eleve_filtered.iterrows():
        pdf.cell(col_w[0], 10, clean_text(str(row['Classe'])[:3]), 1)
        pdf.cell(col_w[1], 10, clean_text(row['Code_UAA']), 1)
        pdf.cell(col_w[2], 10, clean_text(row['Description_UAA'][:75]), 1)
        res = "Acquis" if "Réussite" in str(row['Resultat']) else "Non Acquis"
        pdf.cell(col_w[3], 10, clean_text(res), 1)
        d_s = row['Date_Epreuve'].strftime('%d/%m/%Y') if hasattr(row['Date_Epreuve'], 'strftime') else str(row['Date_Epreuve'])[:10]
        pdf.cell(col_w[4], 10, d_s, 1, 1)
    return pdf.output(dest='S').encode('latin-1')

def send_email_wrapper(destinataires_list, sujet, corps, pdf_bytes=None, pdf_name=None):
    try:
        email_exp = st.secrets["email"]["EMAIL_EXPEDITEUR"]
        mdp_exp = st.secrets["email"]["MOT_DE_PASSE_EMAIL"]
        msg = MIMEMultipart()
        msg['From'] = email_exp
        msg['To'] = ", ".join(destinataires_list)
        msg['Subject'] = sujet
        msg.attach(MIMEText(corps, 'plain', 'utf-8'))
        if pdf_bytes:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(pdf_bytes)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {pdf_name}")
            msg.attach(part)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_exp, mdp_exp)
        server.sendmail(email_exp, destinataires_list, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erreur mail : {e}")
        return False

def send_badge_email(email_dest, nom_eleve, badge_key):
    badge = BADGES_CONFIG[badge_key]
    sujet = f"🏆 Badge débloqué : {badge['titre']}"
    corps = f"Bravo {nom_eleve} !\n\nTu as validé une étape. Voici ton badge :\n👉 {badge['lien']}"
    return send_email_wrapper([email_dest], sujet, corps)

# --- UI ---
st.set_page_config(page_title="Encodage UAA", page_icon="⚡", layout="wide")

if "authenticated" not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Connexion")
    pwd = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if pwd == st.secrets.get("general", {}).get("MOT_DE_PASSE_APP", "admin"):
            st.session_state.authenticated = True
            st.rerun()
else:
    st.sidebar.image(LOGO_PATH, use_container_width=True)
    page_actuelle = st.sidebar.radio("Navigation", ["📝 Encodage", "📊 Dashboard", "📧 Bulletins", "⚙️ Admin"])
    
    df = load_data()
    df_actifs = df[df["Statut"] != "Archivé"] if not df.empty else pd.DataFrame()
    existing_students = sorted(df_actifs["Nom_Prenom"].unique().tolist()) if not df_actifs.empty else []

    if page_actuelle == "📝 Encodage":
        st.subheader("📝 Nouvel encodage")
        mode = st.radio("Élève", ["Existant", "Nouveau"], horizontal=True)
        nom_eleve = st.selectbox("Choisir", existing_students) if mode == "Existant" else st.text_input("Nom Prénom")
        
        c1, c2 = st.columns(2)
        classe = c1.selectbox("Année", list(PROGRAMME.keys()))
        code_choisi = c2.selectbox("UAA", list(PROGRAMME[classe].keys()))
        desc = PROGRAMME[classe][code_choisi]
        st.info(f"**Compétence :** {desc}")

        val_si = {}
        current_si = get_student_substeps(df, nom_eleve)
        
        if code_choisi == "UAA 1" and nom_eleve:
            st.markdown("### 🏅 Sous-étapes (Badges SI)")
            cols = st.columns(5)
            for i in range(1, 6):
                key = f"UAA1_SI{i}"
                val_si[key] = cols[i-1].checkbox(f"SI {i}", value=current_si[key], disabled=current_si[key])

        # --- VERROU ---
        pret_uaa1 = all(val_si[k] or current_si[k] for k in val_si) if code_choisi == "UAA 1" else True
        
        c3, c4 = st.columns(2)
        date_ep = c3.date_input("Date", datetime.today())
        
        if code_choisi == "UAA 1" and not pret_uaa1:
            st.warning("⚠️ Complétez les 5 SI pour valider l'UAA 1.")
            res = c4.radio("Résultat", ["En cours"], disabled=True)
        else:
            res = c4.radio("Résultat", ["En cours", "Réussite (Acquis)", "Echec (Non Acquis)"], horizontal=True)

        if st.button("💾 Sauvegarder", type="primary"):
            if nom_eleve:
                email_eleve = normalize_email_text(nom_eleve) + DOMAIN_ECOLE
                new_row = {"Nom_Prenom": nom_eleve, "Classe": classe, "Code_UAA": code_choisi, "Description_UAA": desc, "Date_Epreuve": pd.to_datetime(date_ep), "Resultat": res, "Statut": "Actif"}
                
                if code_choisi == "UAA 1":
                    for k, v in val_si.items():
                        new_row[k] = "Oui" if (v or current_si[k]) else ""
                        if v and not current_si[k]: send_badge_email(email_eleve, nom_eleve, k)
                    if res == "Réussite (Acquis)": send_badge_email(email_eleve, nom_eleve, "UAA1_FINAL")
                
                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df)
                st.success("Enregistré !")
                time.sleep(1)
                st.rerun()

    elif page_actuelle == "📊 Dashboard":
        st.subheader("📊 Dashboard")
        if not df_actifs.empty:
            sel_eleve = st.selectbox("Élève", ["Tous"] + existing_students)
            if sel_eleve != "Tous":
                st.markdown(f"### Badges de {sel_eleve}")
                states = get_student_substeps(df, sel_eleve)
                uaa1_ok = not df[(df["Nom_Prenom"] == sel_eleve) & (df["Code_UAA"] == "UAA 1") & (df["Resultat"].str.contains("Réussite"))].empty
                states["UAA1_FINAL"] = uaa1_ok
                cols = st.columns(6)
                for i, (k, info) in enumerate(BADGES_CONFIG.items()):
                    with cols[i]:
                        if states.get(k):
                            if os.path.exists(info["image"]): st.image(info["image"], caption=info["titre"])
                            else: st.success(f"✅ {info['titre']}")
                        else: st.markdown(f"<div style='text-align:center;font-size:30px;filter:grayscale(1);'>🔒<br><span style='font-size:10px;'>{info['titre']}</span></div>", unsafe_allow_html=True)
            st.dataframe(df_actifs[["Nom_Prenom", "Classe", "Code_UAA", "Resultat", "Date_Epreuve"]].sort_values("Date_Epreuve", ascending=False), use_container_width=True)

    elif page_actuelle == "📧 Bulletins":
        st.subheader(" Bulletins")
        eleve = st.selectbox("Élève", existing_students)
        if eleve:
            df_b = get_latest_results(df[df["Nom_Prenom"] == eleve])
            pdf = generate_pdf(eleve, df_b)
            st.download_button("⬇️ Télécharger", pdf, f"Bulletin_{eleve}.pdf")

    elif page_actuelle == "⚙️ Admin":
        st.subheader("⚙️ Admin")
        if st.checkbox("Base brute"): st.write(df)
        if st.button("Archiver"):
            e_arc = st.selectbox("Qui ?", existing_students)
            df.loc[df["Nom_Prenom"] == e_arc, "Statut"] = "Archivé"
            save_data(df)
            st.rerun()
