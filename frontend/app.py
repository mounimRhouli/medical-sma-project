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
    page_title="SMA Clinique — Orientation Médicale Simulée",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1B4F72;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 3px solid #2E86C1;
        margin-bottom: 1.5rem;
    }
    .disclaimer-box {
        background-color: #FDEDEC;
        border-left: 5px solid #E74C3C;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 8px 8px 0;
    }
    .info-box {
        background-color: #EBF5FB;
        border-left: 5px solid #2E86C1;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    .success-box {
        background-color: #EAFAF1;
        border-left: 5px solid #27AE60;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


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
            response = requests.get(url, params=params, timeout=60)
        elif method == "POST":
            response = requests.post(url, json=json_data, timeout=60)
        else:
            return {"error": f"Méthode HTTP non supportée : {method}"}

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return {"error": response.json().get("detail", "Ressource non trouvée.")}
        else:
            return {"error": f"Erreur serveur ({response.status_code}): {response.json().get('detail', 'Erreur inconnue')}"}
    except requests.ConnectionError:
        return {
            "error": (
                "Impossible de se connecter au serveur backend. "
                "Vérifiez que le serveur FastAPI est démarré sur "
                f"{API_BASE_URL}"
            )
        }
    except requests.Timeout:
        return {"error": "Le serveur backend n'a pas répondu dans le délai imparti."}
    except Exception as e:
        return {"error": f"Erreur inattendue : {str(e)}"}


def _pdf_text(value) -> str:
    """Prepare text for ReportLab paragraphs."""
    if value is None:
        return "N/A"
    text = str(value)
    replacements = {
        "⚠️": "Attention:",
        "⚠": "Attention:",
        "→": "->",
        "—": "-",
        "–": "-",
        "•": "-",
        "✅": "",
        "📥": "",
        "🏥": "",
        "🩺": "",
        "📋": "",
        "🔄": "",
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
        textColor=colors.HexColor("#173B57"),
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
        backColor=colors.HexColor("#1B4F72"),
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
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F8FB")),
                ("SPAN", (1, 2), (3, 2)),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#B7C9D6")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6E2EA")),
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
    qa_rows = [[Paragraph("<b>#</b>", small_style), Paragraph("<b>Question</b>", small_style), Paragraph("<b>Reponse</b>", small_style)]]
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
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCECF7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#173B57")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#B7C9D6")),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D6E2EA")),
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
        canvas.setStrokeColor(colors.HexColor("#B7C9D6"))
        canvas.line(document.leftMargin, 1.05 * cm, A4[0] - document.rightMargin, 1.05 * cm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#5D6D7E"))
        canvas.drawString(document.leftMargin, 0.65 * cm, "SMA Clinique - Rapport academique simule")
        canvas.drawRightString(A4[0] - document.rightMargin, 0.65 * cm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    return buffer.getvalue()


def render_sidebar():
    """Affiche la barre latérale avec les informations de la consultation."""
    with st.sidebar:
        st.markdown("## 🏥 SMA Clinique")
        st.markdown("---")

        st.markdown("### État de la consultation")
        status_labels = {
            "not_started": "🔵 Non démarrée",
            "started": "🟡 Démarrée",
            "questioning": "🟡 Questionnaire en cours",
            "awaiting_physician": "🟠 Attente du médecin",
            "report_generated": "🟢 Rapport en génération",
            "completed": "🟢 Terminée",
        }
        current_status = st.session_state.get("consultation_status", "not_started")
        st.markdown(f"**Statut :** {status_labels.get(current_status, current_status)}")

        if st.session_state.get("thread_id"):
            st.markdown(f"**Session :** `{st.session_state['thread_id'][:8]}...`")

        if st.session_state.get("question_number", 0) > 0:
            st.markdown("### Progression du questionnaire")
            progress = min(st.session_state["question_number"] / 5, 1.0)
            st.progress(progress)
            st.markdown(f"Question {min(st.session_state['question_number'], 5)}/5")

        if st.session_state.get("patient_name"):
            st.markdown("### Informations patient")
            st.markdown(f"**Nom :** {st.session_state['patient_name']}")
            st.markdown(f"**Âge :** {st.session_state['patient_age']} ans")

        st.markdown("---")
        st.markdown(
            '<div class="disclaimer-box">'
            "⚠️ <strong>Avertissement</strong><br>"
            "Ce système est un exercice académique. "
            "Il ne remplace pas une consultation médicale."
            "</div>",
            unsafe_allow_html=True,
        )


def screen_patient_intake():
    """Écran 1 : Saisie du cas initial patient."""
    st.markdown('<div class="main-header">Nouvelle Consultation — Saisie du Patient</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Informations du patient")

        patient_name = st.text_input(
            "Nom complet du patient",
            value=st.session_state.get("patient_name", ""),
            placeholder="Entrez le nom du patient...",
        )

        patient_age = st.number_input(
            "Âge du patient",
            min_value=1,
            max_value=120,
            value=st.session_state.get("patient_age", 30),
            step=1,
        )

        initial_case = st.text_area(
            "Description du cas initial / motif de consultation",
            value=st.session_state.get("initial_case", ""),
            placeholder="Décrivez les symptômes ou le motif de consultation (minimum 20 caractères)...",
            height=150,
        )

        if st.session_state.get("error_message"):
            st.error(st.session_state["error_message"])

        if st.button("🩺 Démarrer la consultation", type="primary", use_container_width=True):
            if not patient_name.strip():
                st.error("Veuillez entrer le nom du patient.")
                return
            if not initial_case.strip() or len(initial_case.strip()) < 20:
                st.error("La description du cas doit contenir au moins 20 caractères.")
                return

            with st.spinner("Création de la session..."):
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
        st.markdown("### Guide")
        st.markdown(
            '<div class="info-box">'
            "<strong>Processus de consultation :</strong><br><br>"
            "1️⃣ Saisie des informations patient<br>"
            "2️⃣ Questionnaire clinique (5 questions)<br>"
            "3️⃣ Revue par le médecin traitant<br>"
            "4️⃣ Génération du rapport final<br>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="disclaimer-box">'
            "⚠️ Ce système est une simulation académique. "
            "Les résultats ne constituent pas un avis médical professionnel."
            "</div>",
            unsafe_allow_html=True,
        )


def screen_patient_qa():
    """Écran 2 : Questions / Réponses Patient."""
    st.markdown('<div class="main-header">Questionnaire Clinique — Patient</div>', unsafe_allow_html=True)

    question_number = st.session_state.get("question_number", 1)
    progress = min(question_number / 5, 1.0)
    st.progress(progress)
    st.markdown(f"**Question {min(question_number, 5)} sur 5**")

    st.markdown("---")

    current_question = st.session_state.get("current_question", "")
    if current_question:
        st.info(f"🩺 **{current_question}**")

    if st.session_state.get("questions_and_answers"):
        with st.expander("📋 Réponses précédentes", expanded=False):
            for qa in st.session_state["questions_and_answers"]:
                st.markdown(f"**Q :** {qa.get('question', '')}")
                st.markdown(f"**R :** {qa.get('answer', '')}")
                st.markdown("---")

    answer = st.text_area(
        "Votre réponse",
        placeholder="Saisissez votre réponse ici...",
        height=100,
        key=f"answer_q{question_number}",
    )

    if st.session_state.get("error_message"):
        st.error(st.session_state["error_message"])

    if st.button("📤 Répondre", type="primary", use_container_width=True):
        if not answer.strip():
            st.error("Veuillez saisir une réponse avant de continuer.")
            return

        with st.spinner("Envoi de la réponse..."):
            qa_list = list(st.session_state.get("questions_and_answers", []))
            qa_list.append({
                "question": current_question,
                "answer": answer.strip(),
            })
            st.session_state["questions_and_answers"] = qa_list

            result = api_call("POST", "/consultation/resume", {
                "thread_id": st.session_state["thread_id"],
                "answer": answer.strip(),
                "role": "patient",
            })

            if "error" in result:
                st.error(result["error"])
                return

            status = result.get("status", "")

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
    """Écran 3 : Revue Médecin (HITL)."""
    st.markdown('<div class="main-header">Revue Médecin — Human-in-the-Loop</div>', unsafe_allow_html=True)

    st.warning("⏳ **En attente de la revue du médecin traitant**")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Informations Patient")
        st.markdown(
            f"**Nom :** {st.session_state.get('patient_name', 'N/A')}<br>"
            f"**Âge :** {st.session_state.get('patient_age', 'N/A')} ans<br>"
            f"**Cas initial :** {st.session_state.get('initial_case', 'N/A')}",
            unsafe_allow_html=True,
        )

        st.markdown("### Questions et Réponses")
        for i, qa in enumerate(st.session_state.get("questions_and_answers", [])):
            st.markdown(f"**Q{i+1} :** {qa.get('question', '')}")
            st.markdown(f"**R{i+1} :** {qa.get('answer', '')}")

    with col2:
        st.markdown("### Synthèse Clinique Préliminaire")
        diagnostic = st.session_state.get("diagnostic_summary", "")
        if diagnostic:
            st.info(diagnostic)
        else:
            st.warning("Synthèse non disponible.")

        st.markdown("### Recommandation Intermédiaire")
        interim = st.session_state.get("interim_care", "")
        if interim:
            st.success(interim)
        else:
            st.warning("Recommandation non disponible.")

    st.markdown("---")
    st.markdown("### Avis du médecin traitant")
    physician_input = st.text_area(
        "Traitement ou conduite à tenir recommandée par le médecin",
        placeholder="Saisissez votre avis médical, traitement recommandé ou conduite à tenir...",
        height=200,
        key="physician_input",
    )

    if st.session_state.get("error_message"):
        st.error(st.session_state["error_message"])

    if st.button("✅ Valider la revue médicale", type="primary", use_container_width=True):
        if not physician_input.strip():
            st.error("Veuillez saisir votre avis médical avant de valider.")
            return

        with st.spinner("Génération du rapport final en cours..."):
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
            for poll_count in range(max_polls):
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
    """Écran 4 : Rapport Final."""
    st.markdown('<div class="main-header">Rapport Clinique Final</div>', unsafe_allow_html=True)

    report_result = api_call("GET", f"/consultation/{st.session_state['thread_id']}/report")

    if "error" in report_result:
        st.error(f"Erreur lors de la récupération du rapport : {report_result['error']}")
        st.info("Le rapport n'est peut-être pas encore prêt. Veuillez patienter...")
        if st.button("🔄 Rafraîchir"):
            st.rerun()
        return

    final_report = report_result.get("final_report", "")
    final_report_json = report_result.get("final_report_json", {})

    st.text_area(
        "Rapport complet",
        value=final_report,
        height=600,
        disabled=True,
        key="report_display",
    )

    st.markdown("---")
    st.markdown("### Sections détaillées")

    if final_report_json:
        with st.expander("1. Informations Patient"):
            patient_info = final_report_json.get("patient_info", {})
            st.markdown(f"**Nom :** {patient_info.get('name', 'N/A')}")
            st.markdown(f"**Âge :** {patient_info.get('age', 'N/A')} ans")
            st.markdown(f"**Cas initial :** {patient_info.get('initial_case', 'N/A')}")

        with st.expander("2. Anamnèse — Questions & Réponses"):
            for i, qa in enumerate(final_report_json.get("questions_and_answers", [])):
                st.markdown(f"**Q{i+1} :** {qa.get('question', '')}")
                st.markdown(f"**R{i+1} :** {qa.get('answer', '')}")
                st.markdown("---")

        with st.expander("3. Synthèse Clinique Préliminaire"):
            st.info(final_report_json.get("diagnostic_summary", "N/A"))

        with st.expander("4. Recommandation Intermédiaire"):
            st.success(final_report_json.get("interim_care", "N/A"))

        with st.expander("5. Avis du Médecin Traitant"):
            st.markdown(final_report_json.get("physician_treatment", "N/A"))

        with st.expander("6. Conclusion Générale"):
            st.markdown(final_report_json.get("conclusion", "N/A"))

    st.markdown("---")
    st.error(
        "⚠️ **AVERTISSEMENT LÉGAL** — Ce système ne remplace pas une consultation médicale. "
        "Ce rapport est produit dans le cadre d'un exercice académique. "
        "Il ne constitue pas un avis médical professionnel."
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Nouvelle consultation", type="primary", use_container_width=True):
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
                label="📥 Télécharger le rapport (.pdf)",
                data=pdf_bytes,
                file_name=f"rapport_clinique_{st.session_state.get('thread_id', 'unknown')[:8]}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )


def main():
    """Point d'entrée principal de l'application Streamlit."""
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
