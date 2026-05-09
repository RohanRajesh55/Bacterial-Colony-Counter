from fpdf import FPDF
import io
import base64
from datetime import datetime
import db_models as models
from PIL import Image


class PDFReport(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.cell(0, 10, 'Bacterial Colony Analysis Report', align='C')
        self.ln(8)
        
        # Custom Lab Name if provided
        if hasattr(self, 'lab_name') and self.lab_name:
             self.set_font('helvetica', 'I', 10)
             self.cell(0, 6, self.lab_name, align='C')
             self.ln(6)
        
        self.ln(4)
        # Horizontal line
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')
        if hasattr(self, 'researcher_name') and self.researcher_name:
            self.set_x(10)
            self.cell(0, 10, f'Researcher: {self.researcher_name}', align='L')

def generate_pdf_report(analysis: models.Analysis, lab_name: str = None, researcher_name: str = None) -> bytes:
    """Generate a compact PDF report."""
    pdf = PDFReport()
    pdf.lab_name = lab_name
    pdf.researcher_name = researcher_name
    
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # --- Metadata Section (Top) ---
    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(25, 6, "File Name:", align='L')
    pdf.set_font('helvetica', '', 10)
    pdf.cell(80, 6, analysis.filename, align='L')
    
    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(25, 6, "Date:", align='L')
    pdf.set_font('helvetica', '', 10)
    pdf.cell(0, 6, analysis.timestamp.strftime('%Y-%m-%d %H:%M:%S'), align='L')
    pdf.ln(6)
    
    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(25, 6, "Model:", align='L')
    pdf.set_font('helvetica', '', 10)
    pdf.cell(80, 6, analysis.model_used.upper(), align='L')
    
    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(25, 6, "Total Count:", align='L')
    pdf.set_font('helvetica', '', 10)
    pdf.cell(0, 6, str(analysis.total_count), align='L')
    pdf.ln(10)

    # Helper to decode image
    def decode_img(b64_str):
        if not b64_str: return None
        if ',' in b64_str:
            b64_str = b64_str.split(',')[1]
        try:
            return io.BytesIO(base64.b64decode(b64_str))
        except:
            return None

    # --- Two Columns: Details (Left) vs Original Image (Top Right) ---
    y_start = pdf.get_y()
    
    # 1. Classification Table (Left Column, Width ~90)
    pdf.set_font('helvetica', 'B', 11)
    pdf.cell(0, 8, "Classification Breakdown")
    pdf.ln(8)
    
    # Table Header
    pdf.set_font('helvetica', 'B', 9)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(50, 7, "Class Name", border=1, fill=True)
    pdf.cell(20, 7, "Count", border=1, fill=True)
    pdf.cell(20, 7, "Conf", border=1, fill=True)
    pdf.ln()
    
    # Table Rows
    pdf.set_font('helvetica', '', 9)
    row_height = 6
    for detail in analysis.details:
        pdf.cell(50, row_height, detail.class_name, border=1)
        pdf.cell(20, row_height, str(detail.count), border=1)
        conf = f"{detail.confidence:.2f}" if detail.confidence else "-"
        pdf.cell(20, row_height, conf, border=1)
        pdf.ln()
    
    table_bottom_y = pdf.get_y()
    
    # 2. Original Image (Right Column, x=110)
    # Only if we have it
    original_img = decode_img(analysis.thumbnail_base64)
    img_height_mm = 0
    if original_img:
        # Save cursor
        pdf.set_xy(110, y_start) 
        pdf.set_font('helvetica', 'B', 11)
        pdf.cell(0, 8, "Original Preview")
        
        try:
            # Calculate height to maintain aspect ratio
            # FPDF uses 72 DPI by default but we specify Width in mm
            # We can use PIL to get aspect ratio
            with Image.open(original_img) as pil_img:
                w_px, h_px = pil_img.size
                aspect = h_px / w_px
                
            target_w = 80
            target_h = target_w * aspect
            
            # Constraint: Don't let it be too tall (max 80mm)
            if target_h > 80:
                target_h = 80
                target_w = target_h / aspect
                
            img_height_mm = target_h
            
            # Rewind for FPDF
            original_img.seek(0)
            pdf.image(original_img, x=110, y=y_start+10, w=target_w, h=target_h)
        except Exception as e:
            pdf.set_xy(110, y_start+10)
            pdf.cell(80, 10, "[Image Error]", border=1, align='C')
            img_height_mm = 10

    # Move cursor below the lower of the two elements
    # Add buffer
    current_y = max(table_bottom_y, y_start + 10 + img_height_mm) 
    pdf.set_y(current_y + 10)
    
    # --- Visual Analysis Section (Bottom / Next Page) ---
    # We want Annotated and Heatmap side-by-side
    
    if pdf.get_y() > 220:
        pdf.add_page()
    
    pdf.set_font('helvetica', 'B', 12)
    pdf.cell(0, 10, "Analysis Visualization", ln=True)
    
    # Config for side-by-side images
    img_width = 90
    spacing = 10
    x_left = 10
    x_right = 10 + img_width + spacing
    y_imgs = pdf.get_y()
    
    annotated_stream = decode_img(analysis.annotated_base64)
    heatmap_stream = decode_img(analysis.heatmap_base64)
    
    # Calculate heights to check for page break necessity
    h_ann = 0
    h_heat = 0
    
    if annotated_stream:
        try:
            with Image.open(annotated_stream) as pil_img:
                h_ann = img_width * (pil_img.size[1] / pil_img.size[0])
            annotated_stream.seek(0)
        except: pass
        
    if heatmap_stream:
        try:
            with Image.open(heatmap_stream) as pil_img:
                h_heat = img_width * (pil_img.size[1] / pil_img.size[0])
            heatmap_stream.seek(0)
        except: pass
        
    max_img_h = max(h_ann, h_heat)
    
    # Check if we have space (page height ~297 minus footer 15 minus margin)
    if pdf.get_y() + max_img_h + 20 > 280:
        pdf.add_page()
        y_imgs = pdf.get_y() # Update Y after new page
    
    # Annotated (Left)
    if annotated_stream:
        pdf.set_xy(x_left, y_imgs)
        pdf.set_font('helvetica', 'B', 10)
        pdf.cell(img_width, 6, "Detected Colonies (YOLO)", align='C')
        try:
            pdf.image(annotated_stream, x=x_left, y=y_imgs+7, w=img_width)
        except:
            pass

    # Heatmap (Right)
    if heatmap_stream:
        pdf.set_xy(x_right, y_imgs)
        pdf.set_font('helvetica', 'B', 10)
        pdf.cell(img_width, 6, "Density Heatmap", align='C')
        try:
            pdf.image(heatmap_stream, x=x_right, y=y_imgs+7, w=img_width)
        except:
            pass
            
    return pdf.output()
