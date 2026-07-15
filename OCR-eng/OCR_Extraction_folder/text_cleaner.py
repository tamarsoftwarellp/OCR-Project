import re
import unicodedata


# =========================================================
# IMPORTANT SYMBOLS
# =========================================================

IMPORTANT_SYMBOLS = [

    "<", ">", "=", "%", "/", "\\",
    ":", ";", "-", "_", "|",
    "*", "+", "#", "@", "$",
    "&", "₹", ".", ",", "(", ")"

]


# =========================================================
# UNICODE NORMALIZATION
# =========================================================

def normalize_unicode(text):

    return unicodedata.normalize(

        "NFC",

        text

    )


# =========================================================
# REMOVE CONTROL CHARACTERS
# =========================================================

def remove_control_characters(text):

    cleaned = []

    for char in text:

        ascii_code = ord(char)

        # =============================================
        # KEEP NEWLINES + TABS
        # =============================================

        if char in ["\n", "\t"]:

            cleaned.append(char)

            continue

        # =============================================
        # REMOVE INVALID CONTROL CHARS
        # =============================================

        if ascii_code < 32 or ascii_code == 127:

            continue

        cleaned.append(char)

    return "".join(cleaned)


# =========================================================
# FIX COMMON OCR ERRORS
# =========================================================

def fix_common_ocr_errors(text):

    replacements = {

        "ﬁ": "fi",
        "ﬂ": "fl",

        "’": "'",
        "‘": "'",

        "“": '"',
        "”": '"',

        "–": "-",
        "—": "-",

        "¢": "c",

        "§": "S",

        "¥": "Y",

        "€": "E"

    }

    for old, new in replacements.items():

        text = text.replace(old, new)

    return text


# =========================================================
# REMOVE OCR NOISE
# =========================================================

def remove_ocr_noise(text):

    # =============================================
    # REMOVE EXTREME DOT REPETITION
    # =============================================

    text = re.sub(

        r"\.{6,}",

        ".....",

        text

    )

    # =============================================
    # REMOVE SYMBOL REPETITION
    # =============================================

    text = re.sub(

        r"([~`^])\1{3,}",

        r"\1",

        text

    )

    # =============================================
    # REMOVE RANDOM PIPE BLOCKS
    # =============================================

    text = re.sub(

        r"\|{5,}",

        "|",

        text

    )

    # =============================================
    # REMOVE RANDOM UNDERSCORES
    # =============================================

    text = re.sub(

        r"_{6,}",

        "_____",

        text

    )

    return text


# =========================================================
# FIX BROKEN NUMBERS
# =========================================================

def fix_broken_numbers(text):

    # =============================================
    # FIX 1 , 0 0 0
    # =============================================

    text = re.sub(

        r"(\d)\s*,\s*(\d)",

        r"\1,\2",

        text

    )

    # =============================================
    # FIX 1 . 5 0
    # =============================================

    text = re.sub(

        r"(\d)\s*\.\s*(\d)",

        r"\1.\2",

        text

    )

    return text


# =========================================================
# FIX MERGED WORDS
# =========================================================

def fix_merged_words(text):

    # =============================================
    # FIX camelCase OCR merge
    # =============================================

    text = re.sub(

        r"([a-z])([A-Z])",

        r"\1 \2",

        text

    )

    return text


# =========================================================
# FIX SPACING
# =========================================================

def fix_spacing(text):

    # =============================================
    # MULTIPLE SPACES
    # =============================================

    text = re.sub(

        r"[ ]{2,}",

        " ",

        text

    )

    # =============================================
    # SPACE BEFORE PUNCTUATION
    # =============================================

    text = re.sub(

        r"\s+([.,:;!?])",

        r"\1",

        text

    )

    # =============================================
    # FIX BRACKETS
    # =============================================

    text = re.sub(

        r"\(\s+",

        "(",

        text

    )

    text = re.sub(

        r"\s+\)",

        ")",

        text

    )

    return text


# =========================================================
# PRESERVE TABLE STRUCTURE
# =========================================================

def preserve_table_structure(text):

    table_patterns = [

        r"[-]{3,}",
        r"[=]{3,}",
        r"[_]{3,}",
        r"[|]{2,}"

    ]

    for pattern in table_patterns:

        matches = re.findall(

            pattern,

            text

        )

        for match in matches:

            preserved = f" {match} "

            text = text.replace(

                match,

                preserved

            )

    return text


# =========================================================
# REMOVE GARBAGE LINES
# =========================================================

def remove_garbage_lines(text):

    lines = text.split("\n")

    cleaned = []

    for line in lines:

        stripped = line.strip()

        # =============================================
        # EMPTY
        # =============================================

        if len(stripped) == 0:

            cleaned.append("")
            continue

        # =============================================
        # TOO MANY SYMBOLS
        # =============================================

        alpha_count = len(

            re.findall(

                r"[A-Za-z0-9]",

                stripped

            )

        )

        if alpha_count == 0:

            continue

        cleaned.append(stripped)

    return "\n".join(cleaned)


# =========================================================
# NORMALIZE NEWLINES
# =========================================================

def normalize_newlines(text):

    lines = text.split("\n")

    cleaned_lines = []

    previous_blank = False

    for line in lines:

        stripped = line.strip()

        if stripped == "":

            if not previous_blank:

                cleaned_lines.append("")

            previous_blank = True

        else:

            cleaned_lines.append(stripped)

            previous_blank = False

    return "\n".join(cleaned_lines)


# =========================================================
# MAIN CLEANER
# =========================================================

def clean_ocr_text(text):

    if not text:

        return ""

    # =====================================================
    # STEP 1 → UNICODE NORMALIZATION
    # =====================================================

    text = normalize_unicode(text)

    # =====================================================
    # STEP 2 → COMMON OCR FIXES
    # =====================================================

    text = fix_common_ocr_errors(text)

    # =====================================================
    # STEP 3 → REMOVE CONTROL CHARS
    # =====================================================

    text = remove_control_characters(text)

    # =====================================================
    # STEP 4 → PRESERVE TABLES
    # =====================================================

    text = preserve_table_structure(text)

    # =====================================================
    # STEP 5 → REMOVE OCR NOISE
    # =====================================================

    text = remove_ocr_noise(text)

    # =====================================================
    # STEP 6 → FIX NUMBERS
    # =====================================================

    text = fix_broken_numbers(text)

    # =====================================================
    # STEP 7 → FIX MERGED WORDS
    # =====================================================

    text = fix_merged_words(text)

    print("\nAFTER FIX MERGED WORDS")
    print(text[:1000])

    # =====================================================
    # STEP 8 → FIX SPACING
    # =====================================================

    text = fix_spacing(text)

    # =====================================================
    # STEP 9 → REMOVE GARBAGE
    # =====================================================

    text = remove_garbage_lines(text)

    # =====================================================
    # STEP 10 → NORMALIZE NEWLINES
    # =====================================================

    text = normalize_newlines(text)

    # =====================================================
    # FINAL CLEAN
    # =====================================================

    text = text.strip()

    return text