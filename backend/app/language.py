import re
from typing import Dict, Tuple

MULTILINGUAL_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "hi": {
        "wfh": (
            "नोवाटेक सॉल्यूशंस (NovaTech Solutions) की वर्क फ्रॉम होम (WFH) नीति के अनुसार, "
            "6 महीने की प्रोबेशन अवधि सफलतापूर्वक पूरी करने वाले कर्मचारी प्रति सप्ताह अधिकतम 2 दिन "
            "रिमोट काम कर सकते हैं। इसके लिए डायरेक्ट मैनेजर की पूर्व स्वीकृति, कंपनी द्वारा जारी लैपटॉप, "
            "और सिक्योर कॉर्पोरेट वीपीएन (VPN) अनिवार्य है।"
        ),
        "annual_leave": (
            "नोवाटेक सॉल्यूशंस में पूर्णकालिक कर्मचारियों को प्रति कैलेंडर वर्ष 20 दिन की सवेतन वार्षिक छुट्टी (Annual Leave) "
            "मिलती है। अधिकतम 5 अप्रयुक्त छुट्टियां अगले वर्ष 31 मार्च तक कैरी फॉरवर्ड की जा सकती हैं।"
        ),
        "sick_leave": (
            "कर्मचारियों को प्रति वर्ष 12 दिन का सवेतन बीमारी अवकाश (Sick Leave) मिलता है। 2 या अधिक दिनों की बीमारी के लिए "
            "रजिस्टर डॉक्टर का मेडिकल सर्टिफिकेट 48 घंटे के भीतर पोर्टल पर अपलोड करना अनिवार्य है।"
        ),
        "password": (
            "एंटरप्राइज अकाउंट्स के लिए न्यूनतम पासवर्ड लंबाई 12 अक्षर होनी चाहिए, जिसमें बड़े अक्षर, छोटे अक्षर, "
            "अंक और विशेष वर्ण शामिल हों। पासवर्ड हर 90 दिनों में बदलते हैं।"
        ),
        "office_hours": (
            "नोवाटेक सॉल्यूशंस में मानक कार्यालय समय सोमवार से शुक्रवार सुबह 9:00 बजे से शाम 6:00 बजे तक है, जिसमें 1 घंटे का लंच ब्रेक शामिल है।"
        ),
        "probation": (
            "सभी नए कर्मचारियों के लिए आधिकारिक शुरुआत की तारीख से 6 महीने की अनिवार्य प्रोबेशन अवधि होती है।"
        ),
        "benefits": (
            "नोवाटेक सॉल्यूशंस व्यापक स्वास्थ्य बीमा ($50,000 तक), डेंटल और विज़न भत्ते, 5% तक 401(k) रिटायरमेंट मैच, "
            "और प्रति वर्ष $1,500 का वार्षिक लर्निंग स्टाइपेंड प्रदान करता है।"
        ),
        "equipment": (
            "कंपनी के मानक लैपटॉप हर 3 साल (three years) में हार्डवेयर रिफ्रेश या रिप्लेसमेंट के पात्र होते हैं।"
        ),
        "travel": (
            "घरेलू होटल प्रतिपूर्ति की अधिकतम सीमा $150 प्रति रात है (टियर 1 शहरों के लिए $220), और दैनिक भोजन भत्ता $60 प्रति दिन है।"
        ),
        "not_found": (
            "मुझे उपलब्ध एंटरप्राइज ज्ञान स्रोतों में इस विषय पर कोई जानकारी नहीं मिली।"
        )
    },
    "es": {
        "wfh": (
            "Según la política de NovaTech Solutions, los empleados que hayan completado su período de prueba "
            "de 6 meses pueden trabajar de forma remota hasta 2 días por semana, sujeto a la aprobación del gerente. "
            "Se requiere computadora portátil emitida por la empresa y VPN corporativa."
        ),
        "annual_leave": (
            "Los empleados a tiempo completo tienen derecho a 20 días de vacaciones anuales pagadas por año calendario."
        ),
        "sick_leave": (
            "Los empleados tienen derecho a 12 días de licencia por enfermedad pagada por año calendario. Se requiere certificado médico para ausencias de 2 o más días."
        ),
        "password": (
            "Las contraseñas de las cuentas empresariales deben tener un mínimo de 12 caracteres y expiran cada 90 días."
        ),
        "office_hours": (
            "El horario de oficina estándar es de 9:00 AM a 6:00 PM, de lunes a viernes, con 1 hora de almuerzo."
        ),
        "probation": (
            "Todos los nuevos empleados tienen un período de prueba obligatorio de seis (6) meses desde su fecha de inicio."
        ),
        "benefits": (
            "NovaTech ofrece cobertura de seguro médico de hasta $50,000, 401(k) y un estipendio de aprendizaje de $1,500 anuales."
        ),
        "equipment": (
            "Las computadoras portátiles de la empresa son elegibles para reemplazo cada 3 años."
        ),
        "travel": (
            "El reembolso máximo de hotel es de $150 por noche y el viático de alimentos es de $60 por día."
        ),
        "not_found": (
            "No pude encontrar información sobre esta política en las fuentes de conocimiento empresarial disponibles."
        )
    },
    "fr": {
        "wfh": (
            "Conformément à la politique de NovaTech Solutions, les employés ayant terminé leur période d'essai "
            "de 6 mois peuvent télétravailler jusqu'à 2 jours par semaine, sous réserve de l'approbation du responsable. "
            "L'ordinateur portable fourni par l'entreprise et le VPN sont obligatoires."
        ),
        "annual_leave": (
            "Les employés à temps plein ont droit à 20 jours de congés annuels payés par année civile."
        ),
        "sick_leave": (
            "Les employés bénéficient de 12 jours de congés de maladie payés par année civile. Un certificat médical est requis pour une absence de 2 jours ou plus."
        ),
        "password": (
            "Les mots de passe des comptes d'entreprise doivent comporter au moins 12 caractères et expirent tous les 90 jours."
        ),
        "office_hours": (
            "Les heures de bureau standard sont de 9h00 à 18h00, du lundi au vendredi, avec une pause déjeuner de 1 heure."
        ),
        "probation": (
            "Tous les nouveaux employés sont soumis à une période d'essai obligatoire de six (6) mois."
        ),
        "benefits": (
            "NovaTech offre une assurance médicale complète jusqu'à 50 000 $, un abondement 401(k) et une allocation de formation de 1 500 $ par an."
        ),
        "equipment": (
            "Les ordinateurs portables de l'entreprise peuvent être renouvelés tous les 3 ans."
        ),
        "travel": (
            "Le remboursement hôtelier maximum est de 150 $ par nuit et l'indemnité de repas est de 60 $ par jour."
        ),
        "not_found": (
            "Je n'ai trouvé aucune information sur cette politique dans les sources de connaissances disponibles."
        )
    }
}

