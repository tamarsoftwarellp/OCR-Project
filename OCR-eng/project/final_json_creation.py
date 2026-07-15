import os
import json
import logging
from glob import glob
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError

# Configure Enterprise Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Tamil_Software_Fixed_Merger")

# ==========================================
# 1. FIXED DATA SCHEMAS (MATCHING YOUR DATA)
# ==========================================

class GlobalMetadata(BaseModel):
    patient_name: Optional[str] = None
    hospital_name: Optional[str] = None
    date: Optional[str] = None
    reference_or_claim_number: Optional[str] = None

class TableRow(BaseModel):
    # Flexible field structure mapping to handle any table dynamic schema format keys
    date: Optional[str] = None
    time: Optional[str] = None
    amount: Optional[str] = None
    type: Optional[str] = None
    serial_no: Optional[str] = None
    medication_or_item_name: Optional[str] = None
    dosage_frequency: Optional[str] = None

    def __hash__(self):
        # Dynamically builds hash using all provided fields to remove multi-page row duplicates safely
        dict_values = tuple((k, str(v).strip().lower()) for k, v in sorted(self.model_dump().items()) if v is not None)
        return hash(dict_values)

    def __eq__(self, other):
        if not isinstance(other, TableRow):
            return False
        return hash(self) == hash(other)

class TablePayload(BaseModel):
    table_name_or_purpose: str
    headers: List[str] = Field(default_factory=list)
    rows: List[TableRow] = Field(default_factory=list)

class Warnings(BaseModel):
    ignored_handwritten_content: List[str] = Field(default_factory=list)
    unmapped_ambiguous_text_regions: List[str] = Field(default_factory=list)

class PagePayload(BaseModel):
    page_number: int
    document_type_classified: str
    global_metadata: GlobalMetadata
    all_extracted_entities: Dict[str, Any] = Field(default_factory=dict) # Replaced dynamic_entities
    all_extracted_tables: List[TablePayload] = Field(default_factory=list) # Replaced table_fragment
    warnings: Warnings

# The output format layout schema matching your target requirement
class DocumentSubLedger(BaseModel):
    document_type: str
    pages_associated: List[int] = Field(default_factory=list)
    global_metadata: GlobalMetadata = Field(default_factory=GlobalMetadata)
    all_extracted_entities: Dict[str, Any] = Field(default_factory=dict)
    consolidated_tables: List[TableRow] = Field(default_factory=list)
    aggregated_warnings: Warnings = Field(default_factory=Warnings)

# ==========================================
# 2. UPDATED CORE MERGER ENGINE
# ==========================================

class EnterpriseIDPMerger:

    @staticmethod
    def _resolve_best_string(current: Optional[str], incoming: Optional[str]) -> Optional[str]:
        if not incoming or incoming.strip().lower() in ["null", "none", ""]:
            return current
        if not current or current.strip().lower() in ["null", "none", ""]:
            return incoming
        return incoming if len(incoming.strip()) > len(current.strip()) else current

    @classmethod
    def execute_merger(cls, input_directory: str, output_directory: str):
        os.makedirs(output_directory, exist_ok=True)
        search_pattern = os.path.join(input_directory, "raw_json_*.json")
        json_file_paths = glob(search_pattern)
        
        if not json_file_paths:
            logger.warning(f"No JSON files found matching 'raw_json_*.json' inside: {input_directory}")
            return

        validated_pages: List[PagePayload] = []
        for file_path in json_file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                validated_pages.append(PagePayload(**raw_data))
            except (json.JSONDecodeError, ValidationError) as e:
                logger.error(f"Skipping broken input file '{os.path.basename(file_path)}': {e}")
                continue

        # Sort files sequentially by page integer value check
        validated_pages.sort(key=lambda p: p.page_number)
        
        extracted_documents: Dict[str, DocumentSubLedger] = {}
        table_deduplication_registry: Dict[str, set] = {}

        for page in validated_pages:
            doc_type_key = page.document_type_classified.strip().lower().replace(" ", "_")
            
            if doc_type_key not in extracted_documents:
                extracted_documents[doc_type_key] = DocumentSubLedger(
                    document_type=page.document_type_classified.strip()
                )
                table_deduplication_registry[doc_type_key] = set()

            sub_ledger = extracted_documents[doc_type_key]
            sub_ledger.pages_associated.append(page.page_number)
            
            # A. Reduce Metadata
            m_meta = sub_ledger.global_metadata
            p_meta = page.global_metadata
            m_meta.patient_name = cls._resolve_best_string(m_meta.patient_name, p_meta.patient_name)
            m_meta.hospital_name = cls._resolve_best_string(m_meta.hospital_name, p_meta.hospital_name)
            m_meta.date = cls._resolve_best_string(m_meta.date, p_meta.date)
            m_meta.reference_or_claim_number = cls._resolve_best_string(m_meta.reference_or_claim_number, p_meta.reference_or_claim_number)
            
            # B. Merge All Extracted Entities Keys
            for key, val in page.all_extracted_entities.items():
                if val is not None:
                    if key in sub_ledger.all_extracted_entities:
                        sub_ledger.all_extracted_entities[key] = cls._resolve_best_string(
                            str(sub_ledger.all_extracted_entities[key]), str(val)
                        )
                    else:
                        sub_ledger.all_extracted_entities[key] = val
            
            # C. Stitch Tables By Unwrapping Nested 'rows' Object Keys
            for table in page.all_extracted_tables:
                for row in table.rows:
                    if row not in table_deduplication_registry[doc_type_key]:
                        table_deduplication_registry[doc_type_key].add(row)
                        sub_ledger.consolidated_tables.append(row)
            
            # D. Merge Warnings Arrays
            sub_ledger.aggregated_warnings.ignored_handwritten_content.extend(page.warnings.ignored_handwritten_content)
            sub_ledger.aggregated_warnings.unmapped_ambiguous_text_regions.extend(page.warnings.unmapped_ambiguous_text_regions)

        # Write clean output payloads to disk files
        for doc_type_key, sub_ledger in extracted_documents.items():
            sub_ledger.aggregated_warnings.ignored_handwritten_content = list(set(sub_ledger.aggregated_warnings.ignored_handwritten_content))
            sub_ledger.aggregated_warnings.unmapped_ambiguous_text_regions = list(set(sub_ledger.aggregated_warnings.unmapped_ambiguous_text_regions))
            
            output_filename = f"master_{doc_type_key}.json"
            output_file_path = os.path.join(output_directory, output_filename)
            
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(sub_ledger.model_dump(), f, indent=4, ensure_ascii=False)
                
            logger.info(f"Successfully generated clean file matrix: {output_filename}")

# ==========================================
# 3. CONTEXT TESTING RUNTIME CALL
# ==========================================
if __name__ == "__main__":
    INPUT_DIR = os.path.join("RESULT/MEDSAVE", "06_llm_json")
    OUTPUT_DIR = os.path.join("RESULT/MEDSAVE", "07_master_json")
    EnterpriseIDPMerger.execute_merger(input_directory=INPUT_DIR, output_directory=OUTPUT_DIR)
