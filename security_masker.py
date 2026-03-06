"""
Security Masking Module for Recruitment Tool
==============================================

Provides PII and client-sensitive information masking for:
1. Resume uploads (PII: emails, phone numbers, addresses, SSN, DOB)
2. Job Description uploads (client names, project codes, confidential info)

Masking Strategy:
- Replace sensitive data with generic placeholders
- Maintain document structure and readability for skill extraction
- Never log or expose original sensitive data
- Ensure masked data is consistent within a document
"""

import re
import hashlib
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum


class SensitivityLevel(Enum):
    """Classification of sensitive information types."""
    PII_CRITICAL = "PII_CRITICAL"  # SSN, passport, medical
    PII_HIGH = "PII_HIGH"  # Email, phone, address
    PII_MEDIUM = "PII_MEDIUM"  # Names, DOB
    CLIENT_CONFIDENTIAL = "CLIENT_CONFIDENTIAL"  # Client names, project codes
    CLIENT_INTERNAL = "CLIENT_INTERNAL"  # Internal references, codes


@dataclass
class MaskingResult:
    """Result of masking operation."""
    masked_text: str
    mask_count: int
    sensitivity_detected: Dict[str, int] = field(default_factory=dict)
    masking_log: List[str] = field(default_factory=list)  # For audit, not sensitive data


