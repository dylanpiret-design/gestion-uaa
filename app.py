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
from streamlit_gsheets import GSheetsConnection

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
    # On assure que c'est bien une date pour le tri
    df_eleve['Date_Epreuve'] = pd.to_datetime(df_eleve['Date_Epreuve'], errors='coerce')
    df_sorted = df_eleve.sort_values(by="Date_Epreuve", ascending=False)
    df_latest = df_sorted.drop_duplicates(subset=["Code_UAA"], keep="first")
    return df_latest.sort_values(by="Code_UAA")

# --- GESTION DES DONNÉES GOOGLE SHEETS (CORRIGÉE) ---

def load_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df = conn.read(worksheet="Resultats", ttl=0)
        
        # Si le fichier est vide ou ne contient que les entêtes
        if df.empty:
             return pd.DataFrame(columns=["Nom_Prenom", "Classe", "Code_UAA", "Description_UAA", "Date_Epreuve", "Resultat", "Statut"])
        
        # 1. On supprime les lignes totalement vides (les "fantômes" d'Excel)
        df = df.dropna(how="all")
        
        # 2. Conversion robuste de la date (erreurs='coerce' évite le crash si une date est mal écrite)
        df['Date_Epreuve'] = pd.to_datetime(df['Date_Epreuve'], errors='coerce')
        
        # 3. Gestion du Statut par défaut
        if 'Statut' not in df.columns:
            df['Statut'] = 'Actif'
        else:
            df['Statut'] = df['Statut'].fillna('Actif')
            
        return df
    except Exception:
        # En cas de gros problème de connexion, on renvoie un DF vide pour ne pas crasher l'app
        return pd.DataFrame(columns=["Nom_Prenom", "Classe", "Code_UAA", "Description_UAA", "Date_Epreuve", "Resultat", "Statut"])

def save_data(df):
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 1. On travaille sur une copie pour ne pas casser l'affichage
    df_to_save = df.copy()
    
    # 2. NETTOYAGE ABSOLU (C'est ça qui manquait !)
    # On remplit TOUTES les cases vides par du vide "" (sinon ça plante)
    df_to_save = df_to_save.fillna("")
    
    # 3. On force tout en texte (String) pour éviter les erreurs de format nombre/date
    # Cela garantit que Google accepte les données sans réfléchir
    df_to_save = df_to_save.astype(str)
    
    # 4. Envoi
    conn.update(worksheet="Resultats", data=df_to_save)
    st.cache_data.clear()

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

        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(220, 230, 255) 
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, clean_text(f"Élève : {eleve}"), 1, 1, 'L', 1)
        
        sub_df = get_latest_results(df[df["Nom_Prenom"] == eleve])
        
        if sub_df.empty:
            pdf.set_font("Arial", 'I', 10)
            pdf.cell(0, 8, clean_text("Aucun résultat encodé."), 1, 1)
        else:
            pdf.set_font("Arial", 'B', 9)
            pdf.set_fill_color(240, 240, 240)
            col_w = [20, 20, 110, 25, 15] 
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
                    d_str = row['Date_Epreuve'].strftime('%d/%m')
                except:
                    d_str = str(row['Date_Epreuve'])[:5]

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
def send_email_wrapper(destinataires_list, sujet, corps, pdf_bytes=None, pdf_name=None):
    try:
        email_exp = st.secrets["email"]["EMAIL_EXPEDITEUR"]
        mdp_exp = st.secrets["email"]["MOT_DE_PASSE_EMAIL"]
        
        msg = MIMEMultipart()
        msg['From'] = email_exp
        msg['To'] = ", ".join(destinataires_list) 
        msg['Subject'] = sujet
        msg.attach(MIMEText(corps, 'plain'))

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

# --- UI PRINCIPALE ---

