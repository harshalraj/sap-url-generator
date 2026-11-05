"""
Test Suite and Interactive Runner for SAP OData Dynamic URL Generator.

Supports:
1. Live Gemini Mode (requires GEMINI_API_KEY)
2. Mock / Offline Mode (for testing without API key)
3. Interactive Shell (type queries and see generated URLs)
"""

import os
import sys
import argparse
from typing import List, Dict, Any
from sap_url_generator import (
    SAPUrlGenerator,
    ODataUrlResponse,
    ParametersExtracted,
    ODataOptions,
    format_output_table,
    SALES_ORDER_ENTITIES,
    PURCHASE_ORDER_ENTITIES,
)

# Benchmark queries spanning different entities and query patterns
BENCHMARK_QUERIES = [
    {
        "api": "sales",
        "query": "Show me sales order 0005200001",
        "expected_entity": "A_SalesOrder",
        "description": "Header direct key lookup",
    },
    {
        "api": "sales",
        "query": "Get line items and materials for sales order 0005200001",
        "expected_entity": "A_SalesOrderItem",
        "description": "Item details filter by order",
    },
    {
        "api": "sales",
        "query": "Check delivery schedule lines and confirmed shipment dates for order 0005200001",
        "expected_entity": "A_SalesOrderScheduleLine",
        "description": "Schedule lines entity mapping",
    },
    {
        "api": "sales",
        "query": "What are the pricing conditions and discounts for sales order 0005200001?",
        "expected_entity": "A_SalesOrderHeaderPrElement",
        "description": "Header pricing conditions",
    },
    {
        "api": "sales",
        "query": "Show the sold-to party and partner contacts for sales order 0005200001",
        "expected_entity": "A_SalesOrderHeaderPartner",
        "description": "Header business partners",
    },
    {
        "api": "sales",
        "query": "What downstream delivery or invoice documents were generated from sales order 0005200001?",
        "expected_entity": "A_SalesOrderSubsqntProcFlow",
        "description": "Subsequent process flow",
    },
    {
        "api": "sales",
        "query": "Find the preceding quotation document that created sales order 0005200001",
        "expected_entity": "A_SalesOrderPrecdgProcFlow",
        "description": "Preceding process flow",
    },
    {
        "api": "sales",
        "query": "Get internal notes and customer remarks for sales order 0005200001",
        "expected_entity": "A_SalesOrderText",
        "description": "Header texts and notes",
    },
    {
        "api": "sales",
        "query": "List the top 10 sales orders",
        "expected_entity": "A_SalesOrder",
        "description": "Collection top 10",
    },
    {
        "api": "purchase",
        "query": "Fetch details of purchase order 4500000000",
        "expected_entity": "C_PurchaseOrderFs",
        "description": "PO direct key lookup",
    },
    {
        "api": "purchase",
        "query": "Show all purchase orders for supplier 100001",
        "expected_entity": "C_PurchaseOrderFs",
        "description": "PO filtered by supplier",
    },
    {
        "api": "purchase",
        "query": "Show the 5 most recent purchase orders ordered by creation date",
        "expected_entity": "C_PurchaseOrderFs",
        "description": "PO collection with orderby and top",
    },
]


