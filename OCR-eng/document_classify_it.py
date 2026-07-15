import re

from collections import defaultdict


# =========================================================
# DOCUMENT PATTERNS
# =========================================================

DOCUMENT_PATTERNS = {

    "invoice": {

        "keywords": {

            "invoice": 5,
            "tax invoice": 8,
            "invoice number": 7,
            "invoice no": 7,
            "gst": 5,
            "gstin": 7,
            "bill to": 5,
            "ship to": 4,
            "qty": 4,
            "quantity": 4,
            "amount": 4,
            "subtotal": 5,
            "grand total": 8,
            "total": 4,
            "hsn": 5,
            "cgst": 5,
            "sgst": 5,
            "igst": 5,
            "purchase order": 6

        },

        "regex": [

            r"invoice\s*(number|no|#)",
            r"gstin",
            r"po\s*(number|no)",
            r"tax\s*invoice"

        ]

    },

    # =====================================================
    # BANK STATEMENT
    # =====================================================

    "bank_statement": {

        "keywords": {

            "account number": 7,
            "statement": 5,
            "withdrawal": 6,
            "deposit": 6,
            "balance": 5,
            "ifsc": 5,
            "transaction": 5,
            "credit": 5,
            "debit": 5,
            "opening balance": 7,
            "closing balance": 7,
            "bank statement": 8,
            "available balance": 6

        },

        "regex": [

            r"account\s*(number|no)",
            r"ifsc",
            r"txn\s*(id|ref)",
            r"available\s*balance"

        ]

    },

    
    # =====================================================
    # Certificate Analysis
    # =====================================================


    "certificate_of_analysis": {

        "keywords": {

            "certificate of analysis": 15,

            "coa": 8,

            "product name": 7,

            "lot no": 7,

            "batch no": 7,

            "mfg date": 7,

            "exp date": 7,

            "specification": 6,

            "physical state": 5,

            "specific gravity": 5,

            "acid value": 5,

            "peroxide value": 5,

            "iodine value": 5,

            "pesticide": 5,

            "heavy metal": 5,

            "arsenic": 5,

            "cadmium": 5,

            "lead": 5,

            "mercury": 5

        },

        "regex": [

            r"certificate\s*of\s*analysis",

            r"lot\s*no",

            r"batch\s*no",

            r"mfg\s*date",

            r"exp\s*date"

        ]

    },



    # =====================================================
    # PRESCRIPTION
    # =====================================================

    "prescription": {

        "keywords": {

            "rx": 8,
            "prescription": 8,
            "tablet": 5,
            "capsule": 5,
            "doctor": 4,
            "patient": 4,
            "dosage": 6,
            "medicine": 5,
            "drug": 5,
            "mg": 3,
            "ml": 3,
            "bp": 3,
            "diagnosis": 5,
            "take once daily": 6

        },

        "regex": [

            r"\d+\s*mg",
            r"\d+\s*ml",
            r"tab\.",
            r"cap\.",
            r"rx"

        ]

    },

    # =====================================================
    # LAB REPORT
    # =====================================================

    "lab_report": {

        "keywords": {

            "lab report": 8,
            "haemoglobin": 7,
            "hemoglobin": 7,
            "wbc": 7,
            "rbc": 7,
            "platelet": 7,
            "blood sugar": 6,
            "test result": 5,
            "reference range": 7,
            "pathology": 6,
            "specimen": 5,
            "biochemistry": 5,
            "test name": 5

        },

        "regex": [

            r"reference\s*range",
            r"test\s*name",
            r"result\s*unit",
            r"haemoglobin",
            r"hemoglobin"

        ]

    },

    # =====================================================
    # DISCHARGE SUMMARY
    # =====================================================

    "discharge_summary": {

        "keywords": {

            "discharge summary": 10,
            "admission date": 6,
            "discharge date": 6,
            "hospital": 4,
            "patient name": 4,
            "clinical summary": 7,
            "diagnosis": 5,
            "treatment": 5,
            "medical history": 5,
            "chief complaints": 6

        },

        "regex": [

            r"date\s*of\s*admission",
            r"date\s*of\s*discharge",
            r"clinical\s*summary"

        ]

    },

    # =====================================================
    # INSURANCE FORM
    # =====================================================

    "insurance_form": {

        "keywords": {

            "insurance": 8,
            "claim": 8,
            "policy number": 7,
            "insured": 6,
            "claim form": 8,
            "member id": 5,
            "tpa": 5,
            "sum insured": 7,
            "cashless": 6

        },

        "regex": [

            r"policy\s*(number|no)",
            r"claim\s*(id|number)",
            r"member\s*id"

        ]

    },

    # =====================================================
    # ID CARD
    # =====================================================

    "id_card": {

        "keywords": {

            "government of india": 10,
            "aadhaar": 10,
            "uid": 8,
            "dob": 5,
            "male": 3,
            "female": 3,
            "identity": 5,
            "year of birth": 5

        },

        "regex": [

            r"\d{4}\s\d{4}\s\d{4}",
            r"government\s*of\s*india"

        ]

    }

}


