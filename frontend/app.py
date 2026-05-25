"""
Streamlit Frontend — SMA Clinique — Orientation Médicale Simulée
4 screens: Patient intake, Q&A, Physician review (HITL), Final report.
"""

import os
import time
from datetime import datetime
from html import escape
from io import BytesIO
import requests
import streamlit as st
from dotenv import load_dotenv
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="SMA Clinique — Orientation Médicale",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Global */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Hide default Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Main container */
.block-container {
    padding-top: 2rem !important;
    max-width: 1100px;
}

/* Header */
.app-header {
    background: linear-gradient(135deg, #0f766e 0%, #115e59 50%, #134e4a 100%);
    padding: 2rem 2.5rem;
    border-radius: 16px;
    margin-bottom: 2rem;
    box-shadow: 0 4px 24px rgba(15, 118, 110, 0.2);
}
.app-header h1 {
    color: #ffffff;
    font-size: 1.8rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.02em;
}
.app-header p {
    color: #99f6e4;
    font-size: 0.95rem;
    margin: 0.4rem 0 0 0;
    font-weight: 400;
}

/* Cards */
.card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s;
}
.card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

/* Step indicator */
.step-container {
    display: flex;
    align-items: center;
    gap: 0;
    margin: 1.5rem 0;
    padding: 0 1rem;
}
.step {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex: 1;
}
.step-number {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 600;
    font-size: 0.85rem;
    flex-shrink: 0;
}
.step-active .step-number {
    background: #0f766e;
    color: white;
}
.step-done .step-number {
    background: #059669;
    color: white;
}
.step-pending .step-number {
    background: #e5e7eb;
    color: #9ca3af;
}
.step-label {
    font-size: 0.8rem;
    font-weight: 500;
    white-space: nowrap;
}
.step-active .step-label { color: #0f766e; }
.step-done .step-label { color: #059669; }
.step-pending .step-label { color: #9ca3af; }
.step-line {
    flex-grow: 1;
    height: 2px;
    margin: 0 0.5rem;
    min-width: 20px;
}
.step-done + .step-line, .step-active + .step-line { background: #0f766e; }
.step-pending + .step-line, .step-line { background: #e5e7eb; }

/* Disclaimer */
.disclaimer {
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 10px;
    padding: 0.8rem 1rem;
    font-size: 0.82rem;
    color: #991b1b;
    line-height: 1.5;
}

/* Info card */
.info-card {
    background: linear-gradient(135deg, #f0fdfa 0%, #ecfdf5 100%);
    border: 1px solid #a7f3d0;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
}
.info-card h4 {
    color: #065f46;
    margin: 0 0 0.5rem 0;
    font-size: 0.95rem;
}
.info-card p {
    color: #047857;
    margin: 0;
    font-size: 0.85rem;
    line-height: 1.6;
}

/* Question bubble */
.question-bubble {
    background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
    border: 1px solid #93c5fd;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin: 1rem 0;
}
.question-bubble .q-label {
    color: #1e40af;
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.4rem;
}
.question-bubble .q-text {
    color: #1e3a5f;
    font-size: 1.05rem;
    font-weight: 500;
    line-height: 1.5;
}

/* QA history item */
.qa-item {
    background: #f9fafb;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    margin-bottom: 0.5rem;
    border-left: 3px solid #0f766e;
}
.qa-item .qa-q { color: #374151; font-weight: 500; font-size: 0.85rem; }
.qa-item .qa-a { color: #0f766e; font-size: 0.85rem; margin-top: 0.25rem; }

/* Physician section */
.physician-header {
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    border: 1px solid #f59e0b;
    border-radius: 12px;
    padding: 1rem 1.5rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 0.8rem;
}
.physician-header .ph-icon { font-size: 1.5rem; }
.physician-header .ph-text { color: #92400e; font-weight: 600; font-size: 1rem; }
.physician-header .ph-sub { color: #a16207; font-size: 0.85rem; font-weight: 400; }

/* Summary card */
.summary-card {
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
}
.summary-card h5 {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0 0 0.5rem 0;
}
.summary-card p {
    font-size: 0.9rem;
    line-height: 1.6;
    margin: 0;
}
.summary-diag {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
}
.summary-diag h5 { color: #1e40af; }
.summary-diag p { color: #1e3a5f; }
.summary-care {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
}
.summary-care h5 { color: #166534; }
.summary-care p { color: #14532d; }

/* Report section */
.report-section {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    transition: box-shadow 0.2s;
}
.report-section:hover {
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.report-section-title {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #0f766e;
    font-weight: 600;
    margin-bottom: 0.6rem;
    padding-bottom: 0.4rem;
    border-bottom: 2px solid #ccfbf1;
}
.report-section-body {
    color: #374151;
    font-size: 0.9rem;
    line-height: 1.7;
}

/* Metric card */
.metric-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
}
.metric-card {
    flex: 1;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    text-align: center;
}
.metric-card .metric-value {
    font-size: 1.4rem;
    font-weight: 700;
    color: #0f766e;
}
.metric-card .metric-label {
    font-size: 0.75rem;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* Sidebar overrides */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f766e 0%, #134e4a 100%) !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
    color: #ffffff !important;
}

/* Button overrides */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%) !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.7rem 1.5rem !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.01em !important;
    transition: all 0.2s ease !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #115e59 0%, #0f766e 100%) !important;
    box-shadow: 0 4px 12px rgba(15, 118, 110, 0.3) !important;
}

/* Download button */
.stDownloadButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
}

/* Text inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border-radius: 10px !important;
    border: 1.5px solid #d1d5db !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #0f766e !important;
    box-shadow: 0 0 0 2px rgba(15, 118, 110, 0.15) !important;
}

/* Number input */
.stNumberInput > div > div > input {
    border-radius: 10px !important;
}

/* Progress bar */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #0f766e, #14b8a6) !important;
    border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)


STEPS = [
    ("Saisie patient", 1),
    ("Questionnaire", 2),
    ("Revue medecin", 3),
    ("Rapport final", 4),
]


def render_steps(current_screen: int):
    """Render step indicator."""
    parts = []
    for i, (label, screen_num) in enumerate(STEPS):
        if screen_num < current_screen:
            cls = "step-done"
            num = "&#10003;"
        elif screen_num == current_screen:
            cls = "step-active"
            num = str(screen_num)
        else:
            cls = "step-pending"
            num = str(screen_num)

        parts.append(
            f'<div class="step {cls}">'
            f'<div class="step-number">{num}</div>'
            f'<div class="step-label">{label}</div>'
            f'</div>'
        )
        if i < len(STEPS) - 1:
            line_cls = "step-done" if screen_num < current_screen else "step-pending"
            parts.append(f'<div class="step-line" style="background: {"#0f766e" if screen_num < current_screen else "#e5e7eb"};"></div>')

    st.markdown(f'<div class="step-container">{"".join(parts)}</div>', unsafe_allow_html=True)


def init_session_state():
    """Initialise les variables de session Streamlit."""
    defaults = {
        "screen": 1,
        "thread_id": None,
        "patient_name": "",
        "patient_age": 30,
        "initial_case": "",
        "current_question": "",
        "question_number": 0,
        "questions_and_answers": [],
        "diagnostic_summary": "",
        "interim_care": "",
        "physician_treatment": "",
        "final_report": "",
        "final_report_json": {},
        "consultation_status": "not_started",
        "error_message": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def api_call(method: str, endpoint: str, json_data: dict = None, params: dict = None) -> dict:
    """Effectue un appel API vers le backend FastAPI avec gestion d'erreurs."""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=120)
        elif method == "POST":
            response = requests.post(url, json=json_data, timeout=120)
        else:
            return {"error": f"Methode HTTP non supportee : {method}"}

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return {"error": response.json().get("detail", "Ressource non trouvee.")}
        else:
            return {"error": f"Erreur serveur ({response.status_code}): {response.json().get('detail', 'Erreur inconnue')}"}
    except requests.ConnectionError:
        return {
            "error": (
                "Impossible de se connecter au serveur backend. "
                f"Verifiez que le serveur FastAPI est demarre sur {API_BASE_URL}"
            )
        }
    except requests.Timeout:
        return {"error": "Le serveur backend n'a pas repondu dans le delai imparti."}
    except Exception as e:
        return {"error": f"Erreur inattendue : {str(e)}"}


def _pdf_text(value) -> str:
    """Prepare text for ReportLab paragraphs."""
    if value is None:
        return "N/A"
    text = str(value)
    replacements = {
        "\u26a0\ufe0f": "Attention:",
        "\u26a0": "Attention:",
        "\u2192": "->",
        "\u2014": "-",
        "\u2013": "-",
        "\u2022": "-",
        "\u2705": "",
        "\U0001f4e5": "",
        "\U0001f3e5": "",
        "\U0001fa7a": "",
        "\U0001f4cb": "",
        "\U0001f504": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return escape(text).replace("\n", "<br/>")


def build_report_pdf(report_json: dict, thread_id: str) -> bytes:
    """Build a professional PDF version of the final clinical report."""
    buffer = BytesIO()
    report_reference = f"SMA-{thread_id[:8].upper()}" if thread_id else "SMA-UNKNOWN"
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
        title="Rapport Clinique Final",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f766e"),
        spaceAfter=10,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#5D6D7E"),
        spaceAfter=16,
    )
    section_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.white,
        backColor=colors.HexColor("#0f766e"),
        borderPadding=(6, 8, 6, 8),
        spaceBefore=10,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#1F2933"),
        spaceAfter=7,
    )
    small_style = ParagraphStyle(
        "Small",
        parent=body_style,
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#5D6D7E"),
    )
    warning_style = ParagraphStyle(
        "Warning",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#922B21"),
        backColor=colors.HexColor("#FDEDEC"),
        borderColor=colors.HexColor("#E74C3C"),
        borderWidth=0.8,
        borderPadding=8,
    )

    patient_info = report_json.get("patient_info", {})
    qa_items = report_json.get("questions_and_answers", [])
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")

    story = [
        Paragraph("RAPPORT CLINIQUE FINAL", title_style),
        Paragraph(
            "Systeme multi-agents d'orientation clinique preliminaire - Simulation academique",
            subtitle_style,
        ),
    ]

    meta_table = Table(
        [
            [
                Paragraph("<b>Patient</b>", small_style),
                Paragraph(_pdf_text(patient_info.get("name", "N/A")), body_style),
                Paragraph("<b>Age</b>", small_style),
                Paragraph(_pdf_text(f"{patient_info.get('age', 'N/A')} ans"), body_style),
            ],
            [
                Paragraph("<b>Reference</b>", small_style),
                Paragraph(_pdf_text(report_reference), body_style),
                Paragraph("<b>Date</b>", small_style),
                Paragraph(_pdf_text(generated_at), body_style),
            ],
            [
                Paragraph("<b>ID session</b>", small_style),
                Paragraph(_pdf_text(thread_id), body_style),
                "",
                "",
            ],
        ],
        colWidths=[2.0 * cm, 6.1 * cm, 1.7 * cm, 6.0 * cm],
    )
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdfa")),
                ("SPAN", (1, 2), (3, 2)),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#99f6e4")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#ccfbf1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([meta_table, Spacer(1, 10)])

    story.append(Paragraph("1. Motif Initial", section_style))
    story.append(Paragraph(_pdf_text(patient_info.get("initial_case", "N/A")), body_style))

    story.append(Paragraph("2. Anamnese - Questions et Reponses", section_style))
    qa_rows = [
        [
            Paragraph("<b>#</b>", small_style),
            Paragraph("<b>Question</b>", small_style),
            Paragraph("<b>Reponse</b>", small_style),
        ]
    ]
    for idx, qa in enumerate(qa_items, start=1):
        qa_rows.append(
            [
                Paragraph(str(idx), body_style),
                Paragraph(_pdf_text(qa.get("question", "")), body_style),
                Paragraph(_pdf_text(qa.get("answer", "")), body_style),
            ]
        )
    qa_table = Table(qa_rows, colWidths=[1.0 * cm, 7.2 * cm, 7.6 * cm], repeatRows=1)
    qa_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ccfbf1")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#134e4a")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#99f6e4")),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#ccfbf1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(qa_table)

    sections = [
        ("3. Synthese Clinique Preliminaire", report_json.get("diagnostic_summary", "N/A")),
        ("4. Recommandation Intermediaire", report_json.get("interim_care", "N/A")),
        ("5. Avis du Medecin Traitant", report_json.get("physician_treatment", "N/A")),
        ("6. Conclusion Generale", report_json.get("conclusion", "N/A")),
    ]
    for title, content in sections:
        story.append(Paragraph(title, section_style))
        story.append(Paragraph(_pdf_text(content), body_style))

    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "AVERTISSEMENT LEGAL - Ce rapport est produit dans le cadre d'un exercice academique. "
            "Il ne constitue pas un avis medical professionnel et ne remplace pas une consultation medicale.",
            warning_style,
        )
    )

    def add_footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#99f6e4"))
        canvas.line(document.leftMargin, 1.05 * cm, A4[0] - document.rightMargin, 1.05 * cm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#5D6D7E"))
        canvas.drawString(document.leftMargin, 0.65 * cm, "SMA Clinique - Rapport academique simule")
        canvas.drawRightString(A4[0] - document.rightMargin, 0.65 * cm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    return buffer.getvalue()


def render_sidebar():
    """Affiche la barre laterale."""
    with st.sidebar:
        st.markdown("# SMA Clinique")
        st.markdown("Orientation medicale simulee")
        st.markdown("---")

        current_status = st.session_state.get("consultation_status", "not_started")
        status_labels = {
            "not_started": "Non demarree",
            "started": "Demarree",
            "questioning": "Questionnaire en cours",
            "awaiting_physician": "Attente du medecin",
            "report_generated": "Rapport en generation",
            "completed": "Terminee",
        }
        st.markdown(f"**Statut :** {status_labels.get(current_status, current_status)}")

        if st.session_state.get("thread_id"):
            st.markdown(f"**Session :** `{st.session_state['thread_id'][:8]}`")

        if st.session_state.get("question_number", 0) > 0:
            st.markdown("---")
            st.markdown("**Progression**")
            progress = min(st.session_state["question_number"] / 5, 1.0)
            st.progress(progress)
            st.markdown(f"Question {min(st.session_state['question_number'], 5)} / 5")

        if st.session_state.get("patient_name"):
            st.markdown("---")
            st.markdown("**Patient**")
            st.markdown(f"{st.session_state['patient_name']}, {st.session_state['patient_age']} ans")

        st.markdown("---")
        st.markdown(
            '<div class="disclaimer">'
            "Ce systeme est un exercice academique. "
            "Il ne remplace pas une consultation medicale professionnelle."
            "</div>",
            unsafe_allow_html=True,
        )


def screen_patient_intake():
    """Ecran 1 : Saisie du cas initial patient."""
    st.markdown(
        '<div class="app-header">'
        "<h1>Nouvelle Consultation</h1>"
        "<p>Remplissez les informations du patient pour demarrer le questionnaire clinique</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    render_steps(1)

    col1, col2 = st.columns([3, 2], gap="large")

    with col1:
        st.markdown("#### Informations du patient")

        patient_name = st.text_input(
            "Nom complet",
            value=st.session_state.get("patient_name", ""),
            placeholder="Ex : Mohamed Alami",
        )

        patient_age = st.number_input(
            "Age",
            min_value=1,
            max_value=120,
            value=st.session_state.get("patient_age", 30),
            step=1,
        )

        initial_case = st.text_area(
            "Motif de consultation",
            value=st.session_state.get("initial_case", ""),
            placeholder="Decrivez les symptomes ou le motif de consultation (minimum 20 caracteres)...",
            height=140,
        )

        if st.session_state.get("error_message"):
            st.error(st.session_state["error_message"])

        if st.button("Demarrer la consultation", type="primary", use_container_width=True):
            if not patient_name.strip():
                st.error("Veuillez entrer le nom du patient.")
                return
            if not initial_case.strip() or len(initial_case.strip()) < 20:
                st.error("La description du cas doit contenir au moins 20 caracteres.")
                return

            with st.spinner("Creation de la session en cours..."):
                session_result = api_call("POST", "/sessions/start")
                if "error" in session_result:
                    st.error(session_result["error"])
                    return

                thread_id = session_result["thread_id"]

                start_result = api_call("POST", "/consultation/start", {
                    "thread_id": thread_id,
                    "patient_name": patient_name.strip(),
                    "patient_age": patient_age,
                    "initial_case": initial_case.strip(),
                })

                if "error" in start_result:
                    st.error(start_result["error"])
                    return

                st.session_state["thread_id"] = thread_id
                st.session_state["patient_name"] = patient_name.strip()
                st.session_state["patient_age"] = patient_age
                st.session_state["initial_case"] = initial_case.strip()
                st.session_state["current_question"] = start_result.get("question", "")
                st.session_state["question_number"] = start_result.get("question_number", 1)
                st.session_state["consultation_status"] = "questioning"
                st.session_state["screen"] = 2
                st.session_state["error_message"] = ""
                st.rerun()

    with col2:
        st.markdown(
            '<div class="info-card">'
            "<h4>Comment ca fonctionne</h4>"
            "<p>"
            "<strong>1.</strong> Remplissez les informations patient<br>"
            "<strong>2.</strong> Repondez a 5 questions cliniques<br>"
            "<strong>3.</strong> Le medecin valide et donne son avis<br>"
            "<strong>4.</strong> Un rapport final structure est genere<br>"
            "</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="info-card">'
            "<h4>Technologies utilisees</h4>"
            "<p>"
            "LangGraph &bull; FastAPI &bull; Groq LLM<br>"
            "MCP Server &bull; Streamlit &bull; SQLite<br>"
            "Pydantic &bull; ReportLab (PDF)"
            "</p>"
            "</div>",
            unsafe_allow_html=True,
        )


def screen_patient_qa():
    """Ecran 2 : Questions / Reponses Patient."""
    st.markdown(
        '<div class="app-header">'
        "<h1>Questionnaire Clinique</h1>"
        "<p>Repondez aux questions pour permettre l'orientation clinique preliminaire</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    render_steps(2)

    question_number = st.session_state.get("question_number", 1)
    progress = min(question_number / 5, 1.0)
    st.progress(progress)

    st.markdown(
        f'<div class="metric-row">'
        f'<div class="metric-card"><div class="metric-value">{min(question_number, 5)}/5</div><div class="metric-label">Question actuelle</div></div>'
        f'<div class="metric-card"><div class="metric-value">{len(st.session_state.get("questions_and_answers", []))}</div><div class="metric-label">Reponses donnees</div></div>'
        f'<div class="metric-card"><div class="metric-value">{5 - min(question_number, 5)}</div><div class="metric-label">Questions restantes</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    current_question = st.session_state.get("current_question", "")
    if current_question:
        st.markdown(
            f'<div class="question-bubble">'
            f'<div class="q-label">Question {min(question_number, 5)} sur 5</div>'
            f'<div class="q-text">{current_question}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if st.session_state.get("questions_and_answers"):
        with st.expander("Reponses precedentes", expanded=False):
            for i, qa in enumerate(st.session_state["questions_and_answers"]):
                st.markdown(
                    f'<div class="qa-item">'
                    f'<div class="qa-q">Q{i+1}. {qa.get("question", "")}</div>'
                    f'<div class="qa-a">{qa.get("answer", "")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    answer = st.text_area(
        "Votre reponse",
        placeholder="Saisissez votre reponse ici...",
        height=100,
        key=f"answer_q{question_number}",
    )

    if st.session_state.get("error_message"):
        st.error(st.session_state["error_message"])

    if st.button("Envoyer la reponse", type="primary", use_container_width=True):
        if not answer.strip():
            st.error("Veuillez saisir une reponse avant de continuer.")
            return

        with st.spinner("Traitement de la reponse..."):
            result = api_call("POST", "/consultation/resume", {
                "thread_id": st.session_state["thread_id"],
                "answer": answer.strip(),
                "role": "patient",
            })

            if "error" in result:
                st.error(result["error"])
                return

            status = result.get("status", "")

            # Append Q&A only after successful API response
            qa_list = list(st.session_state.get("questions_and_answers", []))
            if len(qa_list) < 5:
                qa_list.append({
                    "question": current_question,
                    "answer": answer.strip(),
                })
                st.session_state["questions_and_answers"] = qa_list

            if status == "awaiting_physician":
                st.session_state["diagnostic_summary"] = result.get("diagnostic_summary", "")
                st.session_state["interim_care"] = result.get("interim_care", "")
                st.session_state["consultation_status"] = "awaiting_physician"
                st.session_state["question_number"] = 5
                st.session_state["screen"] = 3
                st.session_state["error_message"] = ""
                st.rerun()
            elif status == "questioning":
                st.session_state["current_question"] = result.get("question", "")
                st.session_state["question_number"] = result.get("question_number", question_number + 1)
                st.session_state["error_message"] = ""
                st.rerun()


def screen_physician_review():
    """Ecran 3 : Revue Medecin (HITL)."""
    st.markdown(
        '<div class="app-header">'
        "<h1>Revue Medecin</h1>"
        "<p>Human-in-the-Loop — Le medecin examine la synthese et donne son avis</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    render_steps(3)

    st.markdown(
        '<div class="physician-header">'
        '<div class="ph-icon">&#9202;</div>'
        '<div>'
        '<div class="ph-text">En attente de la revue medicale</div>'
        '<div class="ph-sub">Le graphe LangGraph est en pause (interrupt_before=physician_review)</div>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("#### Dossier patient")

        st.markdown(
            '<div class="card">'
            f'<strong>{st.session_state.get("patient_name", "N/A")}</strong>, '
            f'{st.session_state.get("patient_age", "N/A")} ans<br>'
            f'<em>{st.session_state.get("initial_case", "N/A")}</em>'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown("##### Questions et Reponses")
        for i, qa in enumerate(st.session_state.get("questions_and_answers", [])):
            st.markdown(
                f'<div class="qa-item">'
                f'<div class="qa-q">Q{i+1}. {qa.get("question", "")}</div>'
                f'<div class="qa-a">{qa.get("answer", "")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    with col2:
        diagnostic = st.session_state.get("diagnostic_summary", "")
        if diagnostic:
            st.markdown(
                f'<div class="summary-card summary-diag">'
                f'<h5>Synthese clinique preliminaire</h5>'
                f'<p>{diagnostic}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )

        interim = st.session_state.get("interim_care", "")
        if interim:
            st.markdown(
                f'<div class="summary-card summary-care">'
                f'<h5>Recommandation intermediaire</h5>'
                f'<p>{interim}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown("#### Avis du medecin traitant")
    physician_input = st.text_area(
        "Traitement ou conduite a tenir",
        placeholder="Saisissez votre avis medical, traitement recommande ou conduite a tenir...",
        height=180,
        key="physician_input",
    )

    if st.session_state.get("error_message"):
        st.error(st.session_state["error_message"])

    if st.button("Valider la revue medicale", type="primary", use_container_width=True):
        if not physician_input.strip():
            st.error("Veuillez saisir votre avis medical avant de valider.")
            return

        with st.spinner("Generation du rapport final en cours..."):
            result = api_call("POST", "/consultation/resume", {
                "thread_id": st.session_state["thread_id"],
                "answer": physician_input.strip(),
                "role": "physician",
            })

            if "error" in result:
                st.error(result["error"])
                return

            st.session_state["physician_treatment"] = physician_input.strip()

            max_polls = 30
            for _ in range(max_polls):
                status_result = api_call("GET", f"/consultation/{st.session_state['thread_id']}")
                if "error" in status_result:
                    break
                if status_result.get("consultation_status") == "completed" or status_result.get("has_final_report"):
                    break
                time.sleep(2)

            st.session_state["consultation_status"] = "completed"
            st.session_state["screen"] = 4
            st.session_state["error_message"] = ""
            st.rerun()


def screen_final_report():
    """Ecran 4 : Rapport Final."""
    st.markdown(
        '<div class="app-header">'
        "<h1>Rapport Clinique Final</h1>"
        "<p>Consultation terminee — voici le rapport structure genere par le systeme multi-agents</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    render_steps(4)

    report_result = api_call("GET", f"/consultation/{st.session_state['thread_id']}/report")

    if "error" in report_result:
        st.error(f"Erreur : {report_result['error']}")
        st.info("Le rapport n'est peut-etre pas encore pret.")
        if st.button("Rafraichir"):
            st.rerun()
        return

    final_report_json = report_result.get("final_report_json", {})
    patient_info = final_report_json.get("patient_info", {})

    # Metrics
    st.markdown(
        f'<div class="metric-row">'
        f'<div class="metric-card"><div class="metric-value">{patient_info.get("name", "N/A")}</div><div class="metric-label">Patient</div></div>'
        f'<div class="metric-card"><div class="metric-value">{patient_info.get("age", "N/A")} ans</div><div class="metric-label">Age</div></div>'
        f'<div class="metric-card"><div class="metric-value">{len(final_report_json.get("questions_and_answers", []))}</div><div class="metric-label">Questions</div></div>'
        f'<div class="metric-card"><div class="metric-value">Terminee</div><div class="metric-label">Statut</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Report sections
    section_data = [
        ("Motif initial", patient_info.get("initial_case", "N/A")),
        ("Synthese clinique preliminaire", final_report_json.get("diagnostic_summary", "N/A")),
        ("Recommandation intermediaire", final_report_json.get("interim_care", "N/A")),
        ("Avis du medecin traitant", final_report_json.get("physician_treatment", "N/A")),
        ("Conclusion generale", final_report_json.get("conclusion", "N/A")),
    ]

    # Q&A section
    qa_items = final_report_json.get("questions_and_answers", [])
    if qa_items:
        st.markdown(
            '<div class="report-section">'
            '<div class="report-section-title">Anamnese — Questions et Reponses</div>'
            '<div class="report-section-body">' +
            "".join(
                f'<div class="qa-item">'
                f'<div class="qa-q">Q{i+1}. {qa.get("question", "")}</div>'
                f'<div class="qa-a">{qa.get("answer", "")}</div>'
                f'</div>'
                for i, qa in enumerate(qa_items)
            ) +
            '</div></div>',
            unsafe_allow_html=True,
        )

    for title, content in section_data:
        st.markdown(
            f'<div class="report-section">'
            f'<div class="report-section-title">{title}</div>'
            f'<div class="report-section-body">{content}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Legal disclaimer
    st.markdown(
        '<div class="disclaimer" style="margin: 1.5rem 0;">'
        "<strong>AVERTISSEMENT LEGAL</strong> — Ce rapport est produit dans le cadre d'un exercice academique. "
        "Il ne constitue pas un avis medical professionnel et ne remplace pas une consultation medicale."
        "</div>",
        unsafe_allow_html=True,
    )

    # Actions
    col1, col2 = st.columns(2, gap="large")
    with col1:
        if st.button("Nouvelle consultation", type="primary", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    with col2:
        if final_report_json:
            pdf_bytes = build_report_pdf(
                final_report_json,
                st.session_state.get("thread_id", "unknown"),
            )
            st.download_button(
                label="Telecharger le rapport PDF",
                data=pdf_bytes,
                file_name=f"rapport_clinique_{st.session_state.get('thread_id', 'unknown')[:8]}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )


def main():
    """Point d'entree principal de l'application Streamlit."""
    init_session_state()
    render_sidebar()

    screen = st.session_state.get("screen", 1)

    if screen == 1:
        screen_patient_intake()
    elif screen == 2:
        screen_patient_qa()
    elif screen == 3:
        screen_physician_review()
    elif screen == 4:
        screen_final_report()
    else:
        st.session_state["screen"] = 1
        st.rerun()


if __name__ == "__main__":
    main()