def mock_generate(query: str, api: str) -> ODataUrlResponse:
    """Simulate generator responses when no Gemini API key is configured."""
    q_lower = query.lower()
    import re

    # Extract numbers if present
    order_match = re.search(r'\b(000\d{7}|\d{10})\b', query)
    po_match = re.search(r'\b(45\d{8}|\d{10})\b', query)
    top_match = re.search(r'(?:top|first)\s+(\d+)', q_lower)
    supplier_match = re.search(r'supplier\s+(\w+)', q_lower)

    if api == "sales" or ("sales" in q_lower and "purchase" not in q_lower):
        order_id = order_match.group(1) if order_match else "0005200001"
        top_val = int(top_match.group(1)) if top_match else None

        if "schedule line" in q_lower or "shipment date" in q_lower:
            entity = "A_SalesOrderScheduleLine"
            url = f"https://sapacd.hostlogic.hu/sap/opu/odata/sap/API_SALES_ORDER_SRV/{entity}?$filter=SalesOrder eq '{order_id}'&sap-client=900&$format=json"
            q_type = "FILTER"
            reason = "Query references delivery schedule lines and confirmed dates. Matched A_SalesOrderScheduleLine."
            f_str = f"SalesOrder eq '{order_id}'"
        elif "pricing" in q_lower or "discount" in q_lower or "condition" in q_lower:
            entity = "A_SalesOrderHeaderPrElement"
            url = f"https://sapacd.hostlogic.hu/sap/opu/odata/sap/API_SALES_ORDER_SRV/{entity}?$filter=SalesOrder eq '{order_id}'&sap-client=900&$format=json"
            q_type = "FILTER"
            reason = "Query asks for pricing conditions and discounts at header level. Matched A_SalesOrderHeaderPrElement."
            f_str = f"SalesOrder eq '{order_id}'"
        elif "subsequent" in q_lower or "downstream" in q_lower or "invoice" in q_lower or "delivery doc" in q_lower:
            entity = "A_SalesOrderSubsqntProcFlow"
            url = f"https://sapacd.hostlogic.hu/sap/opu/odata/sap/API_SALES_ORDER_SRV/{entity}?$filter=SalesOrder eq '{order_id}'&sap-client=900&$format=json"
            q_type = "FILTER"
            reason = "Query asks for downstream/subsequent documents generated after the order. Matched A_SalesOrderSubsqntProcFlow."
            f_str = f"SalesOrder eq '{order_id}'"
        elif "preceding" in q_lower or "quotation" in q_lower or "inquiry" in q_lower:
            entity = "A_SalesOrderPrecdgProcFlow"
            url = f"https://sapacd.hostlogic.hu/sap/opu/odata/sap/API_SALES_ORDER_SRV/{entity}?$filter=SalesOrder eq '{order_id}'&sap-client=900&$format=json"
            q_type = "FILTER"
            reason = "Query asks for predecessor document flow like quotation or inquiry. Matched A_SalesOrderPrecdgProcFlow."
            f_str = f"SalesOrder eq '{order_id}'"
        elif "partner" in q_lower or "sold-to" in q_lower or "ship-to" in q_lower or "contact" in q_lower:
            entity = "A_SalesOrderHeaderPartner"
            url = f"https://sapacd.hostlogic.hu/sap/opu/odata/sap/API_SALES_ORDER_SRV/{entity}?$filter=SalesOrder eq '{order_id}'&sap-client=900&$format=json"
            q_type = "FILTER"
            reason = "Query asks for order partners (sold-to, contacts). Matched A_SalesOrderHeaderPartner."
            f_str = f"SalesOrder eq '{order_id}'"
        elif "item" in q_lower or "material" in q_lower or "product" in q_lower:
            entity = "A_SalesOrderItem"
            url = f"https://sapacd.hostlogic.hu/sap/opu/odata/sap/API_SALES_ORDER_SRV/{entity}?$filter=SalesOrder eq '{order_id}'&sap-client=900&$format=json"
            q_type = "FILTER"
            reason = "Query asks for line items and materials. Matched A_SalesOrderItem."
            f_str = f"SalesOrder eq '{order_id}'"
        elif "text" in q_lower or "note" in q_lower or "remark" in q_lower:
            entity = "A_SalesOrderText"
            url = f"https://sapacd.hostlogic.hu/sap/opu/odata/sap/API_SALES_ORDER_SRV/{entity}?$filter=SalesOrder eq '{order_id}'&sap-client=900&$format=json"
            q_type = "FILTER"
            reason = "Query asks for internal notes or remarks. Matched A_SalesOrderText."
            f_str = f"SalesOrder eq '{order_id}'"
        elif top_val:
            entity = "A_SalesOrder"
            url = f"https://sapacd.hostlogic.hu/sap/opu/odata/sap/API_SALES_ORDER_SRV/{entity}?sap-client=900&$top={top_val}&$format=json"
            q_type = "COLLECTION"
            reason = f"Query requests top {top_val} sales orders collection."
            f_str = None
        else:
            entity = "A_SalesOrder"
            url = f"https://sapacd.hostlogic.hu/sap/opu/odata/sap/API_SALES_ORDER_SRV/{entity}('{order_id}')?sap-client=900&$format=json"
            q_type = "DIRECT_KEY"
            reason = f"Query specifies sales order ID {order_id}. Matched A_SalesOrder direct key lookup."
            f_str = None

        return ODataUrlResponse(
            service_name="API_SALES_ORDER_SRV",
            matched_entity=entity,
            confidence_score=0.96,
            generated_url=url,
            query_type=q_type,
            parameters_extracted=ParametersExtracted(
                sales_order_id=order_id if q_type != "COLLECTION" else None
            ),
            odata_options=ODataOptions(
                top=top_val,
                filter=f_str,
            ),
            reasoning=f"[Mock Mode] {reason}",
        )
    else:
        # Purchase Order
        po_id = po_match.group(1) if po_match else "4500000000"
        supp_id = supplier_match.group(1) if supplier_match else None
        top_val = int(top_match.group(1)) if top_match else (5 if "recent" in q_lower else None)

        if supp_id:
            url = f"https://sapacd.hostlogic.hu/sap/opu/odata/sap/C_PURCHASEORDER_FS_SRV/C_PurchaseOrderFs?$filter=Supplier eq '{supp_id}'&sap-client=900&$format=json"
            q_type = "FILTER"
            f_str = f"Supplier eq '{supp_id}'"
            ob_str = None
            reason = f"Filtered purchase orders by Supplier '{supp_id}'."
        elif "recent" in q_lower or "latest" in q_lower:
            url = f"https://sapacd.hostlogic.hu/sap/opu/odata/sap/C_PURCHASEORDER_FS_SRV/C_PurchaseOrderFs?$orderby=CreationDate desc&$top={top_val or 5}&sap-client=900&$format=json"
            q_type = "COLLECTION"
            f_str = None
            ob_str = "CreationDate desc"
            reason = f"Recent purchase orders sorted by CreationDate descending with $top={top_val or 5}."
        elif top_val:
            url = f"https://sapacd.hostlogic.hu/sap/opu/odata/sap/C_PURCHASEORDER_FS_SRV/C_PurchaseOrderFs?sap-client=900&$top={top_val}&$format=json"
            q_type = "COLLECTION"
            f_str = None
            ob_str = None
            reason = f"Top {top_val} purchase orders collection."
        else:
            url = f"https://sapacd.hostlogic.hu/sap/opu/odata/sap/C_PURCHASEORDER_FS_SRV/C_PurchaseOrderFs('{po_id}')?sap-client=900&$format=json"
            q_type = "DIRECT_KEY"
            f_str = None
            ob_str = None
            reason = f"Specific purchase order direct key lookup for PO '{po_id}'."

        return ODataUrlResponse(
            service_name="C_PURCHASEORDER_FS_SRV",
            matched_entity="C_PurchaseOrderFs",
            confidence_score=0.97,
            generated_url=url,
            query_type=q_type,
            parameters_extracted=ParametersExtracted(
                purchase_order_id=po_id if q_type == "DIRECT_KEY" else None,
                supplier_id=supp_id,
            ),
            odata_options=ODataOptions(
                top=top_val,
                filter=f_str,
                orderby=ob_str,
            ),
            reasoning=f"[Mock Mode] {reason}",
        )


