"""
PDF Generation and Payload Extraction Service
Builds signed PDF certificates with embedded machine-readable tokens.
Extracts payloads and hashes from uploaded PDFs using pypdf and detects tampering.
"""

import io
import re
import json
import zlib
import base64
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from pypdf import PdfReader

from backend.app.core.errors import CryptographicError


PAYLOAD_BEGIN = "ZT_PAYLOAD_V1_BEGIN"
PAYLOAD_END = "ZT_PAYLOAD_V1_END"
HASH_REGEX = re.compile(r'\b([a-fA-F0-9]{64})\b')


class PDFCertificateService:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._init_custom_styles()

    def _init_custom_styles(self):
        self.title_style = ParagraphStyle(
            'DocTitle',
            parent=self.styles['Heading1'],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#0f172a'),
            alignment=TA_CENTER,
            spaceAfter=6
        )
        self.subtitle_style = ParagraphStyle(
            'DocSubtitle',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor('#64748b'),
            alignment=TA_CENTER,
            spaceAfter=15
        )
        self.section_header = ParagraphStyle(
            'SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor('#1e40af'),
            spaceBefore=10,
            spaceAfter=6
        )
        self.payload_style = ParagraphStyle(
            'PayloadToken',
            parent=self.styles['Normal'],
            fontSize=5,
            leading=6,
            textColor=colors.HexColor('#94a3b8'),
            alignment=TA_CENTER,
            fontName='Courier'
        )
        self.table_cell = ParagraphStyle(
            'TableCell',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#1e293b')
        )
        self.table_cell_bold = ParagraphStyle(
            'TableCellBold',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=12,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#0f172a')
        )

    def _build_payload_token(self, cert_data: Dict[str, Any]) -> str:
        """Create compressed base64url machine verification token."""
        payload_json = json.dumps(cert_data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        compressed = zlib.compress(payload_json, level=9)
        return base64.urlsafe_b64encode(compressed).decode('ascii')

    def generate_pdf(self, cert_data: Dict[str, Any], verification_base_url: str = "https://zerotrace.verify.com") -> bytes:
        """Generate authoritative signed certificate PDF document without QR code."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch
        )

        story = []

        # 1. Header
        story.append(Paragraph("ZeroTrace Sanitization Certificate", self.title_style))
        cert_id = cert_data.get("certificate_id") or cert_data.get("cert_id", "UNKNOWN")
        story.append(Paragraph(f"Official Cryptographic Certificate of Data Erasure &bull; ID: <b>{cert_id}</b>", self.subtitle_style))
        story.append(Spacer(1, 0.1 * inch))

        # 2. Device Information Table
        story.append(Paragraph("1. Device Identification", self.section_header))
        dev_rows = [
            [Paragraph("Device Identifier", self.table_cell_bold), Paragraph(str(cert_data.get("device_id", "N/A")), self.table_cell)],
            [Paragraph("Model / Type", self.table_cell_bold), Paragraph(f"{cert_data.get('device_model', 'N/A')} ({cert_data.get('media_type', 'Drive')})", self.table_cell)],
            [Paragraph("Hardware Serial", self.table_cell_bold), Paragraph(str(cert_data.get("device_serial", "N/A")), self.table_cell)],
            [Paragraph("Reported Capacity", self.table_cell_bold), Paragraph(f"{cert_data.get('bytes_wiped', 0):,} bytes", self.table_cell)],
        ]
        dev_table = Table(dev_rows, colWidths=[2.2 * inch, 5.3 * inch])
        dev_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(dev_table)
        story.append(Spacer(1, 0.1 * inch))

        # 3. Sanitization & Compliance
        story.append(Paragraph("2. Sanitization Standard & Outcome", self.section_header))
        compliance = cert_data.get("compliance", {})
        level = cert_data.get("sanitization_level", "Clear")
        level_color = "#16a34a" if level == "Purge" else "#0284c7"

        san_rows = [
            [Paragraph("Sanitization Level", self.table_cell_bold), Paragraph(f"<font color='{level_color}'><b>{level}</b></font>", self.table_cell)],
            [Paragraph("Applied Method", self.table_cell_bold), Paragraph(str(cert_data.get("wipe_method", "N/A")), self.table_cell)],
            [Paragraph("Governing Standard", self.table_cell_bold), Paragraph(compliance.get("standard", "NIST SP 800-88 Rev. 1"), self.table_cell)],
            [Paragraph("Overwrite Passes", self.table_cell_bold), Paragraph(str(cert_data.get("passes", 1)), self.table_cell)],
            [Paragraph("Execution Period", self.table_cell_bold), Paragraph(f"{cert_data.get('wipe_start_time', 'N/A')} to {cert_data.get('wipe_end_time', 'N/A')}", self.table_cell)],
        ]
        san_table = Table(san_rows, colWidths=[2.2 * inch, 5.3 * inch])
        san_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(san_table)
        story.append(Spacer(1, 0.1 * inch))

        # 4. Cryptographic Proof (Full Width, No QR Code)
        story.append(Paragraph("3. Cryptographic Verification & Public Trust Anchor", self.section_header))
        verification_hash = cert_data.get("verification_hash") or (cert_data.get("_signature") or {}).get("verification_hash", "UNKNOWN")

        crypto_cell = [
            Paragraph("<b>Algorithm:</b> ECDSA-SHA256 (NIST P-256 Curve)", self.table_cell),
            Spacer(1, 4),
            Paragraph(f"<b>Verification Hash (SHA-256):</b><br/><font face='Courier' size=7>{verification_hash}</font>", self.table_cell),
            Spacer(1, 4),
            Paragraph(f"<b>Issued By:</b> {cert_data.get('issuer', 'ZeroTrace Authoritative Backend')}", self.table_cell),
            Paragraph(f"<b>Issued At:</b> {cert_data.get('issued_at', datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))}", self.table_cell),
        ]
        crypto_table = Table([[crypto_cell]], colWidths=[7.5 * inch])
        crypto_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(crypto_table)
        story.append(Spacer(1, 0.15 * inch))

        # 5. Embedded Machine-Readable Payload Token
        token = self._build_payload_token(cert_data)
        # Split token into chunks
        chunks = [token[i:i + 100] for i in range(0, len(token), 100)]
        wrapped_token = "<br/>".join(chunks)
        payload_markup = (
            f"{PAYLOAD_BEGIN}<br/>"
            f"{wrapped_token}<br/>"
            f"{PAYLOAD_END}"
        )
        story.append(Paragraph(payload_markup, self.payload_style))

        # Build document
        doc.build(story)
        return buffer.getvalue()

    def extract_from_pdf(self, pdf_bytes: bytes) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Extract machine-readable signed certificate or standalone hash from PDF bytes.
        Performs structural and text consistency validation to detect tampering.
        Returns: (extracted_certificate_dict_or_None, extracted_hash_or_None)
        """
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            full_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

            # Check for embedded machine token
            begin_idx = full_text.find(PAYLOAD_BEGIN)
            end_idx = full_text.find(PAYLOAD_END)
            if begin_idx != -1:
                if end_idx == -1 or end_idx <= begin_idx:
                    return {"_tamper_detected": "payload_corrupted"}, None

                raw_token_region = full_text[begin_idx + len(PAYLOAD_BEGIN):end_idx]
                token_cleaned = re.sub(r'[^A-Za-z0-9\-_]', '', raw_token_region)
                if not token_cleaned:
                    return {"_tamper_detected": "payload_corrupted"}, None

                try:
                    padded = token_cleaned + '=' * (-len(token_cleaned) % 4)
                    compressed = base64.urlsafe_b64decode(padded)
                    decompressed = zlib.decompress(compressed)
                    cert_data = json.loads(decompressed.decode('utf-8'))
                except Exception:
                    return {"_tamper_detected": "payload_corrupted"}, None

                v_hash = cert_data.get("verification_hash") or (cert_data.get("_signature") or {}).get("verification_hash")

                # Tamper detection: verify visible text consistency with signed payload
                hash_matches = HASH_REGEX.findall(full_text)
                if hash_matches and v_hash:
                    lower_hashes = [h.lower() for h in hash_matches]
                    if v_hash.lower() not in lower_hashes:
                        cert_data["_tamper_detected"] = "tampered_pdf_text_mismatch"

                dev_serial = str(cert_data.get("device_serial", "")).strip()
                if dev_serial and dev_serial != "N/A" and dev_serial not in full_text:
                    cert_data["_tamper_detected"] = "tampered_pdf_text_mismatch"

                cert_id = str(cert_data.get("certificate_id") or cert_data.get("cert_id", "")).strip()
                if cert_id and cert_id != "UNKNOWN" and cert_id not in full_text:
                    cert_data["_tamper_detected"] = "tampered_pdf_text_mismatch"

                return cert_data, v_hash

            # Fallback: scan for SHA-256 hash in text
            hash_match = HASH_REGEX.search(full_text)
            if hash_match:
                return None, hash_match.group(1).lower()

            return None, None
        except Exception:
            return None, None


pdf_service = PDFCertificateService()

