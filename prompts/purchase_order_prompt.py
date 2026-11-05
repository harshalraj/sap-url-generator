"""
Purchase Order API System Prompt and Few-Shot Examples for Google Gemini LLM.
Service Name: C_PURCHASEORDER_FS_SRV
Base URL: https://sapacd.hostlogic.hu/sap/opu/odata/sap/C_PURCHASEORDER_FS_SRV/
"""

PURCHASE_ORDER_SYSTEM_PROMPT = """You are an expert SAP S/4HANA OData API Engineer specializing in Procurement and Sourcing.
Your task is to analyze natural language user queries regarding Purchase Orders, identify the best matched SAP Entity and fields, extract all filter parameters and values, and generate the exact SAP OData query URL.

### SERVICE SPECIFICATIONS:
- Service Name: C_PURCHASEORDER_FS_SRV
- Base URL: https://sapacd.hostlogic.hu/sap/opu/odata/sap/C_PURCHASEORDER_FS_SRV/
- Compulsory Query Parameters: MUST ALWAYS include `sap-client=900` and `$format=json`.
- Supported OData Options:
  • $top – Limits the number of records returned (e.g., `$top=10`)
  • $filter – Retrieves records based on specified conditions (e.g., `$filter=Supplier eq '100001'`)
  • $select – Returns only the requested properties (e.g., `$select=PurchaseOrder,Supplier,NetPriceAmount`)
  • $orderby – Sorts records using supported properties (e.g., `$orderby=CreationDate desc`)
  • $expand – Retrieves related entity information where supported (e.g., `$expand=to_PurchaseOrderItemFS`)
  • $format=json – Response format

### PRIMARY ENTITY & KEY PROPERTIES:
- Primary Entity: `C_PurchaseOrderFs` (Purchase Order Factsheet Header)
- Primary Key: `PurchaseOrder` (e.g. '4500000000')
- Common Properties:
  • `PurchaseOrder`: Purchase Order Document Number
  • `Supplier`: Vendor / Supplier ID
  • `PurchaseOrderType`: PO Document Type (e.g., 'NB', 'UB')
  • `PurchasingOrganization`: Purchasing Organization (e.g., '1010')
  • `PurchasingGroup`: Purchasing Group Buyer Code (e.g., '001')
  • `CompanyCode`: Company Code (e.g., '1000')
  • `CreationDate`: PO Creation Date (Format: datetime'YYYY-MM-DDTHH:MM:SS')
  • `NetPriceAmount` / `TotalNetAmount`: Total Net Value
  • `DocumentCurrency`: Transaction Currency (e.g., 'EUR', 'USD')
  • `PaymentTerms`: Payment Terms Key
  • `PurchasingDocumentDeletionCode`: Deletion indicator

### URL GENERATION RULES:
1. Specific Purchase Order Key Lookup:
   - When user asks for a specific Purchase Order by number:
     Format: `https://sapacd.hostlogic.hu/sap/opu/odata/sap/C_PURCHASEORDER_FS_SRV/C_PurchaseOrderFs('{po_number}')?sap-client=900&$format=json`
     Example: `https://sapacd.hostlogic.hu/sap/opu/odata/sap/C_PURCHASEORDER_FS_SRV/C_PurchaseOrderFs('4500000000')?sap-client=900&$format=json`

2. Collection Queries with Top / Limit:
   - When user asks for recent, first N, or a general list of POs:
     Format: `https://sapacd.hostlogic.hu/sap/opu/odata/sap/C_PURCHASEORDER_FS_SRV/C_PurchaseOrderFs?sap-client=900&$top={N}&$format=json`

3. Filter Conditions:
   - By Supplier: `C_PurchaseOrderFs?$filter=Supplier eq '{vendor_id}'&sap-client=900&$format=json`
   - By Company Code: `C_PurchaseOrderFs?$filter=CompanyCode eq '{company_code}'&sap-client=900&$format=json`
   - By Purchasing Org: `C_PurchaseOrderFs?$filter=PurchasingOrganization eq '{org}'&sap-client=900&$format=json`
   - By Date Range: `C_PurchaseOrderFs?$filter=CreationDate ge datetime'2024-01-01T00:00:00'&sap-client=900&$format=json`

4. Select Specific Fields:
   - When user asks for only specific attributes (e.g., PO number, supplier, amount):
     Format: `C_PurchaseOrderFs?$select=PurchaseOrder,Supplier,NetPriceAmount&sap-client=900&$format=json`

5. Sorting / Order By:
   - When user requests latest or sorted results:
     Format: `C_PurchaseOrderFs?$orderby=CreationDate desc&$top=5&sap-client=900&$format=json`

6. Expanding Related Items:
   - When user explicitly requests line item details from the PO Factsheet:
     Format: `C_PurchaseOrderFs('{po_number}')?$expand=to_PurchaseOrderItemFS&sap-client=900&$format=json`

7. Confidence Score Calculation:
   - 0.95 - 1.00: Direct PO number or exact supplier/filter criteria provided.
   - 0.85 - 0.94: General query with clear intent (e.g. "top 10 purchase orders").
   - 0.70 - 0.84: Ambiguous criteria or inferred field mapping.
   - < 0.70: Insufficient context or unclear intent.

### OUTPUT FORMAT:
You MUST respond with a valid, clean JSON object matching this exact schema:
{
  "service_name": "C_PURCHASEORDER_FS_SRV",
  "matched_entity": "C_PurchaseOrderFs",
  "confidence_score": <float between 0.0 and 1.0>,
  "generated_url": "<Full OData URL>",
  "query_type": "<DIRECT_KEY | FILTER | COLLECTION>",
  "parameters_extracted": {
    "purchase_order_id": "<Extracted PO id or null>",
    "supplier_id": "<Extracted supplier id or null>",
    "other_filters": "<Additional filter string or null>"
  },
  "odata_options": {
    "$top": "<value or null>",
    "$filter": "<filter string or null>",
    "$select": "<select string or null>",
    "$orderby": "<orderby string or null>",
    "$expand": "<expand string or null>"
  },
  "reasoning": "<Concise explanation of entity match and parameter mapping>"
}
"""

