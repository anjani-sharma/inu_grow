import fitz  # PyMuPDF
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from flask import make_response
import os

class DocumentService:
    @staticmethod
    def extract_text(filepath, file_type):
        """Extract text from a document file based on its type"""
        if file_type == 'pdf':
            return DocumentService.extract_text_from_pdf(filepath)
        elif file_type == 'docx':
            return DocumentService.extract_text_from_docx(filepath)
        return ""
    
    @staticmethod
    def extract_text_from_pdf(filepath):
        """Extract text from a PDF file"""
        try:
            doc = fitz.open(filepath)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text.strip()
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""
    
    @staticmethod
    def extract_text_from_docx(filepath):
        """Extract text from a DOCX file"""
        try:
            from docx import Document
            doc = Document(filepath)
            text = ''
            for para in doc.paragraphs:
                if para.text.strip():
                    text += para.text + '\n'
            return text.strip()
        except Exception as e:
            print(f"Error extracting text from DOCX: {e}")
            return ""
    
    @staticmethod
    def generate_pdf(content, filename):
        """Generate a PDF file from text content"""
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        p.setFont("Helvetica", 12)
        y = 750
        
        for line in content.split('\n'):
            if y < 50:
                p.showPage()
                p.setFont("Helvetica", 12)
                y = 750
            p.drawString(50, y, line)
            y -= 15
            
        p.showPage()
        p.save()
        buffer.seek(0)
        
        response = make_response(buffer.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        response.headers['Content-Type'] = 'application/pdf'
        
        return response
    
    @staticmethod
    def html_to_pdf(html_content, output_path):
        """
        Convert HTML content to PDF and save to file
        Uses xhtml2pdf
        """
        try:
            from xhtml2pdf import pisa
            
            # Create PDF
            with open(output_path, "wb") as pdf_file:
                pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
                
            return pisa_status.err == 0
        except Exception as e:
            print(f"HTML to PDF conversion error: {e}")
            # Fallback to simple text PDF if xhtml2pdf fails
            try:
                # Extract text from HTML (simple approach)
                import re
                text_content = re.sub('<.*?>', ' ', html_content)
                text_content = re.sub(r'\s+', ' ', text_content).strip()
                
                # Create a basic PDF with text
                buffer = BytesIO()
                p = canvas.Canvas(buffer, pagesize=letter)
                p.setFont("Helvetica", 12)
                y = 750
                
                for line in text_content.split('\n'):
                    if y < 50:
                        p.showPage()
                        p.setFont("Helvetica", 12)
                        y = 750
                    p.drawString(50, y, line[:80])  # Limit line length
                    y -= 15
                    
                p.showPage()
                p.save()
                
                # Save to file
                with open(output_path, 'wb') as f:
                    f.write(buffer.getvalue())
                    
                return True
            except:
                return False
    
    @staticmethod
    def allowed_file(filename):
        """Check if the file type is allowed"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'docx'}
    
    @staticmethod
    def extract_text_and_links_from_pdf(filepath):
        """Extract text and hyperlinks from a PDF file"""
        try:
            doc = fitz.open(filepath)
            text = ""
            links = set()

            for page in doc:
                text += page.get_text()
                for link in page.get_links():
                    if link.get("uri"):
                        links.add(link["uri"])

            doc.close()
            return text.strip(), list(links)
        except Exception as e:
            print(f"[DocumentService] Error extracting text and links from PDF: {e}")
            return "", []