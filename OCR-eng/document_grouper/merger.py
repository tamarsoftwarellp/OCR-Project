"""
==========================================================================
Enterprise Medical IDP
Document Merger
==========================================================================

Purpose
-------
Reads page-wise document classification JSON files and groups OCR pages
belonging to the same document type.

This module DOES NOT perform OCR.

This module DOES NOT call any LLM.

It only prepares page groupings for the merger stage.

Example

Input

06_document_classification/

page_1.json
page_2.json
page_3.json

↓

Output

{
    "insurance_form":[1,2],
    "hospital_bill":[3]
}
"""

import os
import json
import logging

from collections import defaultdict
from typing import Dict, List

from . import config


# ==========================================================================
# LOGGER
# ==========================================================================

logger = logging.getLogger(__name__)


# ==========================================================================
# READ SINGLE CLASSIFICATION JSON
# ==========================================================================

import os
import re
import json


def read_classification_file(json_path: str) -> tuple[int, str]:
    """
    Reads one classification JSON.

    Returns
    -------
    (
        page_number,
        document_type
    )
    """

    # -------------------------------------------------------
    # Read JSON
    # -------------------------------------------------------

    with open(
        json_path,
        "r",
        encoding=config.ENCODING
    ) as f:

        payload = json.load(f)

    # -------------------------------------------------------
    # Extract page number from filename
    # Example:
    #
    # page_12.json
    #
    # -> 12
    # -------------------------------------------------------

    filename = os.path.basename(json_path)

    match = re.search(

        r"page_(\d+)\.json",

        filename,

        re.IGNORECASE

    )

    if not match:

        raise ValueError(

            f"Invalid classification filename: {filename}"

        )

    page_number = int(

        match.group(1)

    )

    # -------------------------------------------------------
    # Document Type
    # -------------------------------------------------------

    document_type = payload.get(

        "document_type",

        "unknown"

    ).strip().lower()

    return (

        page_number,

        document_type

    )


# ==========================================================================
# LOAD ALL CLASSIFICATIONS
# ==========================================================================

def load_page_classifications() -> Dict[str, List[int]]:
    """
    Reads every JSON inside

    RESULT/.../06_document_classification

    Returns

    {
        "insurance_form":[1,2,4],
        "hospital_bill":[3,5],
        "health_card":[10]
    }
    """

    grouped_pages = defaultdict(list)

    files = sorted(

        [

            file

            for file in os.listdir(

                config.CLASSIFICATION_DIR

            )

            if file.endswith(

                config.CLASSIFICATION_FILE_EXTENSION

            )

        ]

    )

    logger.info(

        "Found %d classification files.",

        len(files)

    )

    for file_name in files:

        json_path = os.path.join(

            config.CLASSIFICATION_DIR,

            file_name

        )

        try:

            page_number, document_type = (

                read_classification_file(

                    json_path

                )

            )

            if config.MAX_OCR_PAGES is not None and page_number > config.MAX_OCR_PAGES:
                logger.warning(
                    "Skipping stale page %s beyond max OCR pages %s in current run.",
                    page_number,
                    config.MAX_OCR_PAGES,
                )
                continue

            grouped_pages[

                document_type

            ].append(

                page_number

            )

        except Exception as e:

            logger.error(

                "Failed reading %s : %s",

                file_name,

                e

            )

    # --------------------------------------------------------------
    # Sort page numbers
    # --------------------------------------------------------------

    for document_type in grouped_pages:

        grouped_pages[

            document_type

        ].sort()

    logger.info(

        "Detected %d unique document types.",

        len(grouped_pages)

    )

    return dict(grouped_pages)


# ==========================================================================
# DISPLAY GROUPS (Debug Helper)
# ==========================================================================

def print_document_groups(
    grouped_pages: Dict[str, List[int]]
) -> None:
    """
    Prints grouped pages.

    Example

    insurance_form

        Pages

        1
        2
        4

    hospital_bill

        Pages

        5
        6
    """

    print()

    print("=" * 70)

    print("DOCUMENT GROUPS")

    print("=" * 70)

    for document_type, pages in grouped_pages.items():

        print()

        print(

            f"{document_type}"

        )

        print(

            f"Pages : {pages}"

        )

    print()

    print("=" * 70)

# ==========================================================================
# BATCH PAGE NUMBERS
# ==========================================================================

def create_page_batches(
    page_numbers: List[int]
) -> List[List[int]]:
    """
    Splits page numbers into fixed-size batches.

    Example

    [1,2,3,4,5,6,7,8,9]

    ↓

    [
        [1,2,3,4,5,6,7],
        [8,9]
    ]
    """

    batches = []

    batch_size = config.MAX_PAGES_PER_BATCH

    for index in range(

        0,

        len(page_numbers),

        batch_size

    ):

        batches.append(

            page_numbers[
                index:index + batch_size
            ]

        )

    return batches


# ==========================================================================
# READ OCR PAGE
# ==========================================================================

def read_ocr_page(
    page_number: int
) -> str:
    """
    Reads one OCR page.

    Returns OCR text.

    Raises FileNotFoundError if OCR page does not exist.
    """

    file_path = os.path.join(

        config.OCR_DIR,

        config.OCR_FILE_TEMPLATE.format(

            page=page_number

        )

    )

    if not os.path.exists(file_path):

        raise FileNotFoundError(

            f"OCR file not found : {file_path}"

        )

    with open(

        file_path,

        "r",

        encoding=config.ENCODING

    ) as f:

        return f.read().strip()


