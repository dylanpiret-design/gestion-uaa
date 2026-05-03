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

# --- CONFIGURATION ---
NOM_OPTION = "Electricien(ne) de maintenance industrielle"
DOMAIN_ECOLE = "@cnddinant.be"
LOGO_PATH = "logo.png"

# Configuration GitHub automatique pour les images des badges
GITHUB_COMPTE = "dylanpiret-design" 
GITHUB_REPO = "gestion-uaa"
GITHUB_BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_COMPTE}/{GITHUB_REPO}/main/"

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

# --- BADGES UAA1 ---
BADGES_UAA1 = {
    "UAA1_SI1": {
        "url": "https://www.badgecraft.eu/fr/wallet/claim?code=bvcshf", 
        "nom": "SI1 : Préparation de l'intervention de maintenance", 
        "img": GITHUB_BASE_URL + "logo_UAA1_SI1.png"
    },
    "UAA1_SI2": {
        "url": "https://www.badgecraft.eu/fr/wallet/claim?code=7kisig", 
        "nom": "SI2 : LMRA - Consignation - Déconsignation", 
        "img": GITHUB_BASE_URL + "logo_UAA1_SI2.png"
    },
    "UAA1_SI3": {
        "url": "https://www.badgecraft.eu/fr/wallet/claim?code=8nvn99", 
        "nom": "SI3 : Remplacement d'un composant électrique + règles de sécurité / ergonomiques / environnementales", 
        "img": GITHUB_BASE_URL + "logo_UAA1_SI3.png"
    },
    "UAA1_SI4": {
        "url": "https://www.badgecraft.eu/fr/wallet/claim?code=4kx8cy", 
        "nom": "SI4 : Remise en service et réglage", 
        "img": GITHUB_BASE_URL + "logo_UAA1_SI4.png"
    },
    "UAA1_SI5": {
        "url": "https://www.badgecraft.eu/fr/wallet/claim?code=mzphq6", 
        "nom": "SI5 : Clôture de l'intervention", 
        "img": GITHUB_BASE_URL + "logo_UAA1_SI5.png"
    }
}
LIEN_UAA1 = "https://www.badgecraft.eu/fr/wallet/claim?code=h5vr9v"
IMG_UAA1 = GITHUB_BASE_URL + "logo_UAA1.png"

# --- BADGES UAA2 ---
BADGES_UAA2 = {
    "UAA2_SI1": {
        "url": "https://www.badgecraft.eu/auto/wallet/claim?code=gjt4f6&qr=1", 
        "nom": "SI1 : Préparation de l'intervention de maintenance", 
        "img": GITHUB_BASE_URL + "logo_UAA2_SI1.png"
    },
    "UAA2_SI2": {
        "url": "https://www.badgecraft.eu/auto/wallet/claim?code=6ubf77&qr=1", 
        "nom": "SI2 : LMRA - Consignation - Déconsignation", 
        "img": GITHUB_BASE_URL + "logo_UAA2_SI2.png"
    },
    "UAA2_SI3": {
        "url": "https://www.badgecraft.eu/auto/wallet/claim?code=hzvqdn&qr=1", 
        "nom": "SI3 : Remplacement d'un composant électrique + règles de sécurité / ergonomiques / environnementales", 
        "img": GITHUB_BASE_URL + "logo_UAA2_SI3.png"
    },
    "UAA2_SI4": {
        "url": "https://www.badgecraft.eu/auto/wallet/claim?code=ott9y2&qr=1", 
        "nom": "SI4 : Remise en service et réglage", 
        "img": GITHUB_BASE_URL + "logo_UAA2_SI4.png"
    },
    "UAA2_SI5": {
        "url": "https://www.badgecraft.eu/auto/wallet/claim?code=zts3i9&qr=1", 
        "nom": "SI5 : Clôture de l'intervention", 
        "img": GITHUB_BASE_URL + "logo_UAA2_SI5.png"
    }
}
LIEN_UAA2 = "https://www.badgecraft.eu/auto/wallet/claim?code=cqs5p3&qr=1"
IMG_UAA2 = GITHUB_BASE_URL + "logo_UAA2.png"

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
    if df_eleve.empty:
        return df_eleve
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

# --- GESTION DES DONNÉES GOOGLE SHEETS ---