class PIIMasker:
    """
    Masks Personal Identifiable Information (PII) from resume documents.
    
    Targets:
    - Email addresses
    - Phone numbers (multiple international formats)
    - Physical addresses
    - Social Security Numbers (SSN)
    - Date of Birth patterns
    - Names (when in header/contact section)
    """
    
    # Regex patterns for PII detection
    PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "phone_us": r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
        "phone_intl": r'\b\+?[1-9]\d{0,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b',
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
        "zip_code": r'\b\d{5}(?:-\d{4})?\b',
        "address": r'\b\d+\s+[\w\s]+(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr|court|ct|circle|cir|way)\b',
        "dob_slash": r'\b(?:0[1-9]|1[0-2])/(?:0[1-9]|[12]\d|3[01])/(?:19|20)\d{2}\b',
        "dob_dash": r'\b(?:19|20)\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])\b',
    }
    
    def __init__(self):
        """Initialize PII masker with compiled patterns."""
        self.compiled_patterns = {
            key: re.compile(pattern, re.IGNORECASE)
            for key, pattern in self.PATTERNS.items()
        }
        self._masked_cache: Dict[str, str] = {}  # Consistent masking within document
    
    def mask_resume(self, resume_text: str) -> MaskingResult:
        """
        Mask PII from resume text.
        
        Args:
            resume_text: Raw resume text
            
        Returns:
            MaskingResult with masked text and statistics
        """
        masked_text = resume_text
        mask_count = 0
        sensitivity_map = {}
        masking_log = []
        
        # Reset cache for new document
        self._masked_cache.clear()
        
        # Mask emails (highest priority for PII)
        masked_text, email_count = self._mask_emails(masked_text)
        mask_count += email_count
        if email_count > 0:
            sensitivity_map["email"] = email_count
            masking_log.append(f"Masked {email_count} email address(es)")
        
        # Mask phone numbers
        masked_text, phone_count = self._mask_phones(masked_text)
        mask_count += phone_count
        if phone_count > 0:
            sensitivity_map["phone"] = phone_count
            masking_log.append(f"Masked {phone_count} phone number(s)")
        
        # Mask SSN
        masked_text, ssn_count = self._mask_ssn(masked_text)
        mask_count += ssn_count
        if ssn_count > 0:
            sensitivity_map["ssn"] = ssn_count
            masking_log.append(f"Masked {ssn_count} SSN(s)")
        
        # Mask addresses
        masked_text, addr_count = self._mask_addresses(masked_text)
        mask_count += addr_count
        if addr_count > 0:
            sensitivity_map["address"] = addr_count
            masking_log.append(f"Masked {addr_count} address(es)")
        
        # Mask DOB
        masked_text, dob_count = self._mask_dob(masked_text)
        mask_count += dob_count
        if dob_count > 0:
            sensitivity_map["dob"] = dob_count
            masking_log.append(f"Masked {dob_count} date of birth pattern(s)")
        
        # Mask zip codes
        masked_text, zip_count = self._mask_zip_codes(masked_text)
        mask_count += zip_count
        if zip_count > 0:
            sensitivity_map["zip_code"] = zip_count
            masking_log.append(f"Masked {zip_count} zip code(s)")
        
        return MaskingResult(
            masked_text=masked_text,
            mask_count=mask_count,
            sensitivity_detected=sensitivity_map,
            masking_log=masking_log
        )
    
    def _mask_emails(self, text: str) -> Tuple[str, int]:
        """Mask email addresses with generic placeholder."""
        count = 0
        
        def replace_email(match):
            nonlocal count
            email = match.group(0)
            
            # Use consistent placeholder for same email
            if email not in self._masked_cache:
                count += 1
                self._masked_cache[email] = f"candidate.email{count}@example.com"
            
            return self._masked_cache[email]
        
        masked = self.compiled_patterns["email"].sub(replace_email, text)
        return masked, count
    
    def _mask_phones(self, text: str) -> Tuple[str, int]:
        """Mask phone numbers with generic placeholder."""
        count = 0
        
        def replace_phone(match):
            nonlocal count
            phone = match.group(0)
            
            if phone not in self._masked_cache:
                count += 1
                self._masked_cache[phone] = f"+1-555-000-{count:04d}"
            
            return self._masked_cache[phone]
        
        # Mask US format first (more specific)
        masked = self.compiled_patterns["phone_us"].sub(replace_phone, text)
        
        # Then mask international formats (be careful not to mask dates/numbers)
        # Only mask if pattern looks like a phone (has country code or formatting)
        def replace_intl_phone(match):
            nonlocal count
            phone = match.group(0)
            
            # Skip if it's just a sequence of numbers without phone formatting
            if not re.search(r'[+\-.\s()]', phone):
                return phone
            
            if phone not in self._masked_cache:
                count += 1
                self._masked_cache[phone] = f"+1-555-{count:03d}-0000"
            
            return self._masked_cache[phone]
        
        # Only apply intl pattern to text with phone indicators
        if re.search(r'\b(?:phone|tel|mobile|cell)\b', text, re.IGNORECASE):
            masked = self.compiled_patterns["phone_intl"].sub(replace_intl_phone, masked)
        
        return masked, count
    
    def _mask_ssn(self, text: str) -> Tuple[str, int]:
        """Mask Social Security Numbers."""
        count = 0
        
        def replace_ssn(match):
            nonlocal count
            count += 1
            return "***-**-****"
        
        masked = self.compiled_patterns["ssn"].sub(replace_ssn, text)
        return masked, count
    
    def _mask_addresses(self, text: str) -> Tuple[str, int]:
        """Mask physical addresses."""
        count = 0
        
        def replace_address(match):
            nonlocal count
            count += 1
            return "[Address Redacted]"
        
        masked = self.compiled_patterns["address"].sub(replace_address, text)
        return masked, count
    
    def _mask_dob(self, text: str) -> Tuple[str, int]:
        """Mask Date of Birth patterns."""
        count = 0
        
        def replace_dob(match):
            nonlocal count
            count += 1
            return "MM/DD/YYYY"
        
        masked = self.compiled_patterns["dob_slash"].sub(replace_dob, text)
        masked = self.compiled_patterns["dob_dash"].sub(replace_dob, masked)
        return masked, count
    
    def _mask_zip_codes(self, text: str) -> Tuple[str, int]:
        """Mask zip codes (context-aware to avoid false positives)."""
        count = 0
        
        def replace_zip(match):
            nonlocal count
            # Only mask if near address keywords
            context_window = 50
            start = max(0, match.start() - context_window)
            end = min(len(text), match.end() + context_window)
            context = text[start:end].lower()
            
            if re.search(r'\b(?:city|state|address|zip|postal|location)\b', context):
                count += 1
                return "XXXXX"
            return match.group(0)
        
        masked = self.compiled_patterns["zip_code"].sub(replace_zip, text)
        return masked, count


