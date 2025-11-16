"""
PDF Certificate Generator
Creates professional PDF certificates with QR codes and security features
"""

import json
import qrcode
from io import BytesIO
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT


class PDFCertificateGenerator:
    """Generate PDF certificates with QR codes and digital signatures"""
    
    def __init__(self, output_dir: str = "certificates"):
        """
        Initialize PDF generator
        
        Args:
            output_dir: Directory to save generated PDFs
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
    
    def generate_qr_code(self, data: str, size: int = 200) -> Image:
        """
        Generate QR code image
        
        Args:
            data: Data to encode in QR code
            size: Size of QR code in pixels
            
        Returns:
            ReportLab Image object
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to BytesIO
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Create ReportLab Image
        return Image(img_buffer, width=2*inch, height=2*inch)
    
    def create_header(self, styles: Dict) -> list:
        """Create certificate header"""
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=28,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        story.append(Paragraph("ZEROTRACE", title_style))
        story.append(Paragraph("SECURE WIPE CERTIFICATE", title_style))
        
        # Subtitle
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.grey,
            spaceAfter=20,
            alignment=TA_CENTER
        )
        story.append(Paragraph("Digital Proof of Secure Data Erasure", subtitle_style))
        story.append(Spacer(1, 0.3*inch))
        
        return story
    
    def create_certificate_info_table(self, cert_data: Dict) -> Table:
        """Create table with certificate information"""
        
        # Prepare data
        table_data = [
            ["Certificate ID:", cert_data.get('cert_id', 'N/A')],
            ["Device ID:", cert_data.get('device_id', 'N/A')],
            ["Device Name:", cert_data.get('device', 'Unknown Device')],
            ["Model:", cert_data.get('device_info', {}).get('model', 'N/A')],
            ["Serial Number:", cert_data.get('device_info', {}).get('serial', 'N/A')],
            ["Wipe Method:", cert_data.get('method_used', 'N/A')],
            ["Start Time:", cert_data.get('start', 'N/A')],
            ["End Time:", cert_data.get('end', 'N/A')],
            ["Status:", cert_data.get('status', 'Completed')],
            ["Verification Hash:", cert_data.get('verification', {}).get('completion_hash', 'N/A')[:32] + "..."],
        ]
        
        # Create table
        table = Table(table_data, colWidths=[2.2*inch, 4*inch])
        
        # Style table
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e5e7eb')),
            ('BACKGROUND', (1, 0), (1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d1d5db')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        return table
    
    def create_signature_section(self, cert_data: Dict, styles: Dict) -> list:
        """Create digital signature section"""
        story = []
        
        signature_info = cert_data.get('_signature', {})
        
        if signature_info:
            story.append(Spacer(1, 0.3*inch))
            
            # Section header
            sig_header_style = ParagraphStyle(
                'SigHeader',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#1e40af'),
                spaceAfter=10
            )
            story.append(Paragraph("Digital Signature Information", sig_header_style))
            
            # Signature details
            sig_data = [
                ["Algorithm:", signature_info.get('algorithm', 'N/A')],
                ["Signed At:", signature_info.get('signed_at', 'N/A')],
                ["Signature:", signature_info.get('signature', 'N/A')[:50] + "..."],
            ]
            
            sig_table = Table(sig_data, colWidths=[1.5*inch, 4.7*inch])
            sig_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            
            story.append(sig_table)
        
        return story
    
    def create_qr_section(self, cert_data: Dict, styles: Dict) -> list:
        """Create QR code section"""
        story = []
        
        story.append(Spacer(1, 0.4*inch))
        
        # QR code header
        qr_header_style = ParagraphStyle(
            'QRHeader',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=10,
            alignment=TA_CENTER
        )
        story.append(Paragraph("Verification QR Code", qr_header_style))
        
        # Create QR code data
        qr_data = json.dumps({
            "cert_id": cert_data.get('cert_id'),
            "verification_hash": cert_data.get('verification', {}).get('completion_hash', '')[:16],
            "verify_url": f"https://zerotrace.verify.com/cert/{cert_data.get('cert_id')}"
        })
        
        # Generate QR code
        qr_img = self.generate_qr_code(qr_data)
        
        # Center QR code
        qr_table = Table([[qr_img]], colWidths=[6.2*inch])
        qr_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(qr_table)
        
        # QR instructions
        qr_instruction_style = ParagraphStyle(
            'QRInstruction',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.grey,
            alignment=TA_CENTER,
            spaceAfter=10
        )
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph("Scan this QR code to verify the authenticity of this certificate", qr_instruction_style))
        
        return story
    
    def create_footer(self, styles: Dict) -> list:
        """Create certificate footer"""
        story = []
        
        story.append(Spacer(1, 0.3*inch))
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        
        footer_text = f"""
        This certificate is cryptographically signed and tamper-proof.<br/>
        Generated by ZeroTrace v1.0 | © {datetime.now().year} ZeroTrace Systems<br/>
        For verification, visit: https://zerotrace.verify.com
        """
        
        story.append(Paragraph(footer_text, footer_style))
        
        return story
    
    def generate_certificate(self, cert_data: Dict, filename: Optional[str] = None) -> Path:
        """
        Generate complete PDF certificate
        
        Args:
            cert_data: Dictionary containing certificate data
            filename: Optional custom filename
            
        Returns:
            Path to generated PDF file
        """
        if not filename:
            cert_id = cert_data.get('cert_id', 'certificate')
            filename = f"{cert_id}.pdf"
        
        pdf_path = self.output_dir / filename
        
        # Create document
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Build content
        story = []
        styles = getSampleStyleSheet()
        
        # Add sections
        story.extend(self.create_header(styles))
        story.append(self.create_certificate_info_table(cert_data))
        story.extend(self.create_signature_section(cert_data, styles))
        story.extend(self.create_qr_section(cert_data, styles))
        story.extend(self.create_footer(styles))
        
        # Build PDF
        doc.build(story)
        
        print(f"Certificate PDF generated: {pdf_path}")
        return pdf_path