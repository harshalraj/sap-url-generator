"""
SAP OData Dynamic URL Generator using Google Gemini.

Translates natural language user queries into dynamic SAP OData URLs for:
1. Sales Order API (API_SALES_ORDER_SRV) - 22 supported entities
2. Purchase Order API (C_PURCHASEORDER_FS_SRV) - C_PurchaseOrderFs
"""

import os
import json
import re
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file if available
load_dotenv()

from prompts.sales_order_prompt import (
    SALES_ORDER_SYSTEM_PROMPT,
    SALES_ORDER_FEW_SHOTS,
)
from prompts.purchase_order_prompt import (
    PURCHASE_ORDER_SYSTEM_PROMPT,
    PURCHASE_ORDER_FEW_SHOTS,
)

# Supported Entities Lists
SALES_ORDER_ENTITIES = [
    "A_SalesOrder",
    "A_SalesOrderItem",
    "A_SalesOrderBillingPlan",
    "A_SalesOrderBillingPlanItem",
    "A_SalesOrderHeaderPartner",
    "A_SalesOrderHeaderPrElement",
    "A_SalesOrderItemBillingPlan",
    "A_SalesOrderItemPartner",
    "A_SalesOrderItemPartnerAddress",
    "A_SalesOrderItemPrElement",
    "A_SalesOrderItemRelatedObject",
    "A_SalesOrderItemText",
    "A_SalesOrderItmPrecdgProcFlow",
    "A_SalesOrderItmSubsqntProcFlow",
    "A_SalesOrderPartnerAddress",
    "A_SalesOrderPrecdgProcFlow",
    "A_SalesOrderRelatedObject",
    "A_SalesOrderScheduleLine",
    "A_SalesOrderSubsqntProcFlow",
    "A_SalesOrderText",
    "A_SlsOrderItemBillingPlanItem",
    "A_SlsOrdPaymentPlanItemDetails",
]

PURCHASE_ORDER_ENTITIES = [
    "C_PurchaseOrderFs",
]


class ODataOptions(BaseModel):
    top: Optional[int] = Field(None, description="Value for $top query option")
    filter: Optional[str] = Field(None, description="Value for $filter query option")
    select: Optional[str] = Field(None, description="Value for $select query option")
    orderby: Optional[str] = Field(None, description="Value for $orderby query option")
    expand: Optional[str] = Field(None, description="Value for $expand query option")


class ParametersExtracted(BaseModel):
    sales_order_id: Optional[str] = Field(None, description="Extracted Sales Order ID")
    purchase_order_id: Optional[str] = Field(None, description="Extracted Purchase Order ID")
    item_id: Optional[str] = Field(None, description="Extracted Item Number")
    supplier_id: Optional[str] = Field(None, description="Extracted Supplier/Vendor ID")
    other_filters: Optional[str] = Field(None, description="Other key-value filters extracted as string")


class ODataUrlResponse(BaseModel):
    service_name: str = Field(..., description="SAP OData Service Name")
    matched_entity: str = Field(..., description="Best matched entity name from supported entities")
    confidence_score: float = Field(..., description="Confidence score between 0.0 and 1.0")
    generated_url: str = Field(..., description="Complete SAP OData URL with sap-client=900 and $format=json")
    query_type: str = Field(..., description="DIRECT_KEY | FILTER | COLLECTION")
    parameters_extracted: ParametersExtracted
    odata_options: ODataOptions
    reasoning: str = Field(..., description="Detailed explanation of entity match and parameter mapping")


