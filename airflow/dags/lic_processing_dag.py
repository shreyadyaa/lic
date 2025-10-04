import os
import json
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

# Import your custom modules - make sure the path is correct
try:
    from utils.pdf_extractor import LICReceiptExtractor, validate_financial_year
except ImportError:
    # Fallback for missing modules
    print("Warning: utils.pdf_extractor not found. Creating mock functions.")
    
    class LICReceiptExtractor:
        def __init__(self, pdf_path):
            self.pdf_path = pdf_path
            
        def extract_all_data(self):
            return {
                'document_type': 'LIC_RECEIPT',
                'premium_amount': '50000',
                'submission_date': '2025-01-15T10:30:00'
            }
    
    def validate_financial_year(submission_date, financial_year):
        return True, f"Valid for financial year {financial_year}"

# Define paths
INPUT_DIR = Path("/opt/airflow/dags/input")
PDF_PATH = INPUT_DIR / "lic_receipt.pdf"
METADATA_PATH = INPUT_DIR / "metadata.json"

# Ensure input directory exists
INPUT_DIR.mkdir(parents=True, exist_ok=True)

# Default DAG arguments
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    dag_id="lic_receipt_processing",
    default_args=default_args,
    description="Process LIC receipts: extract, validate, and clean up",
    schedule_interval=None,  # manual trigger
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["lic", "receipt", "processing"],
    is_paused_upon_creation=False,
)

def check_files_exist(**context):
    """Check if required files exist"""
    pdf_exists = PDF_PATH.exists()
    metadata_exists = METADATA_PATH.exists()
    print(f"PDF file exists: {pdf_exists}")
    print(f"Metadata file exists: {metadata_exists}")
    if not pdf_exists or not metadata_exists:
        print("Required files not found. Skipping processing.")
        return False
    return True

def extract_pdf_data(**context):
    """Extract data from PDF"""
    try:
        extractor = LICReceiptExtractor(str(PDF_PATH))
        extracted_data = extractor.extract_all_data()
        print("=== EXTRACTION RESULTS ===")
        print(f"Document Type: {extracted_data['document_type']}")
        print(f"Premium Amount: {extracted_data['premium_amount']}")
        print(f"Submission Date: {extracted_data['submission_date']}")
        
        # Push to XCom
        task_instance = context['task_instance']
        task_instance.xcom_push(key='extracted_data', value=extracted_data)
        
        return extracted_data
    except Exception as e:
        print(f"Error extracting PDF data: {str(e)}")
        raise

def validate_document(**context):
    """Validate if document is a LIC receipt"""
    try:
        task_instance = context['task_instance']
        extracted_data = task_instance.xcom_pull(task_ids='extract_pdf_data', key='extracted_data')
        
        if not extracted_data:
            print("No extracted data found. Cannot validate document.")
            return False
            
        document_type = extracted_data.get('document_type')
        print(f"=== DOCUMENT VALIDATION ===")
        print(f"Document Type: {document_type}")
        
        is_valid = document_type == "LIC_RECEIPT"
        task_instance.xcom_push(key='is_valid_document', value=is_valid)
        
        if is_valid:
            print("Document is a valid LIC receipt")
        else:
            print("This is not a valid LIC document")
            
        return is_valid
    except Exception as e:
        print(f"Error validating document: {str(e)}")
        raise

def validate_financial_year_task(**context):
    """Validate financial year against submission date"""
    try:
        task_instance = context['task_instance']
        extracted_data = task_instance.xcom_pull(task_ids='extract_pdf_data', key='extracted_data')
        is_valid_document = task_instance.xcom_pull(task_ids='validate_document', key='is_valid_document')
        
        if not is_valid_document:
            print("Skipping financial year validation - document is not valid")
            return
            
        # Load metadata
        try:
            with open(METADATA_PATH, 'r') as f:
                metadata = json.load(f)
            financial_year = metadata.get('financial_year')
        except Exception as e:
            print(f"Error loading metadata: {str(e)}")
            return
            
        submission_date_str = extracted_data.get('submission_date')
        if not submission_date_str:
            print("Could not extract submission date from receipt")
            return
            
        submission_date = datetime.fromisoformat(submission_date_str.replace('Z', '+00:00'))
        premium_amount = extracted_data.get('premium_amount')
        
        print(f"=== FINANCIAL YEAR VALIDATION ===")
        print(f"Financial Year: {financial_year}")
        print(f"Submission Date: {submission_date.strftime('%Y-%m-%d')}")
        print(f"Premium Amount: {premium_amount}")
        
        is_valid, message = validate_financial_year(submission_date, financial_year)
        
        if is_valid:
            print(f"{message}")
            print(f"Premium of {premium_amount} is valid for FY {financial_year}")
        else:
            print(f"{message}")
            
    except Exception as e:
        print(f"Error validating financial year: {str(e)}")
        raise

def cleanup_processed_files(**context):
    """Clean up processed files"""
    print("=== CLEANUP ===")
    print("Files processed successfully. You may remove them manually if needed.")
    print(f"PDF Path: {PDF_PATH}")
    print(f"Metadata Path: {METADATA_PATH}")
    # Uncomment if you want to delete files automatically
    # PDF_PATH.unlink(missing_ok=True)
    # METADATA_PATH.unlink(missing_ok=True)

# Define tasks
check_files_task = PythonOperator(
    task_id="check_files_exist",
    python_callable=check_files_exist,
    dag=dag,
)

extract_data_task = PythonOperator(
    task_id="extract_pdf_data",
    python_callable=extract_pdf_data,
    dag=dag,
)

validate_document_task = PythonOperator(
    task_id="validate_document",
    python_callable=validate_document,
    dag=dag,
)

validate_financial_year_task = PythonOperator(
    task_id="validate_financial_year",
    python_callable=validate_financial_year_task,
    dag=dag,
)

cleanup_task = PythonOperator(
    task_id="cleanup_processed_files",
    python_callable=cleanup_processed_files,
    dag=dag,
)

# Set task dependencies
check_files_task >> extract_data_task >> validate_document_task >> validate_financial_year_task >> cleanup_task