import fitz  

def extract_pdf_pages(path: str):
    try:
        doc = fitz.open(path)
        pages = []

        for i in range(len(doc)):
            page = doc[i]
            text = page.get_text().replace("\n", " ").strip()
            pages.append({
                "pageNumber": i + 1,
                "content": text,
                "totalPages": len(doc),
                "pageIndicator": f"Page {i + 1}/{len(doc)}"
            })

        return { "pages": pages }

    except Exception as e:
        print("PDF error:", e)
        return { "error": "Failed to extract PDF pages" }