def run_benchmark(generator: SAPUrlGenerator, use_mock: bool = False):
    print("\n" + "=" * 80)
    print(f" RUNNING SAP ODATA URL GENERATOR BENCHMARK ({'MOCK MODE' if use_mock else 'LIVE GEMINI MODE'})")
    print("=" * 80)

    passed = 0
    total = len(BENCHMARK_QUERIES)

    for i, test in enumerate(BENCHMARK_QUERIES, 1):
        query = test["query"]
        expected = test["expected_entity"]
        api = test["api"]
        desc = test["description"]

        print(f"\n[{i}/{total}] Test: {desc}")
        print(f" Query:    \"{query}\"")
        print(f" Target:   {expected} ({api.upper()} API)")

        try:
            if use_mock:
                res = mock_generate(query, api)
            else:
                res = generator.generate_url(query, service=api)

            is_match = res.matched_entity == expected
            if is_match:
                passed += 1
                status = "PASSED [OK]"
            else:
                status = f"FAILED [Expected {expected}, got {res.matched_entity}]"

            print(f" Status:   {status}")
            print(f" Entity:   {res.matched_entity} (Confidence: {res.confidence_score * 100:.1f}%)")
            print(f" URL:      {res.generated_url}")
            print(f" Reasoning:{res.reasoning}")

        except Exception as e:
            print(f" Status:   ERROR: {e}")

    print("\n" + "=" * 80)
    print(f" BENCHMARK SUMMARY: {passed}/{total} Passed ({(passed/total)*100:.1f}%)")
    print("=" * 80)


