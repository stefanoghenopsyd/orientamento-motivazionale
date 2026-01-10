import streamlit as st
import plotly.graph_objects as go
from PIL import Image
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURAZIONE E COSTANTI ---
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

# --- 1. FUNZIONI DI SERVIZIO E SALVATAGGIO DATI ---

def save_to_google_drive(data_dict, sheet_name="Genera_Risultati"):
    """Salva i dati su Google Sheet se configurato."""
    if "gcp_service_account" not in st.secrets:
        return False

    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        client = gspread.authorize(creds)
        
        try:
            sheet = client.open(sheet_name).sheet1
        except gspread.exceptions.SpreadsheetNotFound:
            st.error(f"Errore: Il foglio Google '{sheet_name}' non trovato.")
            return False

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp]
        
        demographics = data_dict.get('demographics', {})
        row.extend([
            demographics.get('nickname'),
            demographics.get('genere'),
            demographics.get('eta'),
            demographics.get('scolarita')
        ])
        
        results = data_dict.get('results', {})
        row.append(results.get('total_score_intrinsic')) # Punteggio Intrinseco (0-6)
        row.append(results.get('profile_name'))

        sheet.append_row(row)
        return True

    except Exception as e:
        st.error(f"Errore salvataggio Drive: {e}")
        return False

# --- 2. LAYOUT INTESTAZIONE E DEMOGRAFICA (STANDARD) ---

def render_genera_header(logo_path, test_title, theory_text, objectives_text, instructions_text):
    try:
        logo = Image.open(logo_path)
        st.image(logo, use_column_width=True) 
    except FileNotFoundError:
        st.error(f"Errore: Logo '{logo_path}' non trovato.")

    st.markdown(f"<h1 style='text-align: center; color: #1f3a52; margin-bottom: 25px;'>{test_title}</h1>", unsafe_allow_html=True)

    with st.container():
        st.markdown("### 📘 Introduzione e Riferimenti")
        st.info(f"**Teorie di Riferimento**\n\n{theory_text}")
        st.success(f"**Obiettivi del Test**\n\n{objectives_text}")
        st.warning(f"**Istruzioni di Compilazione**\n\n{instructions_text}")
        
    st.markdown("---")

def render_demographics():
    st.header("👤 Informazioni Sociodemografiche")
    with st.container():
        nickname = st.text_input("Nickname", placeholder="Il tuo nome o pseudonimo")
        col_a, col_b = st.columns(2)
        with col_a:
            genere = st.selectbox("Genere", ["", "Maschile", "Femminile", "Non binario", "Non risponde"])
            eta = st.selectbox("Fascia d'età", ["", "Fino a 20 anni", "21-30 anni", "31-40 anni", "41-50 anni", "51-60 anni", "61-70 anni", "Più di 70 anni"])
        with col_b:
            scolarita = st.selectbox("Scolarità", ["", "Licenza media", "Qualifica professionale", "Diploma maturità", "Laurea triennale", "Laurea magistrale/ciclo unico", "Titolo post laurea"])

    is_completed = all([nickname, genere, eta, scolarita])
    return {"nickname": nickname, "genere": genere, "eta": eta, "scolarita": scolarita, "is_completed": is_completed}

# --- 3. LOGICA DOMANDE (SCELTA MULTIPLA A/B) ---

def render_choice_test(questions_list):
    """
    Renderizza domande a scelta multipla (A o B).
    Restituisce un dizionario con le scelte.
    """
    st.subheader("📝 Questionario")
    st.write("Per ogni situazione, scegli l'opzione che ti descrive meglio.")
    st.markdown("---")

    answers = {}
    all_answered = True
    
    with st.form("genera_motivation_form"):
        for index, item in enumerate(questions_list):
            st.markdown(f"#### {index + 1}. {item['question']}")
            
            # Opzioni formattate per chiarezza
            opt_a = f"A. {item['opt_A']}"
            opt_b = f"B. {item['opt_B']}"
            
            val = st.radio(
                label=f"q_{index}",
                options=[opt_a, opt_b],
                index=None,
                key=f"rad_{index}"
            )
            
            # Salviamo "A" o "B" in base alla scelta (controlliamo se la stringa inizia con A o B)
            if val:
                answers[index] = "A" if val.startswith("A.") else "B"
            else:
                all_answered = False
            
            st.markdown("<br>", unsafe_allow_html=True)

        submitted = st.form_submit_button("✅ Invia e Scopri il Profilo")
        
        if submitted:
            if not all_answered:
                st.error("⚠️ Rispondi a tutte le domande prima di inviare.")
                return None
            return answers
    return None

