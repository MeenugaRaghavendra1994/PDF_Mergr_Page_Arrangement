import streamlit as st
import os
import zipfile
from PyPDF2 import PdfMerger
from io import BytesIO
import tempfile
from PIL import Image
from pdf2image import convert_from_path
import base64
from streamlit_sortables import sort_items

st.set_page_config(page_title="PDF Merger", layout="wide")

# Custom CSS for clean UI
with open("assets/styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("📂 PDF Merger - ZIP & JPG with Page Reorder")

st.write("Upload multiple **ZIP files**, **PDFs**, or **JPG images**. "
         "Preview, reorder pages manually, and merge into one final PDF.")

uploaded_files = st.file_uploader(
    "Upload ZIP, PDF, or JPG files", 
    type=["zip", "pdf", "jpg", "jpeg"],
    accept_multiple_files=True
)

if uploaded_files:
    st.success(f"✅ {len(uploaded_files)} files uploaded successfully!")

    with tempfile.TemporaryDirectory() as extract_folder:
        pdf_files = []

        # Step 1: Process each uploaded file
        for uploaded_file in uploaded_files:
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()

            # ZIP: extract PDFs
            if file_ext == ".zip":
                zip_path = os.path.join(extract_folder, uploaded_file.name)
                with open(zip_path, "wb") as f:
                    f.write(uploaded_file.read())

                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_folder)

                for root, _, files in os.walk(extract_folder):
                    for file in files:
                        if file.lower().endswith(".pdf"):
                            pdf_files.append(os.path.join(root, file))

            # JPG: convert to PDF
            elif file_ext in [".jpg", ".jpeg"]:
                img = Image.open(uploaded_file)
                img_pdf_path = os.path.join(extract_folder, uploaded_file.name.replace(file_ext, ".pdf"))
                img.convert('RGB').save(img_pdf_path)
                pdf_files.append(img_pdf_path)

            # Direct PDF
            elif file_ext == ".pdf":
                pdf_path = os.path.join(extract_folder, uploaded_file.name)
                with open(pdf_path, "wb") as f:
                    f.write(uploaded_file.read())
                pdf_files.append(pdf_path)

        if not pdf_files:
            st.error("❌ No PDF or JPG files found.")
        else:
            # Step 2: Generate preview images
            preview_data = []
            for pdf_path in pdf_files:
                pages = convert_from_path(pdf_path, dpi=80)
                for idx, page in enumerate(pages):
                    preview_path = os.path.join(extract_folder, f"{os.path.basename(pdf_path)}_page{idx+1}.jpg")
                    page.save(preview_path, "JPEG")
                    preview_data.append(preview_path)

            # Step 3: Display previews with drag-and-drop sorting
            st.subheader("🖱️ Reorder Pages by Dragging")

            preview_html = [
                f'<img src="data:image/jpeg;base64,{base64.b64encode(open(img, "rb").read()).decode()}" '
                f'style="width:150px; height:auto; border:1px solid #ccc; border-radius:8px;">'
                for img in preview_data
            ]

            sorted_preview = sort_items(preview_html, direction="horizontal", key="pdf_sort")

            # Step 4: Merge based on user order
            if st.button("Merge and Download"):
                ordered_files = [preview_data[preview_html.index(x)] for x in sorted_preview]
                
                merger = PdfMerger()
                for img_path in ordered_files:
                    # Convert reordered images back to PDF pages
                    img = Image.open(img_path)
                    temp_pdf_path = img_path.replace(".jpg", "_temp.pdf")
                    img.convert('RGB').save(temp_pdf_path)
                    merger.append(temp_pdf_path)

                merged_pdf = BytesIO()
                merger.write(merged_pdf)
                merger.close()
                merged_pdf.seek(0)

                st.download_button(
                    label="⬇️ Download Merged PDF",
                    data=merged_pdf,
                    file_name="final_merged.pdf",
                    mime="application/pdf"
                )