class SAPUrlGenerator:
    """
    Generator that leverages Google Gemini to translate natural language into dynamic SAP OData URLs.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.model = model or os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"
        self.client = None

        if self.api_key:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)

    def _ensure_client(self):
        if not self.client:
            raise ValueError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY environment variable "
                "or pass api_key to SAPUrlGenerator(api_key='...')."
            )

    def _build_few_shot_contents(self, few_shots: List[Dict[str, Any]], user_query: str):
        """Construct multi-turn conversation messages with few-shot examples for Gemini."""
        from google.genai import types

        contents = []
        for example in few_shots:
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=example["query"])]
                )
            )
            contents.append(
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=json.dumps(example["response"]))]
                )
            )

        # Append actual user query
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_query)]
            )
        )
        return contents

    def _post_process_url(self, response: ODataUrlResponse) -> ODataUrlResponse:
        """
        Validates and ensures critical query parameters (sap-client=900, $format=json)
        and base URLs are properly formed.
        """
        url = response.generated_url

        # Ensure sap-client=900 is present
        if "sap-client=900" not in url:
            delimiter = "&" if "?" in url else "?"
            url += f"{delimiter}sap-client=900"

        # Ensure $format=json is present
        if "$format=json" not in url:
            delimiter = "&" if "?" in url else "?"
            url += f"{delimiter}$format=json"

        response.generated_url = url
        return response

    def _generate_with_retry(self, contents, config):
        """Generates content with automatic fallback across models if high demand (503) occurs."""
        import time

        models_to_try = [self.model]
        for fallback in ["gemini-2.5-flash", "gemini-2.0-flash"]:
            if fallback not in models_to_try:
                models_to_try.append(fallback)

        last_err = None
        for model_name in models_to_try:
            for attempt in range(2):
                try:
                    return self.client.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=config,
                    )
                except Exception as e:
                    last_err = e
                    err_msg = str(e)
                    if "503" in err_msg or "UNAVAILABLE" in err_msg or "high demand" in err_msg:
                        time.sleep(1)
                        continue
                    else:
                        raise e
        raise last_err

    def generate_sales_order_url(self, query: str) -> ODataUrlResponse:
        """
        Generate dynamic SAP OData URL for Sales Order API (API_SALES_ORDER_SRV).
        """
        self._ensure_client()
        from google.genai import types

        contents = self._build_few_shot_contents(SALES_ORDER_FEW_SHOTS, query)

        config = types.GenerateContentConfig(
            system_instruction=SALES_ORDER_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=ODataUrlResponse,
            temperature=0.1,
        )

        response = self._generate_with_retry(contents, config)

        if response.parsed:
            result = response.parsed
        else:
            data = json.loads(response.text)
            result = ODataUrlResponse(**data)

        return self._post_process_url(result)

    def generate_purchase_order_url(self, query: str) -> ODataUrlResponse:
        """
        Generate dynamic SAP OData URL for Purchase Order API (C_PURCHASEORDER_FS_SRV).
        """
        self._ensure_client()
        from google.genai import types

        contents = self._build_few_shot_contents(PURCHASE_ORDER_FEW_SHOTS, query)

        config = types.GenerateContentConfig(
            system_instruction=PURCHASE_ORDER_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=ODataUrlResponse,
            temperature=0.1,
        )

        response = self._generate_with_retry(contents, config)

        if response.parsed:
            result = response.parsed
        else:
            data = json.loads(response.text)
            result = ODataUrlResponse(**data)

        return self._post_process_url(result)

    def auto_detect_service(self, query: str) -> str:
        """
        Detects whether query pertains to Sales Order or Purchase Order based on keywords.
        """
        q_lower = query.lower()
        po_keywords = [
            "purchase order", "po ", "po#", "vendor", "supplier",
            "c_purchaseorderfs", "purchasing", "c_purchaseorder"
        ]
        so_keywords = [
            "sales order", "so ", "so#", "customer", "sold-to", "ship-to",
            "schedule line", "a_salesorder", "billing plan", "sales"
        ]

        po_score = sum(1 for kw in po_keywords if kw in q_lower)
        so_score = sum(1 for kw in so_keywords if kw in q_lower)

        if po_score > so_score:
            return "purchase"
        return "sales"

    def generate_url(self, query: str, service: Optional[str] = None) -> ODataUrlResponse:
        """
        Main entrypoint. If service is not specified, auto-detects from query.
        """
        selected_service = service.lower() if service else self.auto_detect_service(query)

        if selected_service in ["sales", "sales_order", "so"]:
            return self.generate_sales_order_url(query)
        elif selected_service in ["purchase", "purchase_order", "po"]:
            return self.generate_purchase_order_url(query)
        else:
            raise ValueError(f"Unknown service '{service}'. Must be 'sales' or 'purchase'.")


def format_output_table(result: ODataUrlResponse) -> str:
    """Format the ODataUrlResponse object into a readable display."""
    lines = [
        "=" * 80,
        f" Service Name:      {result.service_name}",
        f" Matched Entity:    {result.matched_entity}",
        f" Confidence Score:  {result.confidence_score * 100:.1f}% ({result.confidence_score:.2f})",
        f" Query Type:        {result.query_type}",
        "-" * 80,
        f" Generated URL:\n  {result.generated_url}",
        "-" * 80,
        " Parameters Extracted:",
    ]
    for k, v in result.parameters_extracted.model_dump().items():
        if v:
            lines.append(f"   • {k}: {v}")

    lines.append(" OData Options:")
    for k, v in result.odata_options.model_dump().items():
        if v:
            lines.append(f"   • ${k}: {v}")

    lines.append("-" * 80)
    lines.append(f" Reasoning: {result.reasoning}")
    lines.append("=" * 80)
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        user_q = " ".join(sys.argv[1:])
        print(f"\nProcessing User Query: '{user_q}'")
        try:
            generator = SAPUrlGenerator()
            res = generator.generate_url(user_q)
            print(format_output_table(res))
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage: python sap_url_generator.py <natural language query>")
        print("Example: python sap_url_generator.py Show me schedule lines for sales order 0005200001")