def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    colonnes_base = [
        "Nom_Prenom", "Classe", "Code_UAA", "Description_UAA", "Date_Epreuve", "Resultat", "Statut", 
        "UAA1_SI1", "UAA1_SI2", "UAA1_SI3", "UAA1_SI4", "UAA1_SI5",
        "UAA2_SI1", "UAA2_SI2", "UAA2_SI3", "UAA2_SI4", "UAA2_SI5"
    ]
    try:
        # ttl=0 empêche Streamlit de garder l'ancienne version en mémoire
        df = conn.read(worksheet="Data", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=colonnes_base)
        
        # Supprime les éventuels espaces invisibles dans les noms de colonnes
        df.columns = [str(c).strip() for c in df.columns]
        
        df = df.dropna(how="all")
        df['Date_Epreuve'] = pd.to_datetime(df['Date_Epreuve'], errors='coerce')
        
        if 'Statut' not in df.columns:
            df['Statut'] = 'Actif'
        else:
            df['Statut'] = df['Statut'].fillna('Actif')
            
        # S'assurer de manière agressive que TOUTES les colonnes existent
        for col in colonnes_base:
            if col not in df.columns:
                df[col] = ""
                
        return df
    except Exception as e:
        return pd.DataFrame(columns=colonnes_base)

def save_data(df):
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_to_save = df.copy()
    colonnes_obligatoires = [
        "Nom_Prenom", "Classe", "Code_UAA", "Description_UAA", "Date_Epreuve", "Resultat", "Statut", 
        "UAA1_SI1", "UAA1_SI2", "UAA1_SI3", "UAA1_SI4", "UAA1_SI5",
        "UAA2_SI1", "UAA2_SI2", "UAA2_SI3", "UAA2_SI4", "UAA2_SI5"
    ]
    
    # On revérifie avant de sauvegarder
    for col in colonnes_obligatoires:
        if col not in df_to_save.columns:
            df_to_save[col] = ""

    df_to_save = df_to_save[colonnes_obligatoires]
    df_to_save = df_to_save.fillna("")
    df_to_save = df_to_save.astype(str)
    
    try:
        conn.update(worksheet="Data", data=df_to_save)
        st.cache_data.clear() # On vide le cache immédiatement après l'écriture
    except Exception as e:
        st.error(f"Erreur d'écriture Google Sheets : {e}")
        st.stop()

# --- CLASSE PDF ---
class PDF(FPDF):
    def header(self):
        try:
            self.image(LOGO_PATH, x=10, y=8, w=30)
        except:
            pass 
        self.ln(20)

    def footer(self):
        self.set_y(-55)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(2)
        self.set_font("Arial", 'B', 8)
        self.set_text_color(0, 0, 0)
        self.cell(0, 4, clean_text("Rappel du cursus complet (UAA) :"), 0, 1, 'L')
        self.set_font("Arial", 'I', 7)
        self.set_text_color(80, 80, 80)
        
        for annee, uaas in PROGRAMME.items():
            for code, desc in uaas.items():
                desc_courte = desc[:110] + "..." if len(desc) > 110 else desc
                texte = f"[{annee}] {code} : {desc_courte}"
                self.cell(0, 3.5, clean_text(texte), 0, 1, 'L')

        self.set_y(-10)
        self.set_font("Arial", 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

# --- GÉNÉRATION PDF ---
def generate_pdf(nom_eleve, df_eleve_filtered):
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_y(30)
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, clean_text(f"Suivi des UAA - {nom_eleve}"), ln=True, align='C')
    pdf.ln(2)
    pdf.set_font("Arial", 'I', 12)
    pdf.cell(0, 10, clean_text(NOM_OPTION), ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 10, clean_text(f"Date du document : {datetime.now().strftime('%d/%m/%Y')}"), ln=True)
    pdf.ln(2)

    reussites = df_eleve_filtered[df_eleve_filtered["Resultat"].astype(str).str.contains("Réussite")]
    if reussites["Code_UAA"].nunique() >= 6:
        pdf.set_font("Arial", 'B', 11)
        pdf.set_text_color(0, 128, 0)
        pdf.cell(0, 10, clean_text("*** CERTIFICAT DE QUALIFICATION (CQ6) OBTENU ***"), ln=True, align='C')
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
    
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 9)
    col_w = [15, 15, 115, 20, 25]
    headers = ["Annee", "UAA", "Description de la competence", "Resultat", "Date"]
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 10, clean_text(h), 1, 0, 'C', 1)
    pdf.ln()
    
    pdf.set_font("Arial", '', 8)
    for index, row in df_eleve_filtered.iterrows():
        classe = clean_text(str(row['Classe'])[:3])
        code = clean_text(row['Code_UAA'])
        desc = clean_text(row['Description_UAA'])
        if len(desc) > 75: desc = desc[:75] + "..."
        res_brut = str(row['Resultat'])
        if "Réussite" in res_brut:
            res_court = "Acquis"
            color = (0, 128, 0)
        else:
            res_court = "Non Acquis"
            color = (200, 0, 0)
        
        try:
            date_str = row['Date_Epreuve'].strftime('%d/%m/%Y')
        except:
            date_str = str(row['Date_Epreuve'])[:10]

        pdf.cell(col_w[0], 10, classe, 1, 0, 'C')
        pdf.cell(col_w[1], 10, code, 1, 0, 'C')
        pdf.cell(col_w[2], 10, desc, 1)
        pdf.set_text_color(*color)
        pdf.set_font("Arial", 'B', 8)
        pdf.cell(col_w[3], 10, clean_text(res_court), 1, 0, 'C')
        pdf.set_font("Arial", '', 8)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(col_w[4], 10, date_str, 1, 1, 'C')
    
    return pdf.output(dest='S').encode('latin-1')