def interactive_mode(generator: SAPUrlGenerator, use_mock: bool = False):
    print("\n" + "=" * 80)
    print(" SAP ODATA DYNAMIC URL GENERATOR - INTERACTIVE REPL")
    print(f" Mode: {'MOCK SIMULATION' if use_mock else 'LIVE GEMINI API'}")
    print(" Type your natural language queries below.")
    print(" Type 'exit' or 'quit' to stop.")
    print("=" * 80 + "\n")

    while True:
        try:
            user_input = input("Enter Query > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("Exiting interactive mode.")
                break

            if use_mock:
                detected = generator.auto_detect_service(user_input)
                res = mock_generate(user_input, detected)
            else:
                res = generator.generate_url(user_input)

            print("\n" + format_output_table(res) + "\n")

        except KeyboardInterrupt:
            print("\nExiting interactive mode.")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


def main():
    parser = argparse.ArgumentParser(description="SAP OData URL Generator Test and CLI")
    parser.add_argument("--engine", choices=["gemini", "azure"], default="gemini", help="LLM Provider: gemini or azure")
    parser.add_argument("--api-key", help="API key override")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode without calling LLM API")
    parser.add_argument("--interactive", action="store_true", help="Start interactive REPL session")
    parser.add_argument("--query", help="Single query to process")
    parser.add_argument("--service", choices=["sales", "purchase"], help="Explicitly specify service")
    args = parser.parse_args()

    if args.engine == "azure":
        from sap_url_generator_azure import AzureSAPUrlGenerator
        api_key = args.api_key or os.environ.get("AZURE_OPENAI_API_KEY") or os.environ.get("AZURE_OPENAI_KEY")
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        use_mock = args.mock or (not api_key or not endpoint)
        if use_mock and not args.mock:
            print("\nNote: AZURE_OPENAI_API_KEY or AZURE_OPENAI_ENDPOINT not found in .env. Running in Mock Mode.\n")
        generator = AzureSAPUrlGenerator(api_key=api_key)
        if not use_mock:
            print(f"Connected to Azure OpenAI successfully. Deployment: {generator.deployment_name}")
    else:
        api_key = args.api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        use_mock = args.mock or (not api_key)
        if use_mock and not args.mock:
            print("\nNote: GEMINI_API_KEY not found in environment. Defaulting to Mock Simulation Mode.")
            print("To run with live Gemini model, provide --api-key or set GEMINI_API_KEY in .env file.\n")
        generator = SAPUrlGenerator(api_key=api_key)
        if not use_mock:
            print(f"Connected to Gemini API successfully. Model: {generator.model}")

    if args.query:
        if use_mock:
            srv = args.service or generator.auto_detect_service(args.query)
            res = mock_generate(args.query, srv)
        else:
            res = generator.generate_url(args.query, service=args.service)
        print(format_output_table(res))
    elif args.interactive:
        interactive_mode(generator, use_mock=use_mock)
    else:
        # Default: run benchmark
        run_benchmark(generator, use_mock=use_mock)


if __name__ == "__main__":
    main()

