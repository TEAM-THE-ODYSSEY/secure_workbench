import hashlib
import logging
from typing import List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class IntegrityCheckResult(BaseModel):
    is_valid: bool
    file_hash: str
    issues: List[str]

class IntegrityChecker:
    def check(self, file_bytes: bytes, filename: str, expected_hash: Optional[str] = None) -> IntegrityCheckResult:
        logger.info(f"Checking integrity for {filename}")
        issues = []
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        
        if expected_hash and file_hash != expected_hash:
            issues.append(f"Hash mismatch. Expected {expected_hash}, got {file_hash}")
            
        # Basic magic bytes check for PDF
        if filename.lower().endswith('.pdf'):
            if not file_bytes.startswith(b'%PDF'):
                issues.append("File extension is .pdf but missing %PDF magic bytes")
                
        is_valid = len(issues) == 0
        return IntegrityCheckResult(is_valid=is_valid, file_hash=file_hash, issues=issues)