def generate_global_pdf(df):
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_y(30)
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, clean_text("Rapport Global - Situation des Élèves"), ln=True, align='C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, clean_text(NOM_OPTION), ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 10, clean_text(f"Généré le : {datetime.now().strftime('%d/%m/%Y')}"), ln=True, align='C')
    pdf.ln(10)

    df_actifs = df[df["Statut"] != "Archivé"]
    eleves = df_actifs["Nom_Prenom"].unique()
    eleves.sort()

    for eleve in eleves:
        if pdf.get_y() > 220:
            pdf.add_page()
            pdf.set_y(30)

        sub_df = get_latest_results(df[df["Nom_Prenom"] == eleve])
        
        reussites = sub_df[sub_df["Resultat"].astype(str).str.contains("Réussite")]
        if reussites["Code_UAA"].nunique() >= 6:
            titre_eleve = f"Élève : {eleve} - *** CQ6 OBTENU ***"
            pdf.set_fill_color(200, 255, 200) 
        else:
            titre_eleve = f"Élève : {eleve}"
            pdf.set_fill_color(220, 230, 255) 
        
        pdf.set_font("Arial", 'B', 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, clean_text(titre_eleve), 1, 1, 'L', 1)
        
        if sub_df.empty:
            pdf.set_font("Arial", 'I', 10)
            pdf.cell(0, 8, clean_text("Aucun résultat encodé."), 1, 1)
        else:
            pdf.set_font("Arial", 'B', 9)
            pdf.set_fill_color(240, 240, 240)
            
            col_w = [18, 17, 110, 25, 20] 
            
            headers = ["Classe", "UAA", "Description", "Resultat", "Date"]
            for i, h in enumerate(headers):
                pdf.cell(col_w[i], 6, clean_text(h), 1, 0, 'C', 1)
            pdf.ln()
            
            pdf.set_font("Arial", '', 8)
            for _, row in sub_df.iterrows():
                desc = clean_text(row['Description_UAA'])
                if len(desc) > 65: desc = desc[:65] + "..."
                
                res_brut = str(row['Resultat'])
                if "Réussite" in res_brut:
                    res_court = "ACQUIS"
                    color = (0, 128, 0)
                else:
                    res_court = "NON ACQUIS"
                    color = (200, 0, 0)

                try:
                    d_str = row['Date_Epreuve'].strftime('%d/%m/%Y')
                except:
                    d_str = str(row['Date_Epreuve'])[:10]

                pdf.cell(col_w[0], 6, clean_text(str(row['Classe'])[:3]), 1, 0, 'C')
                pdf.cell(col_w[1], 6, clean_text(row['Code_UAA']), 1, 0, 'C')
                pdf.cell(col_w[2], 6, desc, 1)
                pdf.set_text_color(*color)
                pdf.set_font("Arial", 'B', 8)
                pdf.cell(col_w[3], 6, clean_text(res_court), 1, 0, 'C')
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", '', 8)
                pdf.cell(col_w[4], 6, d_str, 1, 1, 'C')
            pdf.ln(5) 
    return pdf.output(dest='S').encode('latin-1')

