# Legal NER Models

Named Entity Recognition models for legal document processing in MegaAgent Pro.

## Models

### 1. Legal Entities Model (`legal-ner-base`)
General-purpose legal entity extraction based on RoBERTa.

**Entities:**
- PERSON, ORGANIZATION, COURT
- CASE_NUMBER, DATE, STATUTE
- CFR_SECTION, VISA_TYPE, COUNTRY
- MONETARY_AMOUNT

### 2. EB-1A Specialized Model (`eb1a-ner-specialized`)
Domain-specific model for EB-1A visa case processing.

**Entities:**
- CRITERION_NAME, EVIDENCE_TYPE
- PUBLICATION, AWARD, PATENT_NUMBER
- CITATION_COUNT, INSTITUTION
- POSITION_TITLE, FIELD_OF_EXPERTISE
- SALARY_AMOUNT, MEMBERSHIP_ORG

### 3. Citation Extractor (`citation-extractor`)
Regex-enhanced transformer for legal citation extraction.

**Citation Types:**
- US Code: `8 U.S.C. § 1153`
- CFR: `8 C.F.R. § 204.5`
- Case Law: `Matter of Dhanasar, 26 I&N Dec. 884`
- USCIS Policy: `USCIS Policy Manual, Vol. 6, Part F, Ch. 2`

## Usage

```python
from legal.legal_ner_models import LegalNERPipeline

# Initialize pipeline
pipeline = LegalNERPipeline(model="eb1a-ner-specialized")

# Extract entities
text = "The applicant received the Nobel Prize in Physics in 2020..."
entities = pipeline.extract(text)

# Results
for entity in entities:
    print(f"{entity.text}: {entity.label} ({entity.confidence:.2f})")
```

## Training

See `config.yaml` for training configuration.

```bash
python -m legal.train_ner --config legal/legal_ner_models/config.yaml
```

## Performance

| Model | F1 Score | Precision | Recall |
|-------|----------|-----------|--------|
| legal-ner-base | 0.91 | 0.92 | 0.90 |
| eb1a-ner-specialized | 0.94 | 0.95 | 0.93 |
| citation-extractor | 0.97 | 0.98 | 0.96 |