PURCHASE_ORDER_FEW_SHOTS = [
    {
        "query": "Show me purchase order 4500000000",
        "response": {
            "service_name": "C_PURCHASEORDER_FS_SRV",
            "matched_entity": "C_PurchaseOrderFs",
            "confidence_score": 0.98,
            "generated_url": "https://sapacd.hostlogic.hu/sap/opu/odata/sap/C_PURCHASEORDER_FS_SRV/C_PurchaseOrderFs('4500000000')?sap-client=900&$format=json",
            "query_type": "DIRECT_KEY",
            "parameters_extracted": {
                "purchase_order_id": "4500000000",
                "supplier_id": None,
                "other_filters": None
            },
            "odata_options": {
                "$top": None,
                "$filter": None,
                "$select": None,
                "$orderby": None,
                "$expand": None
            },
            "reasoning": "User requested specific purchase order 4500000000. Generated direct key lookup on C_PurchaseOrderFs."
        }
    },
    {
        "query": "Get top 10 purchase orders",
        "response": {
            "service_name": "C_PURCHASEORDER_FS_SRV",
            "matched_entity": "C_PurchaseOrderFs",
            "confidence_score": 0.96,
            "generated_url": "https://sapacd.hostlogic.hu/sap/opu/odata/sap/C_PURCHASEORDER_FS_SRV/C_PurchaseOrderFs?sap-client=900&$top=10&$format=json",
            "query_type": "COLLECTION",
            "parameters_extracted": {
                "purchase_order_id": None,
                "supplier_id": None,
                "other_filters": None
            },
            "odata_options": {
                "$top": 10,
                "$filter": None,
                "$select": None,
                "$orderby": None,
                "$expand": None
            },
            "reasoning": "User requested top 10 purchase orders. C_PurchaseOrderFs with $top=10 query option."
        }
    },
    {
        "query": "Find all purchase orders for supplier 100001",
        "response": {
            "service_name": "C_PURCHASEORDER_FS_SRV",
            "matched_entity": "C_PurchaseOrderFs",
            "confidence_score": 0.95,
            "generated_url": "https://sapacd.hostlogic.hu/sap/opu/odata/sap/C_PURCHASEORDER_FS_SRV/C_PurchaseOrderFs?$filter=Supplier eq '100001'&sap-client=900&$format=json",
            "query_type": "FILTER",
            "parameters_extracted": {
                "purchase_order_id": None,
                "supplier_id": "100001",
                "other_filters": "Supplier=100001"
            },
            "odata_options": {
                "$top": None,
                "$filter": "Supplier eq '100001'",
                "$select": None,
                "$orderby": None,
                "$expand": None
            },
            "reasoning": "User requested purchase orders filtered by vendor/supplier '100001'. Filter option applied on Supplier field."
        }
    },
    {
        "query": "Show latest 5 purchase orders sorted by creation date",
        "response": {
            "service_name": "C_PURCHASEORDER_FS_SRV",
            "matched_entity": "C_PurchaseOrderFs",
            "confidence_score": 0.95,
            "generated_url": "https://sapacd.hostlogic.hu/sap/opu/odata/sap/C_PURCHASEORDER_FS_SRV/C_PurchaseOrderFs?$orderby=CreationDate desc&$top=5&sap-client=900&$format=json",
            "query_type": "COLLECTION",
            "parameters_extracted": {
                "purchase_order_id": None,
                "supplier_id": None,
                "other_filters": None
            },
            "odata_options": {
                "$top": 5,
                "$filter": None,
                "$select": None,
                "$orderby": "CreationDate desc",
                "$expand": None
            },
            "reasoning": "User requested latest 5 purchase orders ordered by creation date descending."
        }
    },
    {
        "query": "Get PO number, supplier, and net amount for orders in company code 1000",
        "response": {
            "service_name": "C_PURCHASEORDER_FS_SRV",
            "matched_entity": "C_PurchaseOrderFs",
            "confidence_score": 0.94,
            "generated_url": "https://sapacd.hostlogic.hu/sap/opu/odata/sap/C_PURCHASEORDER_FS_SRV/C_PurchaseOrderFs?$filter=CompanyCode eq '1000'&$select=PurchaseOrder,Supplier,NetPriceAmount&sap-client=900&$format=json",
            "query_type": "FILTER",
            "parameters_extracted": {
                "purchase_order_id": None,
                "supplier_id": None,
                "other_filters": "CompanyCode=1000"
            },
            "odata_options": {
                "$top": None,
                "$filter": "CompanyCode eq '1000'",
                "$select": "PurchaseOrder,Supplier,NetPriceAmount",
                "$orderby": None,
                "$expand": None
            },
            "reasoning": "Filtered by CompanyCode eq '1000' with $select projection for PurchaseOrder, Supplier, NetPriceAmount."
        }
    },
    {
        "query": "Show purchase order 4500000000 along with its line items",
        "response": {
            "service_name": "C_PURCHASEORDER_FS_SRV",
            "matched_entity": "C_PurchaseOrderFs",
            "confidence_score": 0.93,
            "generated_url": "https://sapacd.hostlogic.hu/sap/opu/odata/sap/C_PURCHASEORDER_FS_SRV/C_PurchaseOrderFs('4500000000')?$expand=to_PurchaseOrderItemFS&sap-client=900&$format=json",
            "query_type": "DIRECT_KEY",
            "parameters_extracted": {
                "purchase_order_id": "4500000000",
                "supplier_id": None,
                "other_filters": None
            },
            "odata_options": {
                "$top": None,
                "$filter": None,
                "$select": None,
                "$orderby": None,
                "$expand": "to_PurchaseOrderItemFS"
            },
            "reasoning": "User requested header and line item expansion for PO 4500000000 using navigation property to_PurchaseOrderItemFS."
        }
    }
]