# --- MAIL ---
def send_email_wrapper(destinataires_list, sujet, corps, pdf_bytes=None, pdf_name=None, mime_type='plain'):
    try:
        email_exp = st.secrets["email"]["EMAIL_EXPEDITEUR"]
        mdp_exp = st.secrets["email"]["MOT_DE_PASSE_EMAIL"]
        
        msg = MIMEMultipart()
        msg['From'] = email_exp
        msg['To'] = ", ".join(destinataires_list) 
        msg['Subject'] = sujet
        msg.attach(MIMEText(corps, mime_type, 'utf-8'))

        if pdf_bytes and pdf_name:
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
        st.error(f"Erreur d'envoi mail (Vérifier secrets) : {e}")
        return False

def send_badge_email(nom_eleve, nom_badge, url_badge, img_badge, est_uaa_finale=False):
    destinataire = normalize_email_text(nom_eleve) + DOMAIN_ECOLE
    
    if est_uaa_finale:
        sujet = f"🏆 FÉLICITATIONS ! Tu as validé l'intégralité de l'{nom_badge}"
        label_entete = f"L'intégralité de l'<strong>{nom_badge}</strong> est validée !"
        texte_intro = "C'est une étape majeure ! Tu as réussi l'épreuve de validation finale :"
    else:
        sujet = f"🏆 Félicitations ! Vous avez obtenu le badge : {nom_badge}"
        label_entete = f"Félicitations {nom_eleve} !"
        texte_intro = "Suite à ton évaluation, tu as brillamment obtenu le badge numérique :"

    corps_html = f"""
    <div style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
      <h2 style="color: #2c3e50;">{label_entete}</h2>
      <p>{texte_intro}</p>
      
      <div style="text-align: center; margin: 20px 0;">
          <img src="{img_badge}" alt="{nom_badge}" style="max-width: 150px; border-radius: 10px;">
          <p style="font-size: 16px; font-weight: bold; color: #2980b9;">{nom_badge}</p>
      </div>
      
      <p>Ce badge numérique certifie tes compétences. Tu peux l'ajouter à ton CV ou le partager sur tes réseaux (comme LinkedIn).</p>
      
      <hr style="border: 1px solid #eee; margin: 20px 0;">
      
      <h3 style="color: #2c3e50;">Comment récupérer et sauvegarder ton badge ?</h3>
      
      <p>La procédure est la même que pour tes badges précédents :</p>
      <ol>
        <li>Clique sur le bouton ci-dessous pour réclamer ton badge : <br>
            <a href="{url_badge}" style="display: inline-block; margin-top: 10px; margin-bottom: 10px; padding: 10px 15px; background-color: #27ae60; color: white; text-decoration: none; border-radius: 5px;">Réclamer mon badge</a>
        </li>
        <li>Connecte-toi à ton compte <strong>Badgecraft</strong>.</li>
        <li>Accepte ton badge !</li>
      </ol>

      <p>Et c'est tout ! Ton badge est maintenant stocké de manière sécurisée dans ton "Portefeuille" sur Badgecraft.</p>
      
      <p>Continue sur cette belle lancée !</p>
      <p><em>L'équipe pédagogique</em></p>
    </div>
    """
    send_email_wrapper([destinataire], sujet, corps_html, mime_type='html')

# --- UI PRINCIPALE ---

