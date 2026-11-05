"""
SAP OData Dynamic URL Generator using Azure OpenAI.

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


class AzureSAPUrlGenerator:
    """
    Generator that leverages Azure OpenAI to translate natural language into dynamic SAP OData URLs.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        azure_endpoint: Optional[str] = None,
        api_version: Optional[str] = None,
        deployment_name: Optional[str] = None,
    ):
        self.api_key = (
            api_key
            or os.environ.get("AZURE_OPENAI_API_KEY")
            or os.environ.get("AZURE_OPENAI_KEY")
        )
        self.azure_endpoint = (
            azure_endpoint
            or os.environ.get("AZURE_OPENAI_ENDPOINT")
        )
        self.api_version = (
            api_version
            or os.environ.get("AZURE_OPENAI_API_VERSION")
            or "2024-08-01-preview"
        )
        self.deployment_name = (
            deployment_name
            or os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")
            or os.environ.get("AZURE_OPENAI_MODEL")
            or "gpt-4o"
        )

        self.client = None
        if self.api_key and self.azure_endpoint:
            from openai import AzureOpenAI

            self.client = AzureOpenAI(
                api_key=self.api_key,
                azure_endpoint=self.azure_endpoint,
                api_version=self.api_version,
            )

    def _ensure_client(self):
        if not self.client:
            raise ValueError(
                "Azure OpenAI is not configured. Please set the following environment variables in .env:\n"
                "  • AZURE_OPENAI_API_KEY\n"
                "  • AZURE_OPENAI_ENDPOINT (e.g., https://your-resource.openai.azure.com/)\n"
                "  • AZURE_OPENAI_DEPLOYMENT_NAME (e.g., gpt-4o)\n"
                "  • AZURE_OPENAI_API_VERSION (e.g., 2024-08-01-preview)\n"
                "Or pass them directly to AzureSAPUrlGenerator(...)."
            )

    def _build_messages(
        self,
        system_prompt: str,
        few_shots: List[Dict[str, Any]],
        user_query: str,
    ) -> List[Dict[str, str]]:
        """Construct conversation messages including system instructions and few-shot pairs."""
        messages = [{"role": "system", "content": system_prompt}]

        for example in few_shots:
            messages.append({"role": "user", "content": example["query"]})
            messages.append({"role": "assistant", "content": json.dumps(example["response"])})

        messages.append({"role": "user", "content": user_query})
        return messages

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

    def _call_azure_openai(self, messages: List[Dict[str, str]]) -> ODataUrlResponse:
        """
        Calls Azure OpenAI using beta parse (Structured Outputs) with fallback
        to json_object response format.
        """
        self._ensure_client()

        # Method 1: Try Structured Outputs via beta.chat.completions.parse
        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.deployment_name,
                messages=messages,
                response_format=ODataUrlResponse,
                temperature=0.1,
            )
            result = completion.choices[0].message.parsed
            if result:
                return self._post_process_url(result)
        except Exception as parse_err:
            # If model does not support beta parse, fall back to json_object
            pass

        # Method 2: Standard JSON mode fallback
        completion = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        content = completion.choices[0].message.content
        data = json.loads(content)
        result = ODataUrlResponse(**data)
        return self._post_process_url(result)

    def generate_sales_order_url(self, query: str) -> ODataUrlResponse:
        """
        Generate dynamic SAP OData URL for Sales Order API (API_SALES_ORDER_SRV).
        """
        messages = self._build_messages(
            system_prompt=SALES_ORDER_SYSTEM_PROMPT,
            few_shots=SALES_ORDER_FEW_SHOTS,
            user_query=query,
        )
        return self._call_azure_openai(messages)

    def generate_purchase_order_url(self, query: str) -> ODataUrlResponse:
        """
        Generate dynamic SAP OData URL for Purchase Order API (C_PURCHASEORDER_FS_SRV).
        """
        messages = self._build_messages(
            system_prompt=PURCHASE_ORDER_SYSTEM_PROMPT,
            few_shots=PURCHASE_ORDER_FEW_SHOTS,
            user_query=query,
        )
        return self._call_azure_openai(messages)

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
        print(f"\nProcessing User Query (Azure OpenAI): '{user_q}'")
        try:
            generator = AzureSAPUrlGenerator()
            res = generator.generate_url(user_q)
            print(format_output_table(res))
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Usage: python sap_url_generator_azure.py <natural language query>")
        print("Example: python sap_url_generator_azure.py Show me schedule lines for sales order 0005200001")