class ClientSensitiveMasker:
    """
    Masks client-sensitive information from Job Description documents.
    
    Targets:
    - Client company names
    - Project codes and internal references
    - Confidential project details
    - Internal budget/pricing information
    - Proprietary technology names
    """
    
    # Patterns for client-sensitive information
    PATTERNS = {
        "client_ref": r'\b(?:client|customer)[-\s]?(?:id|ref|code|number)[:\s]*[A-Z0-9-]+\b',
        "project_code": r'\b(?:project|proj|prj)[-\s]?(?:id|code|ref)[:\s]*[A-Z0-9-]+\b',
        "confidential": r'\b(?:confidential|proprietary|internal\s+only|do\s+not\s+share)\b',
        "budget": r'\$[\d,]+(?:\.\d{2})?(?:\s*(?:k|K|M|million|thousand))?',
        "internal_code": r'\b[A-Z]{2,4}-\d{3,6}\b',  # e.g., PROJ-12345, ABC-999
    }
    
    # Common company suffixes to help identify company names
    COMPANY_SUFFIXES = {
        "inc", "incorporated", "corp", "corporation", "llc", "ltd", "limited",
        "company", "co", "group", "holdings", "ventures", "partners", "technologies",
        "tech", "systems", "solutions", "services", "consulting", "enterprises"
    }
    
    def __init__(self):
        """Initialize client-sensitive masker."""
        self.compiled_patterns = {
            key: re.compile(pattern, re.IGNORECASE)
            for key, pattern in self.PATTERNS.items()
        }
        self._masked_cache: Dict[str, str] = {}
        self._company_name_cache: Set[str] = set()
    
    def mask_jd(self, jd_text: str, known_client_names: List[str] = None) -> MaskingResult:
        """
        Mask client-sensitive information from Job Description.
        
        Args:
            jd_text: Raw JD text
            known_client_names: Optional list of specific client names to mask
            
        Returns:
            MaskingResult with masked text and statistics
        """
        masked_text = jd_text
        mask_count = 0
        sensitivity_map = {}
        masking_log = []
        
        # Reset cache for new document
        self._masked_cache.clear()
        self._company_name_cache.clear()
        
        # Mask known client names first (if provided)
        if known_client_names:
            for client_name in known_client_names:
                client_pattern = re.compile(re.escape(client_name), re.IGNORECASE)
                matches = len(client_pattern.findall(masked_text))
                if matches > 0:
                    masked_text = client_pattern.sub("[Client Company]", masked_text)
                    mask_count += matches
                    masking_log.append(f"Masked {matches} instance(s) of known client: {client_name[:20]}...")
        
        # Mask client references
        masked_text, ref_count = self._mask_client_refs(masked_text)
        mask_count += ref_count
        if ref_count > 0:
            sensitivity_map["client_ref"] = ref_count
            masking_log.append(f"Masked {ref_count} client reference(s)")
        
        # Mask project codes
        masked_text, proj_count = self._mask_project_codes(masked_text)
        mask_count += proj_count
        if proj_count > 0:
            sensitivity_map["project_code"] = proj_count
            masking_log.append(f"Masked {proj_count} project code(s)")
        
        # Mask confidential markers
        masked_text, conf_count = self._mask_confidential_markers(masked_text)
        mask_count += conf_count
        if conf_count > 0:
            sensitivity_map["confidential"] = conf_count
            masking_log.append(f"Masked {conf_count} confidential marker(s)")
        
        # Mask budget information
        masked_text, budget_count = self._mask_budget(masked_text)
        mask_count += budget_count
        if budget_count > 0:
            sensitivity_map["budget"] = budget_count
            masking_log.append(f"Masked {budget_count} budget reference(s)")
        
        # Mask internal codes
        masked_text, code_count = self._mask_internal_codes(masked_text)
        mask_count += code_count
        if code_count > 0:
            sensitivity_map["internal_code"] = code_count
            masking_log.append(f"Masked {code_count} internal code(s)")
        
        # Detect and mask company names (heuristic-based)
        masked_text, company_count = self._mask_company_names(masked_text)
        mask_count += company_count
        if company_count > 0:
            sensitivity_map["company_name"] = company_count
            masking_log.append(f"Masked {company_count} potential company name(s)")
        
        return MaskingResult(
            masked_text=masked_text,
            mask_count=mask_count,
            sensitivity_detected=sensitivity_map,
            masking_log=masking_log
        )
    
    def _mask_client_refs(self, text: str) -> Tuple[str, int]:
        """Mask client reference codes."""
        count = 0
        
        def replace_ref(match):
            nonlocal count
            count += 1
            return "[CLIENT-REF-REDACTED]"
        
        masked = self.compiled_patterns["client_ref"].sub(replace_ref, text)
        return masked, count
    
    def _mask_project_codes(self, text: str) -> Tuple[str, int]:
        """Mask project codes."""
        count = 0
        
        def replace_code(match):
            nonlocal count
            count += 1
            return "[PROJECT-CODE-REDACTED]"
        
        masked = self.compiled_patterns["project_code"].sub(replace_code, text)
        return masked, count
    
    def _mask_confidential_markers(self, text: str) -> Tuple[str, int]:
        """Mask confidential markers."""
        count = 0
        
        def replace_conf(match):
            nonlocal count
            count += 1
            return "[CONFIDENTIAL-REDACTED]"
        
        masked = self.compiled_patterns["confidential"].sub(replace_conf, text)
        return masked, count
    
    def _mask_budget(self, text: str) -> Tuple[str, int]:
        """Mask budget/pricing information."""
        count = 0
        
        def replace_budget(match):
            nonlocal count
            # Only mask if near budget/cost keywords
            context_window = 30
            start = max(0, match.start() - context_window)
            end = min(len(text), match.end() + context_window)
            context = text[start:end].lower()
            
            if re.search(r'\b(?:budget|cost|price|rate|salary|compensation|pay)\b', context):
                count += 1
                return "$[REDACTED]"
            return match.group(0)
        
        masked = self.compiled_patterns["budget"].sub(replace_budget, text)
        return masked, count
    
    def _mask_internal_codes(self, text: str) -> Tuple[str, int]:
        """Mask internal reference codes."""
        count = 0
        
        def replace_code(match):
            nonlocal count
            code = match.group(0)
            
            # Skip common acronyms (AWS, API, SQL, etc.)
            common_tech = {"AWS", "API", "SQL", "GCP", "PDF", "CSV", "XML", "JSON", "HTTP", "HTTPS", "REST", "SOAP"}
            if code.upper() in common_tech:
                return code
            
            count += 1
            return "[INTERNAL-CODE-REDACTED]"
        
        masked = self.compiled_patterns["internal_code"].sub(replace_code, text)
        return masked, count
    
    def _mask_company_names(self, text: str) -> Tuple[str, int]:
        """
        Heuristic-based company name detection and masking.
        Looks for capitalized phrases followed by company suffixes.
        """
        count = 0
        
        # Pattern: Capitalized words + company suffix
        # e.g., "Acme Technologies", "XYZ Corp.", "ABC Consulting LLC"
        pattern = r'\b([A-Z][a-z]*(?:\s+[A-Z][a-z]*)*)\s+(' + '|'.join(
            re.escape(suffix) for suffix in self.COMPANY_SUFFIXES
        ) + r')\.?\b'
        
        company_pattern = re.compile(pattern, re.IGNORECASE)
        
        def replace_company(match):
            nonlocal count
            full_match = match.group(0)
            
            # Skip if it's a known technology/framework (false positive check)
            tech_keywords = {
                "microsoft", "amazon", "google", "oracle", "adobe", "apple",
                "python", "java", "react", "angular", "node"
            }
            if any(tech in full_match.lower() for tech in tech_keywords):
                return full_match
            
            # Skip if already cached
            if full_match in self._company_name_cache:
                return "[Client Company]"
            
            self._company_name_cache.add(full_match)
            count += 1
            return "[Client Company]"
        
        masked = company_pattern.sub(replace_company, text)
        return masked, count


