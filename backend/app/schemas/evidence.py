"""
Wipe Evidence Submission Schemas
Captures raw evidence from desktop app for media-aware sanitization policy validation.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


MediaType = Literal["HDD", "SSD", "NVMe", "USB", "Unknown"]


class DeviceEvidence(BaseModel):
    device_id: str = Field(..., description="Unique OS/hardware drive identifier")
    device_name: Optional[str] = Field(None, description="Human friendly device name")
    device_model: Optional[str] = Field(None, description="Drive model string")
    device_serial: Optional[str] = Field(None, description="Hardware serial number")
    total_bytes: int = Field(..., ge=0, description="Reported total storage capacity in bytes")
    sector_size: int = Field(512, ge=512, description="Physical/logical sector size")
    media_type: MediaType = Field("Unknown", description="Underlying physical storage type")


class WipeExecutionEvidence(BaseModel):
    wipe_method: str = Field(..., description="Method name requested and performed")
    passes: int = Field(1, ge=1, description="Number of overwrite passes executed")
    bytes_wiped: int = Field(..., ge=0, description="Total bytes written/sanitized")
    sectors_wiped: Optional[int] = Field(None, ge=0, description="Total sectors sanitized")
    completion_hash: str = Field(..., description="Cryptographic SHA-256 verification hash of sanitized state")
    hardware_sanitization_used: bool = Field(False, description="Whether hardware-level commands (ATA/NVMe) were used")
    fallback_occurred: bool = Field(False, description="Whether fallback to software wipe occurred")
    errors: List[str] = Field(default_factory=list, description="Any sector errors or failure logs")
    wipe_start_time: str = Field(..., description="ISO 8601 start timestamp")
    wipe_end_time: str = Field(..., description="ISO 8601 completion timestamp")

    @field_validator("completion_hash")
    @classmethod
    def validate_hash_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if len(clean) != 64 or not all(c in "0123456789abcdef" for c in clean):
            raise ValueError("completion_hash must be a valid 64-character hex SHA-256 digest")
        return clean


class WipeEvidenceSubmission(BaseModel):
    idempotency_key: Optional[str] = Field(None, description="Optional client idempotency key to prevent duplicate certificates")
    device: DeviceEvidence
    execution: WipeExecutionEvidence
    operator_notes: Optional[str] = Field(None, description="Optional technician notes or compliance remarks")