st.set_page_config(page_title="Encodage UAA", layout="centered")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    try:
        st.image(LOGO_PATH, width=100)
    except:
        pass
    
    st.title("🔒 Connexion")
    pwd = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
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
    try:
        st.sidebar.image(LOGO_PATH, use_container_width=True)
        st.sidebar.divider()
    except:
        pass
        
    st.sidebar.title("Menu")
    if st.sidebar.button("Se déconnecter"):
        st.session_state.authenticated = False
        st.rerun()

    st.title(f"⚡ {NOM_OPTION}")

    df = load_data()
    df_actifs = df[df["Statut"] != "Archivé"]
    existing_students = df_actifs["Nom_Prenom"].unique().tolist() if not df_actifs.empty else []
    existing_students.sort()

    tab1, tab2, tab3 = st.tabs(["📝 Encodage", "📧 Bulletins", "🗑️ Admin"])

    with tab1:
        st.subheader("Nouvel encodage")
        mode_eleve = st.radio("Élève :", ["Existant", "Nouveau"], horizontal=True)
        nom_eleve = ""
        if mode_eleve == "Existant":
            if existing_students:
                nom_eleve = st.selectbox("Choisir l'élève", existing_students)
            else:
                st.warning("Aucun élève actif.")
        else:
            new_name = st.text_input("Nom du nouvel élève (Prénom Nom)")
            if new_name: nom_eleve = new_name.strip()

        if nom_eleve:
            st.divider()
            c1, c2 = st.columns(2)
            classe = c1.selectbox("Année", list(PROGRAMME.keys()))
            codes_uaa = list(PROGRAMME[classe].keys())
            code_choisi = c2.selectbox("UAA", codes_uaa)
            desc = PROGRAMME[classe][code_choisi]
            st.info(f"{code_choisi} : {desc}")

            deja_reussi = False
            date_reussite = None

            if mode_eleve == "Existant" and not df.empty:
                mask = (df["Nom_Prenom"] == nom_eleve) & (df["Code_UAA"] == code_choisi) & (df["Resultat"].astype(str).str.contains("Réussite"))
                resultats_precedents = df[mask]
                
                if not resultats_precedents.empty:
                    deja_reussi = True
                    d = resultats_precedents.iloc[0]["Date_Epreuve"]
                    if isinstance(d, str):
                        date_reussite = d[:10]
                    else:
                        date_reussite = d.strftime('%d/%m/%Y')

            if deja_reussi:
                st.success(f"✅ {nom_eleve} a déjà validé cette UAA le {date_reussite}.")
                st.warning("🔒 L'encodage est verrouillé.")
            else:
                c3, c4 = st.columns(2)
                date_ep = c3.date_input("Date", datetime.today())
                res = c4.radio("Résultat", ["Réussite (Acquis)", "Echec (Non Acquis)"], horizontal=True)
                
                if st.button("Sauvegarder", type="primary"):
                    date_to_save = pd.to_datetime(date_ep)
                    new_row = {
                        "Nom_Prenom": nom_eleve, 
                        "Classe": classe, 
                        "Code_UAA": code_choisi, 
                        "Description_UAA": desc, 
                        "Date_Epreuve": date_to_save, 
                        "Resultat": res,
                        "Statut": "Actif"
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(df)
                    st.success("Enregistré dans le Cloud !")
                    st.rerun()

    with tab2:
        st.subheader("1. Bulletin Individuel")
        eleve_pdf = st.selectbox("Sélectionner l'élève", existing_students, key="pdf_select") if existing_students else None
        
        if eleve_pdf:
            email_auto = normalize_email_text(eleve_pdf) + DOMAIN_ECOLE
            df_historique = df[df["Nom_Prenom"] == eleve_pdf].copy()
            df_final = get_latest_results(df_historique)
            st.dataframe(df_final[["Classe", "Code_UAA", "Resultat", "Date_Epreuve"]], hide_index=True)
            
            pdf_bytes = generate_pdf(eleve_pdf, df_final)
            st.download_button("⬇️ PDF", pdf_bytes, f"Bulletin_{eleve_pdf}.pdf", "application/pdf")
            
            with st.expander("📧 Envoyer par mail"):
                c_mail1, c_mail2 = st.columns(2)
                email_stud = c_mail1.text_input("Destinataire", value=email_auto)
                
                if st.button("Envoyer"):
                    sujet = f"Bulletin UAA - {eleve_pdf}"
                    corps = f"Bonjour,\n\nVeuillez trouver ci-joint le relevé des notes pour {eleve_pdf}."
                    if send_email_wrapper([email_stud], sujet, corps, pdf_bytes, f"Bulletin_{eleve_pdf}.pdf"):
                        st.success(f"✅ Mail envoyé !")

        st.divider()
        st.subheader("2. Rapport Global")
        pdf_global_bytes = generate_global_pdf(df)
        st.download_button("⬇️ PDF Global", pdf_global_bytes, "Rapport_Global.pdf", "application/pdf")
        
        email_rapport = st.text_input("Email prof/direction")
        if st.button("Envoyer Rapport"):
            sujet = f"Rapport Global UAA - {datetime.now().strftime('%d/%m/%Y')}"
            corps = "Bonjour,\n\nVoici le rapport global."
            if send_email_wrapper([email_rapport], sujet, corps, pdf_global_bytes, "Rapport_Global.pdf"):
                st.success("Envoyé !")

    with tab3:
        st.subheader("⚠️ Admin (Google Sheets)")
        action = st.radio("Action :", ["Archiver", "Restaurer", "Supprimer Ligne"])
        
        if action == "Archiver":
            if existing_students:
                eleve_to_arch = st.selectbox("Élève", existing_students)
                if st.button(f"Archiver {eleve_to_arch}"):
                    df.loc[df["Nom_Prenom"] == eleve_to_arch, "Statut"] = "Archivé"
                    save_data(df)
                    st.success("Fait !")
                    st.rerun()

        elif action == "Restaurer":
            df_archives = df[df["Statut"] == "Archivé"]
            eleves_arch = df_archives["Nom_Prenom"].unique().tolist()
            if eleves_arch:
                e = st.selectbox("Restaurer qui ?", eleves_arch)
                if st.button("Restaurer"):
                    df.loc[df["Nom_Prenom"] == e, "Statut"] = "Actif"
                    save_data(df)
                    st.success("Restauré !")
                    st.rerun()
            else:
                st.info("Personne dans les archives.")

        elif action == "Supprimer Ligne":
            st.dataframe(df)
            idx = st.number_input("Index", min_value=0, max_value=len(df)-1, step=1)
            if st.button("Supprimer"):
                df = df.drop(index=idx).reset_index(drop=True)
                save_data(df)
                st.success("Supprimé !")
                st.rerun()