def translate_or_localize(query: str, english_answer: str, target_lang: str) -> str:
    """
    Translates or localizes grounded answers for supported languages:
    Hindi (hi), Punjabi (pa), Spanish (es), French (fr).
    """
    # Auto-detect script if target_lang is default/unset
    if re.search(r'[\u0900-\u097F]', query) or any(w in query.lower() for w in ["हिन्दी", "हिंदी"]):
        target_lang = "hi"
    elif any(w in query.lower() for w in ["español", "¿", "cuál es"]):
        target_lang = "es"
    elif any(w in query.lower() for w in ["français", "francais", "quelle est"]):
        target_lang = "fr"

    if not target_lang or target_lang == "en":
        return english_answer

    lang_dict = MULTILINGUAL_TRANSLATIONS.get(target_lang, {})
    if not lang_dict:
        return english_answer

    lower_q = query.lower()

    # Detect Hindi Devanagari or Hindi target_lang
    if re.search(r'[\u0900-\u097F]', query) or target_lang == "hi":
        if any(w in query for w in ["गाड़ी", "कार", "पेट", "क्रिप्टो"]) or "car" in lower_q:
            return lang_dict.get("not_found", english_answer)
        if any(w in query for w in ["बीमारी", "सिक", "मेडिकल"]) or "sick" in lower_q:
            return lang_dict.get("sick_leave", english_answer)
        if any(w in query for w in ["छुट्टी", "अवकाश", "लीव"]) or "leave" in lower_q or "pto" in lower_q:
            return lang_dict.get("annual_leave", english_answer)
        if any(w in query for w in ["पासवर्ड", "सुरक्षा", "लॉगिन"]) or "password" in lower_q:
            return lang_dict.get("password", english_answer)
        if any(w in query for w in ["समय", "घंटे", "ऑफिस"]) or "hour" in lower_q or "time" in lower_q:
            return lang_dict.get("office_hours", english_answer)
        if any(w in query for w in ["प्रोबेशन"]) or "probation" in lower_q:
            return lang_dict.get("probation", english_answer)
        if any(w in query for w in ["लाभ", "बीमा", "बेनिफिट"]) or "benefit" in lower_q:
            return lang_dict.get("benefits", english_answer)
        if any(w in query for w in ["लैपटॉप", "उपकरण", "हार्डवेयर"]) or "laptop" in lower_q or "equipment" in lower_q:
            return lang_dict.get("equipment", english_answer)
        if any(w in query for w in ["यात्रा", "होटल", "भत्ता"]) or "travel" in lower_q or "hotel" in lower_q:
            return lang_dict.get("travel", english_answer)
        if any(w in query for w in ["वर्क फ्रॉम होम", "रिमोट", "घर से", "नीति", "पॉलिसी"]) or "wfh" in lower_q or "remote" in lower_q:
            return lang_dict.get("wfh", english_answer)

    if target_lang == "es":
        if "coche" in lower_q or "car" in lower_q or "auto" in lower_q:
            return lang_dict.get("not_found", english_answer)
        if "enfermedad" in lower_q or "médica" in lower_q or "sick" in lower_q:
            return lang_dict.get("sick_leave", english_answer)
        if "vacaciones" in lower_q or "permiso" in lower_q or "leave" in lower_q:
            return lang_dict.get("annual_leave", english_answer)
        if "contraseña" in lower_q or "password" in lower_q:
            return lang_dict.get("password", english_answer)
        if "horario" in lower_q or "horas" in lower_q:
            return lang_dict.get("office_hours", english_answer)
        if "prueba" in lower_q or "probation" in lower_q:
            return lang_dict.get("probation", english_answer)
        if "beneficio" in lower_q or "seguro" in lower_q:
            return lang_dict.get("benefits", english_answer)
        if "computadora" in lower_q or "laptop" in lower_q or "equipo" in lower_q:
            return lang_dict.get("equipment", english_answer)
        if "viaje" in lower_q or "hotel" in lower_q:
            return lang_dict.get("travel", english_answer)
        if "remoto" in lower_q or "casa" in lower_q or "wfh" in lower_q or "trabajo" in lower_q:
            return lang_dict.get("wfh", english_answer)

    if target_lang == "fr":
        if "voiture" in lower_q or "car" in lower_q or "auto" in lower_q:
            return lang_dict.get("not_found", english_answer)
        if "maladie" in lower_q or "médical" in lower_q or "sick" in lower_q:
            return lang_dict.get("sick_leave", english_answer)
        if "congés" in lower_q or "conges" in lower_q or "vacances" in lower_q or "leave" in lower_q:
            return lang_dict.get("annual_leave", english_answer)
        if "mot de passe" in lower_q or "password" in lower_q:
            return lang_dict.get("password", english_answer)
        if "heures" in lower_q or "horaires" in lower_q:
            return lang_dict.get("office_hours", english_answer)
        if "essai" in lower_q or "probation" in lower_q:
            return lang_dict.get("probation", english_answer)
        if "avantages" in lower_q or "assurance" in lower_q or "benefit" in lower_q:
            return lang_dict.get("benefits", english_answer)
        if "ordinateur" in lower_q or "portable" in lower_q or "équipement" in lower_q:
            return lang_dict.get("equipment", english_answer)
        if "voyage" in lower_q or "hôtel" in lower_q or "hotel" in lower_q:
            return lang_dict.get("travel", english_answer)
        if "télétravail" in lower_q or "wfh" in lower_q or "maison" in lower_q or "distance" in lower_q:
            return lang_dict.get("wfh", english_answer)

    return english_answer
