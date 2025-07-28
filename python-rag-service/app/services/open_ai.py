import os
import json
from langchain_openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

async def get_answer_from_openai(context: str, question: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set in environment.")

    model = OpenAI(
        temperature=0.3,
        max_tokens=600,
        openai_api_key=api_key
    )

    prompt = f"""
Answer the following question in **strict JSON format** with exactly two fields: 
"contextAnswer" and "additionalInfo".

CRITICAL RULES:
1. For monetary amounts:
   - Always use the exact format found in context (e.g. "9.800,96€" not "9800.96 Euro")
   - Never round or modify numbers
   - Preserve all currency symbols and formatting

2. Source prioritization:
   - Primary source MUST contain the exact numerical value
   - If multiple amounts exist, use the most specific one
   - Always include the page reference where the amount appears

3. Answer structure:
   - "contextAnswer" must contain:
     * The exact numerical value
     * The page number where found
     * Minimal surrounding context
   - "additionalInfo" should only contain:
     * Payment terms/conditions if explicitly mentioned
     * Tax/VAT details if specified
     * Leave empty if no relevant additions exist

CONTEXT HIERARCHY:
1. Exact amounts with page numbers
2. General mentions of totals
3. Payment terms (only if no amounts found)

BAD EXAMPLE:
{{
  "contextAnswer": "The contract mentions a total sum",
  "additionalInfo": "See payment terms on page 5"
}}

GOOD EXAMPLE:
{{
  "contextAnswer": "The total amount is 9.800,96€ (Page 7)",
  "additionalInfo": "Payment due in 2 installments (Page 5)"
}}

Current Context:
{context}

Question: {question}

Respond ONLY with valid JSON:
"""

    raw = await model.ainvoke(prompt)

    try:
        return json.loads(raw)
    except Exception as e:
        raise ValueError(f"Failed to parse response: {raw}")