st.set_page_config(page_title="Encodage UAA", page_icon="⚡", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.image(LOGO_PATH, width=100)
    st.title("🔒 Connexion")
    pwd = st.text_input("Mot de passe", type="password", key="login_pwd")
    if st.button("Se connecter", key="login_btn"):
        try:
            secret_pwd = st.secrets["general"]["MOT_DE_PASSE_APP"]
        except:
            secret_pwd = "admin"
        
        if pwd == secret_pwd:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect")
else:
    st.sidebar.image(LOGO_PATH, use_container_width=True)
    st.sidebar.divider()
    
    page_actuelle = st.sidebar.radio(
        "Navigation",
        ["📝 Encodage", "📊 Dashboard", "📧 Bulletins", "⚙️ Admin"],
        key="navigation_menu"
    )

    st.sidebar.divider()
    if st.sidebar.button("Se déconnecter", key="logout_btn"):
        st.session_state.authenticated = False
        st.rerun()

    st.title(f"⚡ {NOM_OPTION}")

    df = load_data()
    df_actifs = df[df["Statut"] != "Archivé"]
    existing_students = df_actifs["Nom_Prenom"].unique().tolist() if not df_actifs.empty else []
    existing_students.sort()

    if page_actuelle == "📝 Encodage":
        st.subheader("📝 Nouvel encodage")
        
        mode_eleve = st.radio("Élève :", ["Existant", "Nouveau"], horizontal=True, key="mode_eleve_radio")
        nom_eleve = ""
        
        if mode_eleve == "Existant":
            if existing_students:
                nom_eleve = st.selectbox("Choisir l'élève", existing_students, key="select_exist_p1")
            else:
                st.warning("Aucun élève actif.")
        else:
            nom_eleve = st.text_input("Nom du nouvel élève (Prénom Nom)", key="input_new_p1").strip()

        if nom_eleve:
            st.divider()
            
            # --- AJOUT SÉLECTEUR UAA ---
            uaa_choisie = st.selectbox("Sélectionner l'UAA concernée :", ["UAA 1", "UAA 2"])
            badges_actifs = BADGES_UAA1 if uaa_choisie == "UAA 1" else BADGES_UAA2
            
            type_saisie = st.radio("Que souhaitez-vous faire ?", ["🥇 Validation de Badges (Prérequis SI)", "🎓 Résultat d'une épreuve (UAA)"], horizontal=True)

            if type_saisie == "🥇 Validation de Badges (Prérequis SI)":
                st.info(f"Validez ici les sous-compétences (SI) requises avant le passage de l'{uaa_choisie}. Un email contenant le lien du badge sera automatiquement envoyé à l'élève.")
                
                status = {}
                for col in badges_actifs.keys():
                    if not df.empty and nom_eleve in df["Nom_Prenom"].values:
                        status[col] = df.loc[df["Nom_Prenom"] == nom_eleve, col].astype(str).str.contains("Acquis").any()
                    else:
                        status[col] = False

                st.write(f"**Badges {uaa_choisie} pour {nom_eleve} :**")
                nouvelles_validations = []

                cols = st.columns(5)
                for i, (col_badge, info) in enumerate(badges_actifs.items()):
                    with cols[i]:
                        try:
                            st.image(info["img"], width=80)
                        except:
                            st.write("🖼️")
                            
                        if status[col_badge]:
                            st.success(f"✅ Acquis")
                            st.caption(info['nom'])
                        else:
                            if st.checkbox(f"Valider", key=f"chk_{col_badge}"):
                                nouvelles_validations.append(col_badge)
                            st.caption(info['nom'])

                if nouvelles_validations:
                    if st.button("💾 Enregistrer et envoyer les badges", type="primary"):
                        if df.empty or nom_eleve not in df["Nom_Prenom"].values:
                            new_row = {"Nom_Prenom": nom_eleve, "Classe": "", "Code_UAA": "Profil", "Description_UAA": "Création profil pour badges", "Date_Epreuve": pd.to_datetime(datetime.today()), "Resultat": "", "Statut": "Actif"}
                            for b in BADGES_UAA1.keys(): new_row[b] = ""
                            for b in BADGES_UAA2.keys(): new_row[b] = ""
                            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

                        for b in nouvelles_validations:
                            df.loc[df["Nom_Prenom"] == nom_eleve, b] = "Acquis"
                            send_badge_email(nom_eleve, badges_actifs[b]['nom'], badges_actifs[b]['url'], badges_actifs[b]['img'])

                        save_data(df)
                        st.success("✅ Badges enregistrés et emails envoyés ! 🎉")
                        time.sleep(2)
                        st.rerun()

            elif type_saisie == "🎓 Résultat d'une épreuve (UAA)":
                c1, c2 = st.columns(2)
                classe_associee = "4TQEMI" if uaa_choisie == "UAA 1" else "5TQEMI"
                st.write(f"**Année :** {classe_associee}")
                desc = PROGRAMME[classe_associee][uaa_choisie]
                st.info(f"**Compétence visée :** {desc}")

                badges_manquants = False
                if mode_eleve == "Existant" and not df.empty and nom_eleve in df["Nom_Prenom"].values:
                    status_uaa = [df.loc[df["Nom_Prenom"] == nom_eleve, b].astype(str).str.contains("Acquis").any() for b in badges_actifs.keys()]
                    if not all(status_uaa):
                        badges_manquants = True
                else:
                    badges_manquants = True

                if badges_manquants:
                    st.error(f"🔒 Action bloquée : Impossible d'encoder un résultat pour l'{uaa_choisie}. L'élève **{nom_eleve}** doit d'abord valider tous les badges prérequis de cette UAA.")
                else:
                    deja_reussi = False
                    date_reussite_str = ""
                    
                    if mode_eleve == "Existant" and not df.empty:
                        mask = (df["Nom_Prenom"] == nom_eleve) & (df["Code_UAA"] == uaa_choisie) & (df["Resultat"].astype(str).str.contains("Réussite", na=False))
                        df_deja = df[mask]
                        if not df_deja.empty:
                            deja_reussi = True
                            try:
                                date_reussite_str = pd.to_datetime(df_deja.iloc[0]["Date_Epreuve"]).strftime('%d/%m/%Y')
                            except:
                                date_reussite_str = str(df_deja.iloc[0]["Date_Epreuve"])[:10]

                    if deja_reussi:
                        st.error(f"🔒 Action bloquée : **{nom_eleve}** a déjà validé l'**{uaa_choisie}** le {date_reussite_str}. Nouvel encodage impossible.")
                    else:
                        c3, c4 = st.columns(2)
                        date_ep = c3.date_input("Date de l'épreuve", datetime.today())
                        res = c4.radio("Résultat obtenu", ["Réussite (Acquis)", "Echec (Non Acquis)"], horizontal=True)

                        if st.button("💾 Sauvegarder le résultat", type="primary"):
                            if not date_ep:
                                st.error("❌ Oups ! Veuillez définir une date valide.")
                            else:
                                if "Réussite" in res:
                                    lien_final = LIEN_UAA1 if uaa_choisie == "UAA 1" else LIEN_UAA2
                                    img_final = IMG_UAA1 if uaa_choisie == "UAA 1" else IMG_UAA2
                                    send_badge_email(nom_eleve, uaa_choisie, lien_final, img_final, est_uaa_finale=True)

                                date_to_save = pd.to_datetime(date_ep)
                                new_row = {
                                    "Nom_Prenom": nom_eleve, 
                                    "Classe": classe_associee, 
                                    "Code_UAA": uaa_choisie, 
                                    "Description_UAA": desc, 
                                    "Date_Epreuve": date_to_save, 
                                    "Resultat": res,
                                    "Statut": "Actif"
                                }
                                df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                                
                                toutes_cles_badges = list(BADGES_UAA1.keys()) + list(BADGES_UAA2.keys())
                                for b in toutes_cles_badges:
                                    if not df.empty and nom_eleve in df["Nom_Prenom"].values:
                                        if df.loc[df["Nom_Prenom"] == nom_eleve, b].astype(str).str.contains("Acquis").any():
                                            df.loc[df.index[-1], b] = "Acquis"

                                save_data(df)
                                st.toast('✅ Encodage enregistré avec succès !')
                                
                                reussites_eleve = df[(df["Nom_Prenom"] == nom_eleve) & (df["Resultat"].astype(str).str.contains("Réussite"))]
                                if reussites_eleve["Code_UAA"].nunique() >= 6:
                                    st.balloons()
                                    st.success(f"🎓 FÉLICITATIONS ! L'élève {nom_eleve} a validé ses 6 UAA et obtient son Certificat de Qualification !")
                                    time.sleep(3)
                                else:
                                    st.success(f"✅ Résultat ajouté pour {nom_eleve} !")
                                time.sleep(1)
                                st.rerun()

    elif page_actuelle == "📊 Dashboard":
        st.subheader("📊 Tableau de Bord & Données")
        
        if df_actifs.empty:
            st.info("Aucune donnée enregistrée pour le moment.")
        else:
            col_f1, col_f2 = st.columns(2)
            classes_uniques = df_actifs["Classe"].unique().tolist()
            classes_uniques = [c for c in classes_uniques if str(c).strip() != ""] 
            
            filtre_classe = col_f1.multiselect("Filtrer par Classe", classes_uniques, default=classes_uniques, key="dash_f_classe")
            filtre_eleve = col_f2.multiselect("Filtrer par Élève", existing_students, default=[], key="dash_f_eleve")

            df_filtered = df_actifs[df_actifs["Classe"].isin(filtre_classe)]
            if filtre_eleve:
                df_filtered = df_filtered[df_filtered["Nom_Prenom"].isin(filtre_eleve)]

            df_eval = df_filtered[~df_filtered["Code_UAA"].str.contains("Profil", na=False)]

            nb_eleves = df_eval["Nom_Prenom"].nunique()
            total_eval = len(df_eval)
            reussites = len(df_eval[df_eval["Resultat"].str.contains("Réussite")])
            taux_reussite = round((reussites / total_eval * 100) if total_eval > 0 else 0, 1)

            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("👩‍🎓 Élèves évalués", nb_eleves)
            kpi2.metric("📝 Total des évaluations", total_eval)
            kpi3.metric("🎯 Taux de réussite global", f"{taux_reussite}%")

            st.divider()

            c_chart1, c_chart2 = st.columns(2)
            
            with c_chart1:
                st.markdown("**Répartition des Résultats**")
                if not df_eval.empty:
                    df_eval["Resultat_Court"] = df_eval["Resultat"].apply(lambda x: "Acquis" if "Réussite" in str(x) else "Non Acquis")
                    repartition = df_eval["Resultat_Court"].value_counts().reset_index()
                    repartition.columns = ["Statut", "Nombre"]
                    fig_pie = px.pie(repartition, values="Nombre", names="Statut", color="Statut", 
                                    color_discrete_map={"Acquis":"#28a745", "Non Acquis":"#dc3545"},
                                    hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True, key="pie_chart_dash")

            with c_chart2:
                st.markdown("**Évaluations par Classe**")
                if not df_eval.empty:
                    eval_par_classe = df_eval.groupby(["Classe", "Resultat_Court"]).size().reset_index(name="Nombre")
                    fig_bar = px.bar(eval_par_classe, x="Classe", y="Nombre", color="Resultat_Court",
                                    barmode="group",
                                    color_discrete_map={"Acquis":"#28a745", "Non Acquis":"#dc3545"})
                    st.plotly_chart(fig_bar, use_container_width=True, key="bar_chart_dash")

            st.markdown("**Détail des données (filtré)**")
            df_display = df_filtered[["Nom_Prenom", "Classe", "Code_UAA", "Date_Epreuve", "Resultat"]].sort_values(by="Date_Epreuve", ascending=False)
            df_display["Date_Epreuve"] = df_display["Date_Epreuve"].dt.strftime('%d/%m/%Y')
            
            st.dataframe(df_display.style.apply(colorer_lignes, axis=1), hide_index=True, use_container_width=True)

    elif page_actuelle == "📧 Bulletins":
        st.subheader("1. Bulletin Individuel")
        eleve_pdf = st.selectbox("Sélectionner l'élève", existing_students, key="pdf_select_p3") if existing_students else None
        
        if eleve_pdf:
            email_auto = normalize_email_text(eleve_pdf) + DOMAIN_ECOLE
            df_historique = df[(df["Nom_Prenom"] == eleve_pdf) & (~df["Code_UAA"].str.contains("Profil", na=False))].copy()
            df_final = get_latest_results(df_historique)
            
            pdf_bytes = generate_pdf(eleve_pdf, df_final)
            st.download_button("⬇️ Télécharger le PDF", pdf_bytes, f"Bulletin_{eleve_pdf}.pdf", "application/pdf", key=f"dl_pdf_indiv_{eleve_pdf}")
            
            with st.expander("📧 Envoyer par mail"):
                st.caption("💡 *Astuce : Séparez les adresses par une virgule.*")
                c_mail1, c_mail2 = st.columns(2)
                email_stud = c_mail1.text_input("Email de l'élève", value=email_auto, key=f"email_stud_p3_{eleve_pdf}")
                email_parent = c_mail2.text_input("Email(s) parents (facultatif)", key=f"email_parent_p3_{eleve_pdf}")
                
                if st.button("Envoyer le bulletin", key=f"btn_send_indiv_{eleve_pdf}"):
                    reussites_actuelles = df_final[df_final["Resultat"].astype(str).str.contains("Réussite")]
                    nb_uaa = reussites_actuelles["Code_UAA"].nunique()
                    cq6_message = "\n\n🎉 Félicitations ! CQ6 obtenu." if nb_uaa >= 6 else ""

                    sujet = f"Bilan UAA - {eleve_pdf}"
                    corps = f"Bonjour,\n\nVoici le récapitulatif des UAA pour {eleve_pdf}.\n\nBilan : {nb_uaa} / 6{cq6_message}\n\nCordialement."
                    
                    destinataires = []
                    if email_stud.strip(): destinataires.extend([e.strip() for e in email_stud.replace(';', ',').split(',') if e.strip()])
                    if email_parent.strip(): destinataires.extend([e.strip() for e in email_parent.replace(';', ',').split(',') if e.strip()])

                    if not destinataires:
                        st.error("❌ Indiquez une adresse email.")
                    else:
                        if send_email_wrapper(destinataires, sujet, corps, pdf_bytes, f"Bulletin_{eleve_pdf}.pdf"):
                            st.success(f"✅ Mail envoyé !")

        st.divider()
        st.subheader("2. Rapport Global")
        df_pdf_global = df[~df["Code_UAA"].str.contains("Profil", na=False)]
        pdf_global_bytes = generate_global_pdf(df_pdf_global)
        st.download_button("⬇️ Télécharger PDF Global", pdf_global_bytes, "Rapport_Global.pdf", "application/pdf", key="dl_pdf_global")

    elif page_actuelle == "⚙️ Admin":
        st.subheader("⚙️ Administration & Base de Données")
        action = st.radio("Choisissez une action :", ["Renommer un élève", "Archiver", "Restaurer", "Supprimer Ligne", "⚠️ Réparer la base (Vider le cache)"], key="admin_action_radio")
        
        if action == "Renommer un élève":
            if existing_students:
                st.info("Cette action modifiera le nom de l'élève sur l'ensemble de ses enregistrements.")
                old_name = st.selectbox("Sélectionnez l'élève à renommer", existing_students, key="rename_old_p4")
                new_name = st.text_input("Entrez le nouveau nom (Prénom Nom)", key="rename_new_p4")
                
                if st.button("Valider le nouveau nom", type="primary", key="btn_rename"):
                    if new_name.strip() == "":
                        st.error("Le nouveau nom ne peut pas être vide.")
                    else:
                        df.loc[df["Nom_Prenom"] == old_name, "Nom_Prenom"] = new_name.strip()
                        save_data(df)
                        st.success(f"✅ {old_name} a été renommé en {new_name.strip()} !")
                        time.sleep(1)
                        st.rerun()

        elif action == "Archiver":
            if existing_students:
                eleve_to_arch = st.selectbox("Élève", existing_students, key="archive_eleve_p4")
                if st.button(f"Archiver {eleve_to_arch}", key="btn_archive"):
                    df.loc[df["Nom_Prenom"] == eleve_to_arch, "Statut"] = "Archivé"
                    save_data(df)
                    st.success("Fait !")
                    time.sleep(1)
                    st.rerun()

        elif action == "Restaurer":
            df_archives = df[df["Statut"] == "Archivé"]
            eleves_arch = df_archives["Nom_Prenom"].unique().tolist()
            if eleves_arch:
                e = st.selectbox("Restaurer qui ?", eleves_arch, key="restore_eleve_p4")
                if st.button("Restaurer", key="btn_restore"):
                    df.loc[df["Nom_Prenom"] == e, "Statut"] = "Actif"
                    save_data(df)
                    st.success("Restauré !")
                    time.sleep(1)
                    st.rerun()
            else:
                st.info("Personne dans les archives.")

        elif action == "Supprimer Ligne":
            st.dataframe(df)
            idx = st.number_input("Index de la ligne à supprimer", min_value=0, max_value=max(0, len(df)-1), step=1, key="delete_idx_p4")
            if st.button("Supprimer définitivement", type="primary", key="btn_delete_line"):
                df = df.drop(index=idx).reset_index(drop=True)
                save_data(df)
                st.success("Ligne supprimée !")
                time.sleep(1)
                st.rerun()

        elif action == "⚠️ Réparer la base (Vider le cache)":
            st.warning("Utilisez ce bouton uniquement si l'application plante lors de l'encodage de l'UAA 2.")
            if st.button("Forcer la réparation et vider le cache", type="primary", key="btn_repair_db"):
                st.cache_data.clear()
                df_repair = load_data()
                save_data(df_repair)
                st.success("✅ Mémoire de l'application vidée. Tout devrait fonctionner à présent !")
                time.sleep(2)
                st.rerun()
