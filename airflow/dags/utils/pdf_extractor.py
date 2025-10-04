import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
import PyPDF2
from dateutil.parser import parse as date_parse

class LICReceiptExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.extracted_data = {}
        
    def extract_text_from_pdf(self) -> str:
        """Extract text content from PDF"""
        try:
            with open(self.pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            raise Exception(f"Error reading PDF: {str(e)}")
    
    def extract_document_type(self, text: str) -> str:
        """Extract document type from text"""
        # Look for LIC-specific keywords
        lic_keywords = [
            "life insurance corporation",
            "lic of india",
            "premium receipt",
            "policy number",
            "premium paid",
            "receipt no"
        ]
        
        text_lower = text.lower()
        matches = sum(1 for keyword in lic_keywords if keyword in text_lower)
        
        # If we find multiple LIC-related keywords, classify as LIC_RECEIPT
        if matches >= 3:
            return "LIC_RECEIPT"
        else:
            return "OTHER_DOCUMENT"
    
    def extract_premium_amount(self, text: str) -> Optional[float]:
        """Extract premium amount from text"""
        # Common patterns for premium amounts
        patterns = [
            r'premium[:\s]+(?:rs\.?|₹)?\s*([0-9,]+\.?[0-9]*)',
            r'amount[:\s]+(?:rs\.?|₹)?\s*([0-9,]+\.?[0-9]*)',
            r'paid[:\s]+(?:rs\.?|₹)?\s*([0-9,]+\.?[0-9]*)',
            r'₹\s*([0-9,]+\.?[0-9]*)',
            r'rs\.?\s*([0-9,]+\.?[0-9]*)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                try:
                    # Clean the amount string and convert to float
                    amount_str = matches[0].replace(',', '')
                    return float(amount_str)
                except ValueError:
                    continue
        
        return None
    
    def extract_submission_date(self, text: str) -> Optional[datetime]:
        """Extract submission date from text"""
        # Common date patterns
        date_patterns = [
            r'date[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'dated[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'receipt date[:\s]+(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{2,4})'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text.lower())
            for match in matches:
                try:
                    # Handle tuple matches from groups
                    date_str = match[0] if isinstance(match, tuple) else match
                    parsed_date = date_parse(date_str, fuzzy=True)
                    # Return the first successfully parsed date
                    return parsed_date
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def extract_all_data(self) -> Dict:
        """Extract all required data from the PDF"""
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {self.pdf_path}")
        
        # Extract text from PDF
        text = self.extract_text_from_pdf()
        
        # Extract all required fields
        document_type = self.extract_document_type(text)
        premium_amount = self.extract_premium_amount(text)
        submission_date = self.extract_submission_date(text)
        
        return {
            "document_type": document_type,
            "premium_amount": premium_amount,
            "submission_date": submission_date.isoformat() if submission_date else None,
            "raw_text": text[:500] + "..." if len(text) > 500 else text  # Store first 500 chars for debugging
        }

def validate_financial_year(submission_date: datetime, financial_year: str) -> Tuple[bool, str]:
    """
    Validate if submission date falls within the financial year
    
    Args:
        submission_date: The date from the receipt
        financial_year: Financial year string (e.g., "2023-24")
    
    Returns:
        Tuple of (is_valid, message)
    """
    try:
        # Parse financial year (e.g., "2023-24" -> start: 2023-04-01, end: 2024-03-31)
        year_parts = financial_year.split('-')
        start_year = int(year_parts[0])
        end_year = int(year_parts[1])
        
        # Financial year in India runs from April 1st to March 31st
        fy_start = datetime(start_year, 4, 1)
        fy_end = datetime(start_year + 1, 3, 31, 23, 59, 59)
        
        # Check if submission date falls within the financial year
        is_valid = fy_start <= submission_date <= fy_end
        
        if is_valid:
            return True, f"Premium submission date {submission_date.strftime('%Y-%m-%d')} is valid for FY {financial_year}"
        else:
            return False, f"Premium submission date {submission_date.strftime('%Y-%m-%d')} not in FY {financial_year}"
            
    except Exception as e:
        return False, f"Error validating financial year: {str(e)}"