# ==========================================================================
# WRITE MERGED OCR FILE
# ==========================================================================

def write_merged_batch(
    document_type: str,
    batch_number: int,
    page_numbers: List[int]
) -> None:
    """
    Creates one merged OCR file.

    Example

    insurance_form_001_raw.txt
    """

    output_folder = os.path.join(

        config.MERGED_OUTPUT_DIR,

        document_type

    )

    os.makedirs(

        output_folder,

        exist_ok=True

    )

    output_file = os.path.join(

        output_folder,

        config.MERGED_FILE_TEMPLATE.format(

            document_type=document_type,

            batch=batch_number

        )

    )

    logger.info(

        "Creating %s",

        output_file

    )

    with open(

        output_file,

        "w",

        encoding=config.ENCODING

    ) as writer:
        

        # ---------------------------------------------------------
        # Document Header
        # ---------------------------------------------------------
        writer.write("=" * 80 + "\n")
        writer.write(f"DOCUMENT TYPE : {document_type.upper()}\n")
        writer.write(f"PAGES INCLUDED : {page_numbers}\n")
        writer.write(f"TOTAL PAGES    : {len(page_numbers)}\n")
        writer.write("=" * 80 + "\n\n")

        
        for page in page_numbers:

            try:

                ocr_text = read_ocr_page(

                    page

                )

            except Exception as e:

                logger.error(

                    "Skipping Page %d : %s",

                    page,

                    e

                )

                continue

            writer.write(

                "=" * 70 + "\n"

            )

            writer.write(

                f"PAGE {page}\n"

            )

            writer.write(

                "=" * 70 + "\n\n"

            )

            writer.write(

                ocr_text

            )

            writer.write(

                "\n\n"

            )

    logger.info(

        "Saved : %s",

        output_file

    )


# ==========================================================================
# MERGE ONE DOCUMENT TYPE
# ==========================================================================

def merge_document_type(
    document_type: str,
    page_numbers: List[int]
) -> None:
    """
    Merges all OCR pages belonging to one document type.

    If pages exceed the configured batch size,
    multiple merged OCR files are created.
    """

    batches = create_page_batches(

        page_numbers

    )

    logger.info(

        "%s -> %d pages -> %d batch(es)",

        document_type,

        len(page_numbers),

        len(batches)

    )

    for batch_index, batch_pages in enumerate(

        batches,

        start=1

    ):

        write_merged_batch(

            document_type=document_type,

            batch_number=batch_index,

            page_numbers=batch_pages

        )

def run_merger(result_dir: str | None = None, run_id: str | None = None) -> None:
    """
    Executes the complete document merger pipeline.

    Pipeline

    Classification JSON
            │
            ▼
    Group Pages
            │
            ▼
    Split into batches
            │
            ▼
    Merge OCR
            │
            ▼
    Save merged OCR
    """

    config.configure_runtime_context(
        result_dir=result_dir,
        run_id=run_id
    )

    active_run_id = run_id or config.RUN_ID
    active_result_dir = result_dir or config.CURRENT_RESULT_DIR

    os.makedirs(
        config.MERGED_OUTPUT_DIR,
        exist_ok=True
    )

    logger.info("=" * 80)
    logger.info("Starting Document Merger")
    logger.info("Run ID: %s", active_run_id)
    logger.info("Current Result Directory: %s", active_result_dir)
    logger.info("Max OCR Pages: %s", config.MAX_OCR_PAGES)
    logger.info("=" * 80)


    # ---------------------------------------------------------
    # Read classifications
    # ---------------------------------------------------------

    grouped_pages = load_page_classifications()

    if not grouped_pages:

        logger.warning(
            "No classified documents found."
        )

        return

    # ---------------------------------------------------------
    # Debug display
    # ---------------------------------------------------------

    print_document_groups(
        grouped_pages
    )

    # ---------------------------------------------------------
    # Merge each document type
    # ---------------------------------------------------------

    total_documents = 0

    total_pages = 0

    for document_type, pages in grouped_pages.items():

        merge_document_type(

            document_type=document_type,

            page_numbers=pages

        )

        total_documents += 1

        total_pages += len(pages)

    logger.info("=" * 80)
    logger.info("Document Merger Completed")
    logger.info("=" * 80)

    logger.info(
        "Document Types : %d",
        total_documents
    )

    logger.info(
        "Pages Processed : %d",
        total_pages
    )

    logger.info(
        "Merged Output : %s",
        config.MERGED_OUTPUT_DIR
    )

    print()


    total_batches = 0

    for document_type, pages in grouped_pages.items():

        batches = create_page_batches(pages)

        total_batches += len(batches)

        merge_document_type(
            document_type,
            pages
        )

    print("=" * 80)
    print("DOCUMENT MERGER COMPLETED")
    print("=" * 80)

    print(f"Document Types : {total_documents}")
    print(f"Pages Processed: {total_pages}")
    print(f"Output Folder  : {config.MERGED_OUTPUT_DIR}")

    print("=" * 80)

    return {
        "document_types": total_documents,
        "pages": total_pages,
        "output_directory": config.MERGED_OUTPUT_DIR
    }

if __name__ == "__main__":

    logging.basicConfig(

        level=logging.INFO,

        format="%(asctime)s | %(levelname)s | %(message)s"

    )

    run_merger()