# =========================================================
# OCR TEXT NORMALIZATION
# =========================================================

def normalize_text(text):

    text = text.lower()

    # OCR cleanup
    text = text.replace("|", " ")
    text = text.replace(":", " ")
    text = text.replace(";", " ")

    # Remove extra symbols
    text = re.sub(

        r"[^a-z0-9\s\-\./]",

        " ",

        text

    )

    # Remove multiple spaces
    text = re.sub(

        r"\s+",

        " ",

        text

    )

    return text.strip()


# =========================================================
# KEYWORD SCORE
# =========================================================

def calculate_keyword_score(

    text,
    keywords

):

    score = 0

    matched_keywords = []

    for keyword, weight in keywords.items():

        occurrences = text.count(keyword)

        if occurrences > 0:

            weighted_score = occurrences * weight

            score += weighted_score

            matched_keywords.append({

                "keyword": keyword,

                "count": occurrences,

                "weight": weight,

                "score": weighted_score

            })

    return score, matched_keywords


# =========================================================
# REGEX SCORE
# =========================================================

def calculate_regex_score(

    text,
    regex_patterns

):

    score = 0

    matched_patterns = []

    for pattern in regex_patterns:

        matches = re.findall(

            pattern,

            text,

            re.IGNORECASE

        )

        if matches:

            regex_weight = 8

            regex_score = len(matches) * regex_weight

            score += regex_score

            matched_patterns.append({

                "pattern": pattern,

                "matches": len(matches),

                "score": regex_score

            })

    return score, matched_patterns


# =========================================================
# CLASSIFY DOCUMENT
# =========================================================

def classify_document(text):

    # =====================================================
    # EMPTY INPUT
    # =====================================================

    if not text or len(text.strip()) == 0:

        return {

            "document_type": "unknown",

            "confidence_score": 0,

            "all_scores": {},

            "matched_keywords": {},

            "matched_patterns": {}

        }

    # =====================================================
    # NORMALIZE
    # =====================================================

    normalized_text = normalize_text(text)

    scores = defaultdict(int)

    matched_keywords = {}

    matched_patterns = {}

    # =====================================================
    # SCORE EACH DOCUMENT TYPE
    # =====================================================

    for doc_type, config in DOCUMENT_PATTERNS.items():

        keyword_score, keyword_matches = (

            calculate_keyword_score(

                normalized_text,

                config["keywords"]

            )

        )

        regex_score, regex_matches = (

            calculate_regex_score(

                normalized_text,

                config["regex"]

            )

        )

        total_score = keyword_score + regex_score

        scores[doc_type] = total_score

        matched_keywords[doc_type] = keyword_matches

        matched_patterns[doc_type] = regex_matches

    # =====================================================
    # BEST MATCH
    # =====================================================

    predicted_class = max(

        scores,

        key=scores.get

    )

    best_score = scores[predicted_class]

    # =====================================================
    # UNKNOWN DOCUMENT DETECTION
    # =====================================================

    if best_score < 10:

        predicted_class = "unknown"

    # =====================================================
    # CONFIDENCE
    # =====================================================

    total_scores = sum(scores.values())

    confidence = 0

    if total_scores > 0:

        confidence = round(

            (

                best_score

                /

                total_scores

            ) * 100,

            2

        )

    # =====================================================
    # LOW CONFIDENCE OVERRIDE
    # =====================================================

    if confidence < 35:

        predicted_class = "unknown"

    # =====================================================
    # FINAL RESPONSE
    # =====================================================

    return {

        "document_type": predicted_class,

        "confidence_score": confidence,

        "all_scores": dict(scores),

        "matched_keywords": matched_keywords,

        "matched_patterns": matched_patterns

    }