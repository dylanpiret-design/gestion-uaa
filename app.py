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
    try:
        df = conn.read(worksheet="Data", ttl=0)
        if df.empty:
             return pd.DataFrame(columns=["Nom_Prenom", "Classe", "Code_UAA", "Description_UAA", "Date_Epreuve", "Resultat", "Statut"])
        df = df.dropna(how="all")
        df['Date_Epreuve'] = pd.to_datetime(df['Date_Epreuve'], errors='coerce')
        if 'Statut' not in df.columns:
            df['Statut'] = 'Actif'
        else:
            df['Statut'] = df['Statut'].fillna('Actif')
        return df
    except Exception:
        return pd.DataFrame(columns=["Nom_Prenom", "Classe", "Code_UAA", "Description_UAA", "Date_Epreuve", "Resultat", "Statut"])

def save_data(df):
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_to_save = df.copy()
    colonnes_obligatoires = ["Nom_Prenom", "Classe", "Code_UAA", "Description_UAA", "Date_Epreuve", "Resultat", "Statut"]
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
            
            # --- CORRECTION DE LA LARGEUR DES COLONNES ICI ---
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

                # --- CORRECTION DU FORMAT DE LA DATE ICI ---
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
def send_email_wrapper(destinataires_list, sujet, corps, pdf_bytes=None, pdf_name=None):
    try:
        email_exp = st.secrets["email"]["EMAIL_EXPEDITEUR"]
        mdp_exp = st.secrets["email"]["MOT_DE_PASSE_EMAIL"]
        
        msg = MIMEMultipart()
        msg['From'] = email_exp
        msg['To'] = ", ".join(destinataires_list) 
        msg['Subject'] = sujet
        msg.attach(MIMEText(corps, 'plain', 'utf-8'))

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
    # --- NOUVELLE NAVIGATION DANS LA SIDEBAR ---
    st.sidebar.image(LOGO_PATH, use_container_width=True)
    st.sidebar.divider()
    
    # Le composant radio force Streamlit à mémoriser la page actuelle
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

    # ==========================================
    # PAGE 1 : ENCODAGE
    # ==========================================
    if page_actuelle == "📝 Encodage":
        st.subheader("Nouvel encodage")
        
        mode_eleve = st.radio("Élève :", ["Existant", "Nouveau"], horizontal=True, key="mode_eleve_radio")
        nom_eleve = ""
        
        if mode_eleve == "Existant":
            if existing_students:
                nom_eleve = st.selectbox("Choisir l'élève", existing_students, key="select_exist_p1")
            else:
                st.warning("Aucun élève actif.")
        else:
            nom_eleve = st.text_input("Nom du nouvel élève (Prénom Nom)", key="input_new_p1").strip()

        st.divider()

        c1, c2 = st.columns(2)
        classe = c1.selectbox("Année", list(PROGRAMME.keys()))
        codes_uaa = list(PROGRAMME[classe].keys())
        code_choisi = c2.selectbox("UAA", codes_uaa)
        desc = PROGRAMME[classe][code_choisi]
        st.info(f"**Compétence visée :** {desc}")

        # --- VÉRIFICATION DYNAMIQUE (AVANT ENCODAGE) ---
        deja_reussi = False
        date_reussite_str = ""
        
        if mode_eleve == "Existant" and nom_eleve and not df.empty:
            mask = (df["Nom_Prenom"] == nom_eleve) & (df["Code_UAA"] == code_choisi) & (df["Resultat"].astype(str).str.contains("Réussite", na=False))
            df_deja = df[mask]
            if not df_deja.empty:
                deja_reussi = True
                try:
                    date_reussite_str = pd.to_datetime(df_deja.iloc[0]["Date_Epreuve"]).strftime('%d/%m/%Y')
                except:
                    date_reussite_str = str(df_deja.iloc[0]["Date_Epreuve"])[:10]

        # Si déjà réussi, on bloque l'interface
        if deja_reussi:
            st.error(f"🔒 Action bloquée : **{nom_eleve}** a déjà validé l'**{code_choisi}** le {date_reussite_str}. Nouvel encodage impossible.")
        else:
            c3, c4 = st.columns(2)
            date_ep = c3.date_input("Date de l'épreuve", datetime.today())
            res = c4.radio("Résultat obtenu", ["Réussite (Acquis)", "Echec (Non Acquis)"], horizontal=True)

            if st.button("💾 Sauvegarder le résultat", type="primary"):
                if not nom_eleve:
                    st.error("❌ Oups ! Veuillez renseigner le nom de l'élève avant de sauvegarder.")
                elif not date_ep:
                    st.error("❌ Oups ! Veuillez définir une date valide.")
                else:
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

    # ==========================================
    # PAGE 2 : DASHBOARD
    # ==========================================
    elif page_actuelle == "📊 Dashboard":
        st.subheader("📊 Tableau de Bord & Données")
        
        if df_actifs.empty:
            st.info("Aucune donnée enregistrée pour le moment.")
        else:
            col_f1, col_f2 = st.columns(2)
            classes_uniques = df_actifs["Classe"].unique().tolist()
            filtre_classe = col_f1.multiselect("Filtrer par Classe", classes_uniques, default=classes_uniques, key="dash_f_classe")
            filtre_eleve = col_f2.multiselect("Filtrer par Élève", existing_students, default=[], key="dash_f_eleve")

            df_filtered = df_actifs[df_actifs["Classe"].isin(filtre_classe)]
            if filtre_eleve:
                df_filtered = df_filtered[df_filtered["Nom_Prenom"].isin(filtre_eleve)]

            nb_eleves = df_filtered["Nom_Prenom"].nunique()
            total_eval = len(df_filtered)
            reussites = len(df_filtered[df_filtered["Resultat"].str.contains("Réussite")])
            taux_reussite = round((reussites / total_eval * 100) if total_eval > 0 else 0, 1)

            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("👩‍🎓 Élèves évalués", nb_eleves)
            kpi2.metric("📝 Total des évaluations", total_eval)
            kpi3.metric("🎯 Taux de réussite global", f"{taux_reussite}%")

            st.divider()

            c_chart1, c_chart2 = st.columns(2)
            
            with c_chart1:
                st.markdown("**Répartition des Résultats**")
                df_filtered["Resultat_Court"] = df_filtered["Resultat"].apply(lambda x: "Acquis" if "Réussite" in str(x) else "Non Acquis")
                repartition = df_filtered["Resultat_Court"].value_counts().reset_index()
                repartition.columns = ["Statut", "Nombre"]
                fig_pie = px.pie(repartition, values="Nombre", names="Statut", color="Statut", 
                                 color_discrete_map={"Acquis":"#28a745", "Non Acquis":"#dc3545"},
                                 hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True, key="pie_chart_dash")

            with c_chart2:
                st.markdown("**Évaluations par Classe**")
                eval_par_classe = df_filtered.groupby(["Classe", "Resultat_Court"]).size().reset_index(name="Nombre")
                fig_bar = px.bar(eval_par_classe, x="Classe", y="Nombre", color="Resultat_Court",
                                 barmode="group",
                                 color_discrete_map={"Acquis":"#28a745", "Non Acquis":"#dc3545"})
                st.plotly_chart(fig_bar, use_container_width=True, key="bar_chart_dash")

            st.markdown("**Détail des données (filtré)**")
            df_display = df_filtered[["Nom_Prenom", "Classe", "Code_UAA", "Date_Epreuve", "Resultat"]].sort_values(by="Date_Epreuve", ascending=False)
            df_display["Date_Epreuve"] = df_display["Date_Epreuve"].dt.strftime('%d/%m/%Y')
            
            st.dataframe(df_display.style.apply(colorer_lignes, axis=1), hide_index=True, use_container_width=True)

    # ==========================================
    # PAGE 3 : BULLETINS
    # ==========================================
    elif page_actuelle == "📧 Bulletins":
        st.subheader("1. Bulletin Individuel")
        eleve_pdf = st.selectbox("Sélectionner l'élève", existing_students, key="pdf_select_p3") if existing_students else None
        
        if eleve_pdf:
            email_auto = normalize_email_text(eleve_pdf) + DOMAIN_ECOLE
            df_historique = df[df["Nom_Prenom"] == eleve_pdf].copy()
            df_final = get_latest_results(df_historique)
            
            pdf_bytes = generate_pdf(eleve_pdf, df_final)
            st.download_button("⬇️ Télécharger le PDF", pdf_bytes, f"Bulletin_{eleve_pdf}.pdf", "application/pdf", key=f"dl_pdf_indiv_{eleve_pdf}")
            
            with st.expander("📧 Envoyer par mail"):
                st.caption("💡 *Astuce : Vous pouvez envoyer à plusieurs destinataires en séparant les adresses par une virgule (ex: parent1@mail.be, parent2@mail.be).*")
                c_mail1, c_mail2 = st.columns(2)
                
                # --- CORRECTION DES CLÉS ICI ---
                email_stud = c_mail1.text_input("Email de l'élève", value=email_auto, key=f"email_stud_p3_{eleve_pdf}")
                email_parent = c_mail2.text_input("Email(s) parents/tuteurs (facultatif)", key=f"email_parent_p3_{eleve_pdf}")
                # -------------------------------
                
                if st.button("Envoyer le bulletin", key=f"btn_send_indiv_{eleve_pdf}"):
                    reussites_actuelles = df_final[df_final["Resultat"].astype(str).str.contains("Réussite")]
                    nb_uaa = reussites_actuelles["Code_UAA"].nunique()
                    cq6_message = "\n\n🎉 Excellente nouvelle ! Avec la validation de ces unités, l'élève a officiellement acquis les 6 UAA nécessaires et obtient son Certificat de Qualification (CQ6). Toutes nos félicitations !" if nb_uaa >= 6 else ""

                    sujet = f"Bilan d'avancement des Compétences (UAA) - {eleve_pdf}"
                    corps = f"Bonjour,\n\nVoici le récapitulatif officiel de l'état d'avancement des Unités d'Acquis d'Apprentissage (UAA) pour {eleve_pdf} à la date du {datetime.now().strftime('%d/%m/%Y')}.\n\nBilan actuel :\n- Total des UAA validées (Acquises) : {nb_uaa} / 6{cq6_message}\n\nVous trouverez le détail complet dans le document PDF en pièce jointe.\n\nNous restons à votre entière disposition pour faire le point sur ces résultats.\n\nCordialement,\nL'équipe pédagogique."
                    
                    # Nettoyage et préparation de la liste des destinataires
                    destinataires = []
                    if email_stud.strip():
                        destinataires.extend([e.strip() for e in email_stud.replace(';', ',').split(',') if e.strip()])
                    if email_parent.strip():
                        destinataires.extend([e.strip() for e in email_parent.replace(';', ',').split(',') if e.strip()])

                    if not destinataires:
                        st.error("❌ Veuillez indiquer au moins une adresse email.")
                    else:
                        if send_email_wrapper(destinataires, sujet, corps, pdf_bytes, f"Bulletin_{eleve_pdf}.pdf"):
                            st.success(f"✅ Mail envoyé avec succès à : {', '.join(destinataires)} !")

        st.divider()
        st.subheader("2. Rapport Global")
        pdf_global_bytes = generate_global_pdf(df)
        st.download_button("⬇️ Télécharger PDF Global", pdf_global_bytes, "Rapport_Global.pdf", "application/pdf", key="dl_pdf_global")
        
        st.caption("💡 *Astuce : Séparez les adresses par une virgule pour l'envoyer à plusieurs directions/profs en même temps.*")

        # --- NOUVEAU : Bouton pour pré-remplir les adresses ---
        if st.button("👥 Pré-remplir l'équipe pédagogique"):
            # On injecte les adresses directement dans la "mémoire" du champ texte
            st.session_state["email_rapport_p3"] = "leslie.hubot@cnddinant.be,fabian.polet@cnddinant.be,francois.leclercq@cnddinant.be,dylan.piret@cnddinant.be"
        
        email_rapport = st.text_input("Email(s) prof/direction", key="email_rapport_p3")
        
        if st.button("Envoyer Rapport", key="btn_send_global"):
            destinataires_globaux = [e.strip() for e in email_rapport.replace(';', ',').split(',') if e.strip()]
            
            if not destinataires_globaux:
                st.error("❌ Veuillez indiquer au moins une adresse email.")
            else:
                sujet = f"Rapport Global UAA - {NOM_OPTION} - {datetime.now().strftime('%d/%m/%Y')}"
                corps = f"Bonjour,\n\nVeuillez trouver ci-joint le récapitulatif global de l'état d'avancement des Compétences (UAA) pour l'ensemble des élèves actifs de l'option {NOM_OPTION}, arrêté à la date du {datetime.now().strftime('%d/%m/%Y')}.\n\nCordialement,\nL'équipe pédagogique."
                
                if send_email_wrapper(destinataires_globaux, sujet, corps, pdf_global_bytes, "Rapport_Global.pdf"):
                    st.success(f"✅ Rapport envoyé à : {', '.join(destinataires_globaux)} !")

    # ==========================================
    # PAGE 4 : ADMIN
    # ==========================================
    elif page_actuelle == "⚙️ Admin":
        st.subheader("⚙️ Administration & Base de Données")
        action = st.radio("Choisissez une action :", ["Renommer un élève", "Archiver", "Restaurer", "Supprimer Ligne"], key="admin_action_radio")
        
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
