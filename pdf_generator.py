from imports import *

class PDFGenerator:
    """Enhanced PDF certificate generator"""
    
    def __init__(self):
        self.output_dir = Path("certificates")
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_certificate(self, signed_json_path: Path) -> Optional[Path]:
        """Generate a professional PDF certificate"""
        try:
            with open(signed_json_path, 'r') as f:
                data = json.load(f)
            
            pdf_path = self.output_dir / (signed_json_path.stem + ".pdf")
            
            # Create PDF document
            doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
            story = []
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = styles['Title']
            title_style.fontSize = 24
            title_style.textColor = colors.darkblue
            
            # Title
            story.append(Paragraph("ZEROTRACE WIPE CERTIFICATE", title_style))
            story.append(Spacer(1, 0.5*inch))
            
            # Certificate info
            cert_info = [
                ["Certificate ID:", data.get("verification", {}).get("completion_hash", "N/A")[:16]],
                ["Device:", data.get("device", "Unknown")],
                ["Device Model:", data.get("device_info", {}).get("model", "Unknown")],
                ["Device Serial:", data.get("device_info", {}).get("serial", "Unknown")],
                ["Wipe Method:", data.get("method_used", "Unknown")],
                ["Start Time:", data.get("start", "Unknown")],
                ["End Time:", data.get("end", "Unknown")],
                ["Status:", data.get("status", "Unknown")],
            ]
            
            # Create table
            table = Table(cert_info, colWidths=[2*inch, 4*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('BACKGROUND', (0, 0), (0, -1), colors.grey),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ]))
            
            story.append(table)
            story.append(Spacer(1, 0.5*inch))
            
            # Generate QR code
            qr_data = {
                "cert_id": data.get("verification", {}).get("completion_hash", "")[:16],
                "device": data.get("device"),
                "status": data.get("status"),
                "verify_url": "https://zerotrace.verify.com/cert"
            }
            
            qr_img = self._generate_qr_code(json.dumps(qr_data))
            if qr_img:
                story.append(Paragraph("Scan QR Code to Verify:", styles['Heading2']))
                story.append(qr_img)
                story.append(Spacer(1, 0.3*inch))
            
            # Signature info
            if "_signature" in data:
                story.append(Paragraph("Digital Signature:", styles['Heading2']))
                sig_info = data["_signature"]
                story.append(Paragraph(f"Algorithm: {sig_info.get('algorithm', 'Unknown')}", styles['Normal']))
                story.append(Paragraph(f"Signed At: {sig_info.get('signed_at', 'Unknown')}", styles['Normal']))
            
            # Build PDF
            doc.build(story)
            return pdf_path
            
        except Exception as e:
            print(f"Error generating PDF: {e}")
            return None
    
    def _generate_qr_code(self, data: str) -> Optional[Image]:
        """Generate QR code image for the certificate"""
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(data)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to reportlab Image
            img_buffer = BytesIO()
            qr_img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            return Image(img_buffer, width=2*inch, height=2*inch)
            
        except Exception as e:
            print(f"Error generating QR code: {e}")
            return None