# Dynamic SAP OData URL Generator for Google Gemini LLM

This repository provides **System Prompts**, **Few-Shot Examples**, and a complete **Python SDK** powered by **Google Gemini** (`google-genai` SDK and Pydantic) to dynamically translate natural language queries into exact SAP S/4HANA OData API URLs.

---

## 1. Supported SAP OData Services

### A. Sales Order API (`API_SALES_ORDER_SRV`)
- **Service Name**: `API_SALES_ORDER_SRV`
- **Base URL**: `https://sapacd.hostlogic.hu/sap/opu/odata/sap/API_SALES_ORDER_SRV/`
- **Client**: `sap-client=900`
- **Format**: `$format=json`
- **Supported Entities (22 entities)**:
  1. `A_SalesOrder`: Sales Order Header (order type, net amount, sold-to party, creation date)
  2. `A_SalesOrderItem`: Sales Order Line Items (material, item number, quantity, net price, plant)
  3. `A_SalesOrderBillingPlan`: Header Billing Plan (periodic or milestone billing header)
  4. `A_SalesOrderBillingPlanItem`: Header Billing Plan Items (milestone dates, billing percentage)
  5. `A_SalesOrderHeaderPartner`: Header Partners (Sold-to party, Ship-to party, Bill-to party, Payer, Contact rep)
  6. `A_SalesOrderHeaderPrElement`: Header Pricing Conditions / Elements (gross value, discounts, freight, surcharge, tax)
  7. `A_SalesOrderItemBillingPlan`: Item-level Billing Plan Header
  8. `A_SalesOrderItemPartner`: Item-level Partners (item-specific ship-to party)
  9. `A_SalesOrderItemPartnerAddress`: Item Partner Physical Address details
  10. `A_SalesOrderItemPrElement`: Item Pricing Conditions / Pricing Elements (base price, unit discount, taxes)
  11. `A_SalesOrderItemRelatedObject`: Item Related Objects / DMS attachments
  12. `A_SalesOrderItemText`: Item Texts and Notes (packaging instructions, item remarks)
  13. `A_SalesOrderItmPrecdgProcFlow`: Item Preceding Process Flow (preceding quote or contract line item)
  14. `A_SalesOrderItmSubsqntProcFlow`: Item Subsequent Process Flow (outbound delivery item, invoice item)
  15. `A_SalesOrderPartnerAddress`: Header Partner Physical Address details (street, city, postal code, country)
  16. `A_SalesOrderPrecdgProcFlow`: Header Preceding Process Flow (predecessor document flow: inquiry, quotation)
  17. `A_SalesOrderRelatedObject`: Header Related Objects / Linked DMS documents
  18. `A_SalesOrderScheduleLine`: Schedule Lines / Delivery Schedule (requested delivery date, confirmed delivery date, quantity)
  19. `A_SalesOrderSubsqntProcFlow`: Header Subsequent Process Flow (downstream document flow: deliveries, goods issues, invoices)
  20. `A_SalesOrderText`: Header Texts and Notes (customer notes, internal instructions)
  21. `A_SlsOrderItemBillingPlanItem`: Detailed Item Billing Plan Item records
  22. `A_SlsOrdPaymentPlanItemDetails`: Payment Card / Payment Plan Details (credit card token, authorization, installment terms)

---

### B. Purchase Order API (`C_PURCHASEORDER_FS_SRV`)
- **Service Name**: `C_PURCHASEORDER_FS_SRV`
- **Base URL**: `https://sapacd.hostlogic.hu/sap/opu/odata/sap/C_PURCHASEORDER_FS_SRV/`
- **Primary Entity**: `C_PurchaseOrderFs`
- **Client**: `sap-client=900`
- **Format**: `$format=json`
- **Supported Query Options**:
  - `$top`: Limit number of records returned
  - `$filter`: Filter conditions (`Supplier eq '100001'`, `CompanyCode eq '1000'`, etc.)
  - `$select`: Projections (`PurchaseOrder,Supplier,NetPriceAmount`)
  - `$orderby`: Sorting (`CreationDate desc`)
  - `$expand`: Navigation properties (`to_PurchaseOrderItemFS`)

---

## 2. Dynamic URL Generation Rules

1. **Direct Key Lookup**:
   - When the user asks for a specific header entity by its identifier:
     - Sales Order: `A_SalesOrder('{order_id}')?sap-client=900&$format=json`
     - Purchase Order: `C_PurchaseOrderFs('{po_number}')?sap-client=900&$format=json`
2. **Child Entity Filtering**:
   - When the user queries child/subordinate entities belonging to a specific order:
     - `{EntityName}?$filter=SalesOrder eq '{order_id}'&sap-client=900&$format=json`
3. **Collections and Projections**:
   - Applying `$top`, `$orderby`, `$select`, or composite `$filter` logic.
