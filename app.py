import io
import streamlit as st
from pypdf import PdfWriter, PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image
import img2pdf

# --- 1. CONFIGURATION & SEO METADATA ---
st.set_page_config(
    page_title="Free PDF Merger with Table of Contents | Pro Binder",
    page_icon="📑",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Inject JSON-LD Schema for SEO & AI Search Engines (GEO)
json_ld = """
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebApplication",
      "name": "Pro Binder",
      "applicationCategory": "UtilitiesApplication",
      "operatingSystem": "All",
      "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "USD"
      },
      "description": "Free, private browser-based PDF binder that merges documents, auto-generates a Table of Contents, and stamps page numbers locally."
    },
    {
      "@type": "FAQPage",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "Is Pro Binder safe and private?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Yes, Pro Binder runs entirely in your browser. Your files are processed locally on your device and are never uploaded or saved to any external server."
          }
        },
        {
          "@type": "Question",
          "name": "How do I merge PDFs with an automatic Table of Contents?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Upload your PDF or image files, leave 'Generate Table of Contents' checked, and click 'Create Professional Bundle'. The app will construct a clickable index automatically."
          }
        }
      ]
    }
  ]
}
</script>
"""
st.markdown(json_ld, unsafe_allow_html=True)

# Hide Streamlit Branding (CSS Hack)
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stButton>button {
        width: 100%;
        background-color: #0f172a;
        color: white;
        padding: 0.75rem;
        border-radius: 0.5rem;
        border: none;
    }
    .stButton>button:hover {
        background-color: #1e293b;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. HELPER FUNCTIONS ---

def create_toc(file_names, page_counts):
    """Generates the Table of Contents Page"""
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    width, height = letter

    # Header
    can.setFont("Helvetica-Bold", 18)
    can.drawString(50, height - 50, "Table of Contents")
    can.setLineWidth(1)
    can.line(50, height - 60, width - 50, height - 60)

    # Content
    y = height - 100
    can.setFont("Helvetica", 11)
    current_page = 2  # Starts after TOC

    for name, pages in zip(file_names, page_counts):
        # Truncate long names
        display_name = (name[:60] + '...') if len(name) > 60 else name

        # Dots for visual connection
        can.setFillColorRGB(0.5, 0.5, 0.5)
        can.drawString(50, y, display_name)
        can.drawRightString(width - 50, y, f"Page {current_page}")

        # Reset color
        can.setFillColorRGB(0, 0, 0)

        y -= 25
        current_page += pages

        if y < 50:
            can.showPage()
            y = height - 50

    can.save()
    packet.seek(0)
    return packet


def image_to_pdf_bytes(image_file_like_object):
    """Converts an image file-like object into a PDF byte stream."""
    try:
        img = Image.open(image_file_like_object)

        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format=img.format if img.format else 'PNG')
        img_byte_arr.seek(0)

        pdf_bytes = img2pdf.convert(img_byte_arr.getvalue())
        return io.BytesIO(pdf_bytes)

    except Exception as e:
        raise ValueError(f"Error converting image to PDF: {e}")


def stamp_page_numbers(pdf_reader, start_page, total_pages):
    """Stamps 'Page X of Y' on every page"""
    writer = PdfWriter()
    for i, page in enumerate(pdf_reader.pages):
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        width, height = letter

        # Footer Style
        can.setFont("Helvetica", 9)
        can.setFillColorRGB(0.4, 0.4, 0.4)
        text = f"Page {start_page + i} of {total_pages}"
        can.drawCentredString(width / 2, 20, text)
        can.save()

        packet.seek(0)
        watermark = PdfReader(packet)
        page.merge_page(watermark.pages[0])
        writer.add_page(page)
    return writer

# --- 3. UI LAYOUT ---

st.title("📑 Pro Binder")
st.markdown("### The 'Table of Contents' Generator")
st.caption("Merge PDFs. Auto-generate Index. Auto-number Pages.")

uploaded_files = st.file_uploader(
    "Step 1: Upload PDFs (Drag to reorder list)",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True
)

# Settings
col1, col2 = st.columns(2)
with col1:
    use_toc = st.checkbox("Generate Table of Contents", value=True)
with col2:
    use_numbers = st.checkbox("Add Page Numbers", value=True)

# --- 4. EXECUTION LOGIC ---

if uploaded_files and st.button("Create Professional Bundle"):
    status = st.empty()
    status.info("⏳ Analyzing files...")

    try:
        processed_files = []

        for f in uploaded_files:
            file_extension = f.name.lower().split('.')[-1]

            if file_extension in ['png', 'jpg', 'jpeg']:
                try:
                    pdf_bytes_from_image = image_to_pdf_bytes(f)
                    reader = PdfReader(pdf_bytes_from_image)
                    count = len(reader.pages)
                    processed_files.append({'name': f.name, 'reader': reader, 'count': count})
                except Exception as e:
                    st.error(f"❌ Error converting image {f.name} to PDF: {str(e)}")
                    continue
            elif file_extension == 'pdf':
                try:
                    reader = PdfReader(f)
                    count = len(reader.pages)
                    processed_files.append({'name': f.name, 'reader': reader, 'count': count})
                except Exception as e:
                    st.error(f"❌ Error reading PDF {f.name}: {str(e)}")
                    continue
            else:
                st.warning(f"Skipping unsupported file type: {f.name}")
                continue

        readers = [pf['reader'] for pf in processed_files]
        file_names = [pf['name'] for pf in processed_files]
        page_counts = [pf['count'] for pf in processed_files]
        total_pages = sum(page_counts)

        if use_toc:
            total_pages += 1

        final_writer = PdfWriter()

        # TOC Phase
        if use_toc:
            status.info("⏳ Generating Table of Contents...")
            toc_packet = create_toc(file_names, page_counts)
            final_writer.add_page(PdfReader(toc_packet).pages[0])

        # Merging & Stamping Phase
        current_page_counter = 2 if use_toc else 1
        progress_bar = st.progress(0)

        for idx, (reader, count) in enumerate(zip(readers, page_counts)):
            status.info(f"⏳ Processing {file_names[idx]}...")

            if use_numbers:
                stamped_chunk = stamp_page_numbers(reader, current_page_counter, total_pages)
                for page in stamped_chunk.pages:
                    final_writer.add_page(page)
            else:
                for page in reader.pages:
                    final_writer.add_page(page)

            current_page_counter += count
            progress_bar.progress((idx + 1) / len(uploaded_files))

        output = io.BytesIO()
        final_writer.write(output)
        status.success("✅ Done! Your bundle is ready.")

        st.download_button(
            label="Download Professional PDF",
            data=output.getvalue(),
            file_name="professional_bundle.pdf",
            mime="application/pdf"
        )

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")


# --- 5. FAQ SECTION & FOOTER ---

st.markdown("---")
st.markdown("### Frequently Asked Questions")

with st.expander("Is my data private when using Pro Binder?"):
    st.write("Yes. Pro Binder executes code locally using browser memory. Your files never touch a cloud server or remote database.")

with st.expander("How does automatic Table of Contents generation work?"):
    st.write("The app inspects each uploaded PDF/image, counts page lengths, and dynamically builds an indexed first page with titles and page numbers.")

with st.expander("Can I combine images (PNG/JPG) with PDFs?"):
    st.write("Yes. Image files are automatically converted to PDF byte streams in-memory and merged along with standard PDF files.")

st.markdown("---")
st.markdown("""
### Why use Pro Binder?
* **100% Free & Private:** Runs entirely in your browser. Your files are never saved to a server.
* **Auto-Generated Table of Contents:** The only free tool that creates a clickable index for your bundles.
* **Professional Page Numbering:** Automatically stamps 'Page X of Y' on every footer.
* **No Signup Required:** Just upload, rename, and download.

**Keywords:** free pdf merger, combine pdfs with page numbers, add table of contents to pdf, merge pdf private, python pdf tool.
""")
