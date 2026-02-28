import json
import qrcode
import base64
import zlib
from io import BytesIO
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER


class PDFCertificateGenerator:
    """Generate PDF certificates with QR codes and digital signatures"""
    
    def __init__(self, output_dir: str = "certificates"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
    
    def generate_qr_code(self, data: str, size: int = 200) -> Image:
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

    def generate_qr_code_image(self, cert_id: str, verification_hash: str, device_id: str = "", 
                               method: str = "", output_name: str = None) -> Path:
        """Generate standalone QR code image file from verification hash
        
        Args:
            cert_id: Certificate ID
            verification_hash: Verification hash from wipe operation
            device_id: Device ID (optional)
            method: Wipe method used (optional)
            output_name: Custom output filename (optional)
            
        Returns:
            Path to generated QR code image
        """
        if not output_name:
            output_name = f"{cert_id}_qr.png"
        
        output_path = self.output_dir / output_name
        
        # Create QR data
        qr_data = json.dumps({
            "cert_id": cert_id,
            "verification_hash": verification_hash,
            "device_id": device_id,
            "method": method,
            "timestamp": datetime.utcnow().isoformat(),
            "verify_url": f"https://zerotrace.verify.com/cert/{cert_id}"
        })
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create and save image
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(str(output_path))
        
        print(f"QR code image generated: {output_path}")
        return output_path
    
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
        
        # Get verification hash from signature or verification field
        verification_hash = cert_data.get('_signature', {}).get('verification_hash', '')
        if not verification_hash:
            verification_hash = cert_data.get('verification', {}).get('completion_hash', 'N/A')
        
        # Render full hash in wrapped monospaced lines to avoid visual truncation in PDF.
        hash_text = verification_hash if verification_hash != 'N/A' else 'N/A'
        if hash_text != 'N/A' and len(hash_text) > 32:
            hash_text = f"{hash_text[:32]}<br/>{hash_text[32:]}"

        hash_style = ParagraphStyle(
            'HashCell',
            fontName='Courier',
            fontSize=8,
            leading=10,
            textColor=colors.black
        )

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
            ["Verification Hash:", Paragraph(hash_text, hash_style)],
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
            ('FONTNAME', (1, 0), (1, -1), 'Courier'),  # Use monospace for hash
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTSIZE', (1, 9), (1, 9), 8),  # Smaller font for verification hash row
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
            full_signature = signature_info.get('signature', 'N/A')
            if full_signature != 'N/A' and len(full_signature) > 48:
                full_signature = "<br/>".join(
                    full_signature[i:i + 48] for i in range(0, len(full_signature), 48)
                )

            sig_value_style = ParagraphStyle(
                'SigValue',
                parent=styles['Normal'],
                fontSize=8,
                leading=10,
                fontName='Courier',
                textColor=colors.black
            )

            sig_data = [
                ["Algorithm:", signature_info.get('algorithm', 'N/A')],
                ["Signed At:", signature_info.get('signed_at', 'N/A')],
                ["Signature:", Paragraph(full_signature, sig_value_style)],
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
        """Create QR code section with verification hash"""
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
        
        # Get verification hash from signature or verification field
        verification_hash = cert_data.get('_signature', {}).get('verification_hash', '')
        if not verification_hash:
            # Fallback to completion_hash
            verification_hash = cert_data.get('verification', {}).get('completion_hash', '')
        
        # Create QR code data with full verification hash
        qr_data = json.dumps({
            "cert_id": cert_data.get('cert_id'),
            "verification_hash": verification_hash,
            "device_id": cert_data.get('device_id'),
            "method": cert_data.get('method_used'),
            "status": cert_data.get('status'),
            "timestamp": cert_data.get('generated_at'),
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
        
        # Hash display for reference
        hash_display_style = ParagraphStyle(
            'HashDisplay',
            parent=styles['Normal'],
            fontSize=7,
            leading=9,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER,
            spaceAfter=10,
            fontName='Courier'
        )
        hash_display_value = verification_hash
        if hash_display_value and len(hash_display_value) > 32:
            hash_display_value = f"{hash_display_value[:32]}<br/>{hash_display_value[32:]}"
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(f"Hash: {hash_display_value}", hash_display_style))
        
        # QR instructions
        qr_instruction_style = ParagraphStyle(
            'QRInstruction',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.grey,
            alignment=TA_CENTER,
            spaceAfter=10
        )
        story.append(Spacer(1, 0.1*inch))
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

    def _build_payload_token(self, cert_data: Dict) -> str:
        """Create compressed, base64 payload token for machine verification from PDF text."""
        # Keep full signed certificate for deterministic verification on backend.
        payload_json = json.dumps(cert_data, sort_keys=True, separators=(',', ':')).encode('utf-8')
        compressed = zlib.compress(payload_json, level=9)
        token = base64.urlsafe_b64encode(compressed).decode('ascii')
        return token

    def _wrap_token_for_pdf(self, token: str, chunk_size: int = 100) -> str:
        chunks = [token[i:i + chunk_size] for i in range(0, len(token), chunk_size)]
        return "<br/>".join(chunks)

    def create_machine_payload_section(self, cert_data: Dict, styles: Dict) -> list:
        """Embed a machine-readable signed payload in the PDF for robust verification."""
        story = []
        story.append(Spacer(1, 0.1 * inch))

        token = self._build_payload_token(cert_data)
        wrapped = self._wrap_token_for_pdf(token)

        payload_style = ParagraphStyle(
            'PayloadToken',
            parent=styles['Normal'],
            fontSize=5,
            leading=6,
            textColor=colors.HexColor('#6b7280'),
            alignment=TA_CENTER,
            fontName='Courier'
        )

        # Use explicit begin/end markers for easy extraction from raw PDF text.
        marker_text = (
            "ZT_PAYLOAD_V1_BEGIN<br/>"
            f"{wrapped}<br/>"
            "ZT_PAYLOAD_V1_END"
        )
        story.append(Paragraph(marker_text, payload_style))
        return story
    
    def generate_certificate(self, cert_data: Dict, filename: Optional[str] = None) -> Path:
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
        story.extend(self.create_machine_payload_section(cert_data, styles))
        story.extend(self.create_footer(styles))
        
        # Build PDF
        doc.build(story)
        
        print(f"Certificate PDF generated: {pdf_path}")
        return pdf_path
