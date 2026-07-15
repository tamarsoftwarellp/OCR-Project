import os

from pdf2image import convert_from_path


# =========================================================
# PDF → IMAGE CONVERTER
# =========================================================

def convert_pdf_to_images(

    pdf_path,
    output_folder,
    dpi=300,
    image_format="PNG",
    max_pages=None,

):

    # =====================================================
    # CREATE OUTPUT DIRECTORY
    # =====================================================

    os.makedirs(

        output_folder,
        exist_ok=True

    )

    # =====================================================
    # VALIDATE PDF
    # =====================================================

    if not os.path.exists(pdf_path):

        raise FileNotFoundError(

            f"PDF not found → {pdf_path}"

        )

    # =====================================================
    # CONVERT PDF TO IMAGES
    # =====================================================

    try:

        convert_kwargs = {
            "dpi": dpi,
            "fmt": "png",
            "thread_count": 4,
        }
        if max_pages is not None:
            convert_kwargs["first_page"] = 1
            convert_kwargs["last_page"] = max_pages

        pages = convert_from_path(

            pdf_path,

            **convert_kwargs,

        )

    except Exception as e:

        raise RuntimeError(

            f"PDF conversion failed → {str(e)}"

        )

    # =====================================================
    # SAVE PAGES
    # =====================================================

    image_paths = []

    for index, page in enumerate(pages):

        page_number = index + 1

        image_name = (

            f"page_{page_number}.png"

        )

        image_path = os.path.join(

            output_folder,

            image_name

        )

        # =================================================
        # SAVE IMAGE
        # =================================================

        page.save(

            image_path,

            image_format

        )

        image_paths.append(

            image_path

        )

        # print(

        #     f"Saved Page {page_number} → "
        #     f"{image_path}"

        # )

    # =====================================================
    # SUMMARY
    # =====================================================

    print(

        f"\nTotal Pages Converted → "
        f"{len(image_paths)}"

    )

    return image_paths