4. **Mandatory Query Parameters**:
   - `sap-client=900` and `$format=json` are enforced on every URL.

---

## 3. Confidence Scoring Logic

The LLM computes a confidence score between `0.0` and `1.0`:
- **0.95 - 1.00**: High confidence. Exact entity recognized, primary key or standard filter value explicitly provided in the query.
- **0.85 - 0.94**: Strong confidence. Clear entity match with standard parameters or general collection request.
- **0.70 - 0.84**: Moderate confidence. Best matched entity identified, but some query ambiguities or inferred parameters.
- **< 0.70**: Low confidence. Ambiguous query or insufficient context.

---

## 4. Project Structure

```
SAP POC/
├── prompts/
│   ├── __init__.py
│   ├── sales_order_prompt.py        # Sales Order System Prompt + 11 Few-Shot Examples
│   └── purchase_order_prompt.py     # Purchase Order System Prompt + 6 Few-Shot Examples
├── sap_url_generator.py             # Google Gemini Generator (google-genai SDK)
├── sap_url_generator_azure.py       # Azure OpenAI Generator (openai SDK)
├── test_generator.py                # Benchmark test suite and interactive CLI REPL
├── .env.example                     # Environment template for Gemini & Azure OpenAI
└── README.md                        # Documentation
```

---

## 5. Setup & Usage

### 1. Configure Gemini API Key
Create a `.env` file or export `GEMINI_API_KEY`:
```bash
cp .env.example .env
# Edit .env and enter your key:
GEMINI_API_KEY=your_actual_gemini_api_key
```

### 2. Run the Benchmark Test Suite
Runs all 12 test cases verifying entity matching and URL generation:
```bash
# If GEMINI_API_KEY is configured:
python test_generator.py

# Or force mock simulation mode:
python test_generator.py --mock
```

### 3. Test a Single Query
```bash
python test_generator.py --query "Show me schedule lines for sales order 0005200001"
```

Output:
```
================================================================================
 Service Name:      API_SALES_ORDER_SRV
 Matched Entity:    A_SalesOrderScheduleLine
 Confidence Score:  96.0% (0.96)
 Query Type:        FILTER
--------------------------------------------------------------------------------
 Generated URL:
  https://sapacd.hostlogic.hu/sap/opu/odata/sap/API_SALES_ORDER_SRV/A_SalesOrderScheduleLine?$filter=SalesOrder eq '0005200001'&sap-client=900&$format=json
--------------------------------------------------------------------------------
 Parameters Extracted:
   • sales_order_id: 0005200001
 OData Options:
   • $filter: SalesOrder eq '0005200001'
--------------------------------------------------------------------------------
 Reasoning: Query references delivery schedule lines and confirmed dates. Matched A_SalesOrderScheduleLine.
================================================================================
```

### 4. Interactive REPL Mode
```bash
python test_generator.py --interactive
```

### 5. Python Code Usage
```python
from sap_url_generator import SAPUrlGenerator

# Initialize generator
generator = SAPUrlGenerator()

# 1. Sales Order Query
response = generator.generate_sales_order_url("Get pricing elements for sales order 0005200001")
print(response.generated_url)
# -> https://sapacd.hostlogic.hu/sap/opu/odata/sap/API_SALES_ORDER_SRV/A_SalesOrderHeaderPrElement?$filter=SalesOrder eq '0005200001'&sap-client=900&$format=json

# 2. Purchase Order Query
response = generator.generate_purchase_order_url("Show latest 5 purchase orders for supplier 100001")
print(response.generated_url)
# -> https://sapacd.hostlogic.hu/sap/opu/odata/sap/C_PURCHASEORDER_FS_SRV/C_PurchaseOrderFs?$filter=Supplier eq '100001'&$orderby=CreationDate desc&$top=5&sap-client=900&$format=json

# 3. Auto-detect Service from natural language query
response = generator.generate_url("What downstream delivery documents were generated from sales order 0005200001?")
print(response.matched_entity) # A_SalesOrderSubsqntProcFlow
print(response.confidence_score) # 0.95
```

---

## 6. Azure OpenAI Usage

### Configure `.env`
```env
AZURE_OPENAI_API_KEY=your_azure_openai_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
```

### Run via CLI
```bash
python sap_url_generator_azure.py "Show me schedule lines for sales order 0005200001"
```

### Python Code Usage
```python
from sap_url_generator_azure import AzureSAPUrlGenerator

azure_gen = AzureSAPUrlGenerator()
res = azure_gen.generate_url("Show top 5 purchase orders for supplier 100001")
print(res.generated_url)
# -> https://sapacd.hostlogic.hu/sap/opu/odata/sap/C_PURCHASEORDER_FS_SRV/C_PurchaseOrderFs?$filter=Supplier eq '100001'&$top=5&sap-client=900&$format=json
```

### Run Test Suite with Azure Engine
```bash
python test_generator.py --engine azure
```