# --- 4. LOGICA PROFILI E GRAFICA GAUGE ---

def calculate_profile(answers):
    """
    Calcola il punteggio intrinseco.
    A = Intrinseco (+1 punto)
    B = Estrinseco (0 punti)
    """
    score_intrinsic = 0
    total_questions = len(answers)
    
    for key, val in answers.items():
        if val == "A":
            score_intrinsic += 1
            
    # Definizione Profili in base al numero di risposte "A"
    # Scala da 0 (Tutte B) a 6 (Tutte A)
    if score_intrinsic == 6:
        profile = "Orientamento fortemente intrinseco: la passione prima di tutto"
        desc = "Sei guidato/a quasi esclusivamente dalla passione, dalla curiosità e dalla voglia di imparare. I riconoscimenti esterni sono secondari rispetto alla gioia del fare."
        color = "green"
    elif 4 <= score_intrinsic <= 5:
        profile = "Orientamento intrinseco: il significato prima di tutto"
        desc = "Il motore delle tue azioni è il senso di realizzazione e il valore del tuo lavoro, anche se apprezzi un giusto riconoscimento."
        color = "#90EE90" # Light Green
    elif score_intrinsic == 3:
        profile = "Orientamento intrinseco con sfumature estrinseche"
        desc = "Sei un equilibrista: cerchi la soddisfazione personale (cuore), ma tieni sempre un occhio pragmatico al riconoscimento e alla stabilità (ragione)."
        color = "yellow"
    elif 1 <= score_intrinsic <= 2:
        profile = "Orientamento estrinseco: il valore materiale dominante"
        desc = "Per te il lavoro è un mezzo. Sebbene tu possa apprezzare ciò che fai, la priorità è ciò che ottieni in cambio: status, denaro o vantaggi."
        color = "orange"
    else: # score 0
        profile = "Orientamento fortemente estrinseco: la sicurezza prima di tutto"
        desc = "La stabilità, la sicurezza economica e il prestigio sono i tuoi fari guida. Le emozioni legate al compito passano in secondo piano rispetto al risultato tangibile."
        color = "red"
        
    return score_intrinsic, profile, desc, color

def show_gauge_chart(score, max_score=6):
    """
    Disegna un tachimetro (Gauge) da Estrinseco (SX) a Intrinseco (DX).
    """
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        title = {'text': "Posizionamento Motivazionale"},
        domain = {'x': [0, 1], 'y': [0, 1]},
        gauge = {
            'axis': {'range': [0, max_score], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "#1f3a52"}, # Colore della lancetta/barra attuale
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 1.5], 'color': '#ffcccc'},   # Rosso (Estrinseco)
                {'range': [1.5, 3.5], 'color': '#ffffcc'}, # Giallo (Misto)
                {'range': [3.5, 6], 'color': '#ccffcc'}    # Verde (Intrinseco)
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': score
            }
        }
    ))
    
    # Annotazioni per rendere chiaro il grafico
    fig.add_annotation(x=0.1, y=0, text="ESTRINSECO", showarrow=False, yshift=-20, font=dict(size=12, color="red"))
    fig.add_annotation(x=0.9, y=0, text="INTRINSECO", showarrow=False, yshift=-20, font=dict(size=12, color="green"))

    fig.update_layout(height=300, margin=dict(t=50, b=50, l=30, r=30))
    st.plotly_chart(fig, use_container_width=True)

# --- 5. MAIN APPLICATION ---