class SecurityMasker:
    """
    Unified security masking interface for recruitment tool.
    Orchestrates PII and client-sensitive masking.
    """
    
    def __init__(self):
        """Initialize security masker with both PII and client maskers."""
        self.pii_masker = PIIMasker()
        self.client_masker = ClientSensitiveMasker()
    
    def mask_resume(self, resume_text: str) -> MaskingResult:
        """
        Mask PII from resume.
        
        Args:
            resume_text: Raw resume text
            
        Returns:
            MaskingResult with masked text
        """
        return self.pii_masker.mask_resume(resume_text)
    
    def mask_jd(
        self,
        jd_text: str,
        known_client_names: List[str] = None
    ) -> MaskingResult:
        """
        Mask client-sensitive information from JD.
        
        Args:
            jd_text: Raw JD text
            known_client_names: Optional list of client names to mask
            
        Returns:
            MaskingResult with masked text
        """
        return self.client_masker.mask_jd(jd_text, known_client_names)
    
    def get_masking_summary(self, result: MaskingResult) -> str:
        """
        Generate human-readable summary of masking operation.
        
        Args:
            result: MaskingResult to summarize
            
        Returns:
            Formatted summary string
        """
        if result.mask_count == 0:
            return "✓ No sensitive information detected"
        
        summary_parts = [
            f"🔒 Masked {result.mask_count} sensitive item(s):",
        ]
        summary_parts.extend([f"  • {log}" for log in result.masking_log])
        
        return "\n".join(summary_parts)


