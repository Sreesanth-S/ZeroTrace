"""
Media-Aware Sanitization Policy Validator
Validates evidence submitted by desktop app and classifies outcome into Purge, Clear, or Inconclusive/Failed.
"""

from typing import Tuple, Dict, Any
from datetime import datetime
from backend.app.schemas.evidence import WipeEvidenceSubmission
from backend.app.core.errors import EvidenceValidationError


class EvidenceValidator:
    """Enforces NIST SP 800-88 Rev. 1 media sanitization policy."""

    PURGE_METHODS = {
        "nvme sanitize",
        "ata secure erase",
        "cryptographic erase",
        "crypto scramble",
        "nist 800-88 purge"
    }

    CLEAR_METHODS = {
        "nist 800-88 clear",
        "dod 5220.22-m",
        "dod 5220.22-m (ece)",
        "zero fill",
        "random fill",
        "gutmann 35-pass",
        "single pass overwrite"
    }

    def validate_and_classify(self, submission: WipeEvidenceSubmission) -> Tuple[str, Dict[str, Any]]:
        """
        Validates wipe evidence and returns:
        (sanitization_level: "Purge" | "Clear", compliance_metadata: dict)
        
        Raises EvidenceValidationError if outcome is Inconclusive/Failed.
        """
        device = submission.device
        execution = submission.execution

        # 1. Sanity check: verify errors
        if execution.errors:
            error_details = ", ".join(execution.errors)
            raise EvidenceValidationError(
                f"Wipe evidence reports unrecovered errors: {error_details}. Certificate issuance rejected.",
                details={"errors": execution.errors}
            )

        # 2. Timestamp sanity check
        try:
            start_dt = datetime.fromisoformat(execution.wipe_start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(execution.wipe_end_time.replace("Z", "+00:00"))
            if end_dt < start_dt:
                raise EvidenceValidationError(
                    "Wipe completion timestamp occurs before start timestamp.",
                    details={"start": execution.wipe_start_time, "end": execution.wipe_end_time}
                )
        except ValueError as exc:
            raise EvidenceValidationError(f"Invalid timestamp format: {exc}")

        # 3. Capacity & verification hash check
        if execution.bytes_wiped <= 0 and not execution.hardware_sanitization_used:
            raise EvidenceValidationError(
                "Bytes wiped cannot be zero for software overwrite methods.",
                details={"bytes_wiped": execution.bytes_wiped}
            )

        if not execution.completion_hash or len(execution.completion_hash) != 64:
            raise EvidenceValidationError(
                "Completion hash is missing or invalid.",
                details={"completion_hash": execution.completion_hash}
            )

        method_normalized = execution.wipe_method.strip().lower()

        # 4. Media-aware classification
        is_purge_method = any(m in method_normalized for m in self.PURGE_METHODS)

        if is_purge_method:
            if execution.fallback_occurred:
                # Hardware Purge failed or fell back to software Clear
                level = "Clear"
                compliance_info = {
                    "standard": "NIST SP 800-88 Rev. 1",
                    "level": "Clear",
                    "method": f"{execution.wipe_method} (Software Fallback)",
                    "hardware_sanitization": False,
                    "fallback_occurred": True,
                    "target_media": device.media_type,
                    "implemented": True,
                    "notes": "Purge command fell back to software Clear overwrite passes."
                }
            elif execution.hardware_sanitization_used:
                level = "Purge"
                compliance_info = {
                    "standard": "NIST SP 800-88 Rev. 1",
                    "level": "Purge",
                    "method": execution.wipe_method,
                    "hardware_sanitization": True,
                    "fallback_occurred": False,
                    "target_media": device.media_type,
                    "implemented": True,
                    "notes": f"Firmware-level hardware sanitize completed successfully on {device.media_type}."
                }
            else:
                # Purge requested but no hardware command executed; treat as Clear if bytes wiped
                level = "Clear"
                compliance_info = {
                    "standard": "NIST SP 800-88 Rev. 1",
                    "level": "Clear",
                    "method": execution.wipe_method,
                    "hardware_sanitization": False,
                    "fallback_occurred": True,
                    "target_media": device.media_type,
                    "implemented": True,
                    "notes": "Purge requested without hardware execution; classified as Clear."
                }
        else:
            # Overwrite methods correspond to Clear
            level = "Clear"
            compliance_info = {
                "standard": "NIST SP 800-88 Rev. 1 / DoD 5220.22-M",
                "level": "Clear",
                "method": execution.wipe_method,
                "passes": execution.passes,
                "hardware_sanitization": False,
                "fallback_occurred": False,
                "target_media": device.media_type,
                "implemented": True,
                "notes": f"Logical overwrite passes ({execution.passes}) completed."
            }

        return level, compliance_info


evidence_validator = EvidenceValidator()