def main():
    st.set_page_config(page_title="GÉNERA - Motivazione", layout="centered")
    
    # --- CONFIGURAZIONE TEST ---
    CONFIG = {
        "logo": "GENERA Logo Colore.png",
        "titolo": "Autovalutazione dell’Orientamento Motivazionale",
        "teoria": "Basato sulla Self-Determination Theory (SDT), questo test esplora se le tue azioni sono guidate da fattori interni (passione, interesse) o esterni (ricompense, immagine).",
        "obiettivi": "Identificare il tuo 'motore' principale per aiutarti a scegliere contesti professionali più allineati alla tua natura.",
        "istruzioni": "Per ogni coppia di scenari, seleziona quello che senti più vicino al tuo modo di essere reale.",
        "sheet_name": "GENERA_Motivation_Data"
    }

    # Domande definite dall'utente
    QUESTIONS = [
        {
            "question": "Quando avvii un nuovo progetto professionale, qual è la sensazione che cerchi di più?",
            "opt_A": "Il brivido della sfida intellettuale, la possibilità di imparare e sentirmi competente.",
            "opt_B": "La prospettiva di ricevere un riconoscimento o di migliorare la mia reputazione."
        },
        {
            "question": "Tra due offerte di lavoro, opteresti probabilmente per quella che:",
            "opt_A": "Ti offre maggiore autonomia, libertà di sperimentare e creatività.",
            "opt_B": "Ti garantisce maggiore stabilità economica e una carriera ben definita."
        },
        {
            "question": "Cosa ti spinge a dare il massimo anche quando nessuno ti guarda?",
            "opt_A": "La soddisfazione personale di fare un buon lavoro e sentirmi realizzato/a.",
            "opt_B": "La paura di deludere le aspettative altrui o di perdere opportunità."
        },
        {
            "question": "Nell'aver portato a termine un compito impegnativo, cosa ti appaga di più?",
            "opt_A": "La sensazione di aver risolto un problema complesso o creato qualcosa di originale.",
            "opt_B": "I complimenti e l'ammirazione dei tuoi colleghi o superiori."
        },
        {
            "question": "Cosa faresti se il tuo lavoro diventasse molto ben retribuito, ma noioso?",
            "opt_A": "Probabilmente cercherei un'altra opportunità, la noia mi toglierebbe ogni stimolo.",
            "opt_B": "Continuerei a farlo volentieri, purché il compenso resti elevato."
        },
        {
            "question": "Scegli tra passione (paga bassa) e sicurezza (lavoro non interessante):",
            "opt_A": "Il progetto che mi appassiona, sperando di renderlo sostenibile.",
            "opt_B": "Il progetto che mi garantisce sicurezza, la passione può svanire."
        }
    ]

    # --- ESECUZIONE ---
    render_genera_header(CONFIG["logo"], CONFIG["titolo"], CONFIG["teoria"], CONFIG["obiettivi"], CONFIG["istruzioni"])
    user_info = render_demographics()

    if user_info["is_completed"]:
        raw_answers = render_choice_test(QUESTIONS)
        
        if raw_answers:
            # Calcolo Profilo
            score, profile_title, profile_desc, color_code = calculate_profile(raw_answers)
            
            st.divider()
            st.header(f"Risultati per {user_info['nickname']}")
            
            # Layout Risultati: Grafico sopra, testo sotto
            st.subheader("1. La tua Bussola Motivazionale")
            show_gauge_chart(score, max_score=6)
            
            st.subheader("2. Il tuo Profilo")
            # Box colorato in base al risultato
            if color_code == "green" or color_code == "#90EE90":
                st.success(f"**{profile_title}**\n\n{profile_desc}")
            elif color_code == "yellow":
                st.warning(f"**{profile_title}**\n\n{profile_desc}")
            else:
                st.error(f"**{profile_title}**\n\n{profile_desc}") # Usa rosso/arancio

            # Salvataggio
            full_data = {
                "demographics": user_info,
                "results": {"total_score_intrinsic": score, "profile_name": profile_title}
            }
            if save_to_google_drive(full_data, sheet_name=CONFIG["sheet_name"]):
                st.caption("✅ Risultati salvati.")

    else:
        st.info("Compila i campi sopra per iniziare il test.")

if __name__ == "__main__":
    main()