# ==================== Utility Functions ====================

def create_masking_audit_log(result: MaskingResult, doc_type: str) -> Dict:
    """
    Create audit log entry for masking operation (no sensitive data).
    
    Args:
        result: MaskingResult from masking operation
        doc_type: "resume" or "jd"
        
    Returns:
        Audit log dictionary
    """
    import datetime
    
    return {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "document_type": doc_type,
        "mask_count": result.mask_count,
        "sensitivity_types": list(result.sensitivity_detected.keys()),
        "status": "success" if result.mask_count >= 0 else "failed",
    }


if __name__ == "__main__":
    # Example usage and testing
    
    sample_resume = """
    John Doe
    Email: john.doe@gmail.com
    Phone: +1-555-123-4567
    Address: 123 Main Street, Anytown, CA 12345
    SSN: 123-45-6789
    DOB: 01/15/1990
    
    PROFESSIONAL EXPERIENCE
    Senior Developer at TechCorp Inc.
    - Built Python applications
    - Contact: john.work@techcorp.com
    """
    
    sample_jd = """
    Client: Acme Technologies LLC (Client-ID: CLT-12345)
    Project Code: PROJ-67890
    
    CONFIDENTIAL - INTERNAL ONLY
    
    We are seeking a Python developer for our client project.
    Budget: $150,000 - $180,000
    Project Reference: ABC-12345
    
    Required Skills:
    - Python, AWS, PostgreSQL
    - 5+ years experience
    """
    
    masker = SecurityMasker()
    
    print("=" * 80)
    print("RESUME MASKING TEST")
    print("=" * 80)
    resume_result = masker.mask_resume(sample_resume)
    print("\nOriginal Resume (first 200 chars):")
    print(sample_resume[:200])
    print("\nMasked Resume:")
    print(resume_result.masked_text)
    print("\n" + masker.get_masking_summary(resume_result))
    
    print("\n" + "=" * 80)
    print("JD MASKING TEST")
    print("=" * 80)
    jd_result = masker.mask_jd(sample_jd, known_client_names=["Acme Technologies"])
    print("\nOriginal JD (first 200 chars):")
    print(sample_jd[:200])
    print("\nMasked JD:")
    print(jd_result.masked_text)
    print("\n" + masker.get_masking_summary(jd_result))
