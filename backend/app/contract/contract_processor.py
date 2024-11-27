import asyncio
import json
import os
import tempfile
from typing import List

import aiohttp
import convertapi
import tiktoken
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader

import core.config as config
from app.contract.contract_models import Clause, ContractType


class ContractProcessor:
    """
    Static class to process contracts and extract clauses.

    - parse_pdf_to_html: Convert a PDF file to HTML.
    - convert_pdf_to_html: Convert a PDF file to HTML and return the number of pages.
    - mark_clauses: Mark clauses in the HTML content.
    - get_number_of_pages: Get the number of pages in a PDF file.
    """

    @staticmethod
    def parse_pdf_to_html(file_path: str) -> str:
        result = convertapi.convert(
            "html", {"File": file_path, "Wysiwyg": "false"}, from_format="pdf"
        )
        return result.file.io.getvalue().decode("utf-8")

    @staticmethod
    def convert_pdf_to_html(file: bytes) -> tuple[str, int]:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf.write(file)
            temp_pdf_path = temp_pdf.name

        try:
            html = ContractProcessor.parse_pdf_to_html(temp_pdf_path)
            pages = ContractProcessor.get_number_of_pages(temp_pdf_path)
        finally:
            os.unlink(temp_pdf_path)

        return html, pages

    @staticmethod
    def mark_clauses(html: str) -> tuple[str, list[Clause]]:
        soup = BeautifulSoup(html, "html.parser")
        clauses = []

        for clause_counter, li in enumerate(
            soup.find_all("li", recursive=True), start=1
        ):
            if li.get_text(strip=True):
                li["data-is-clause"] = "true"
                li["data-location"] = "section"
                li["data-clause-id"] = f"clause-{clause_counter}"
                clauses.append(
                    Clause(
                        key=f"clause-{clause_counter}",
                        content=li.get_text(strip=True),
                        location=li["data-location"],
                    )
                )

        return str(soup), clauses

    @staticmethod
    def get_number_of_pages(file_path: str) -> int:
        with open(file_path, "rb") as file:
            reader = PdfReader(file)
            return len(reader.pages)

    #####################################################################
    ######## CONTRACT PROPERTY EXTRACTION ################################
    #####################################################################

    @staticmethod
    def preprocess_html(html_string: str) -> str:
        soup = BeautifulSoup(html_string, "html.parser")
        for tag in soup(["script", "style", "meta", "link"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    @staticmethod
    def split_into_chunks(text: str, max_tokens: int = 1000) -> List[str]:
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        tokens = encoding.encode(text)
        return [
            encoding.decode(tokens[i : i + max_tokens])
            for i in range(0, len(tokens), max_tokens)
        ]

    @staticmethod
    async def extract_multiple_properties(session, html_string, properties):
        prompts = "\n".join([f"- {prop['prompt']}" for prop in properties])
        property_names = ", ".join([f'"{prop["name"]}"' for prop in properties])
        json_instruction = (
            "Provide the extracted properties in valid JSON format with keys as property names. "
            f"Use the following property names exactly as keys: {property_names}. "
            "Ensure all property values are strings. "
            "Do not include any markdown formatting, code block markers, or additional text. "
            "Only output the JSON object."
        )
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert legal assistant analyzing contract clauses.",
                },
                {
                    "role": "user",
                    "content": f"Analyze the following content and extract properties:\n\n{html_string}\n\n{prompts}\n\n{json_instruction}",
                },
            ],
            "temperature": 0.1,
            "max_tokens": 500,
        }

        async with session.post(
            "https://api.openai.com/v1/chat/completions", json=payload
        ) as response:
            if response.status != 200:
                raise Exception(
                    f"OpenAI API error: {response.status} - {await response.text()}"
                )
            response_data = await response.json()
            print("Raw API Response:", response_data)
            response_text = response_data["choices"][0]["message"]["content"].strip()

            # Remove code block markers if present
            if response_text.startswith("```") and response_text.endswith("```"):
                # Remove the first line if it contains the code block language (e.g., 'json')
                lines = response_text.split("\n")
                if len(lines) > 1 and lines[0].strip().startswith("```"):
                    response_text = "\n".join(lines[1:-1])
                else:
                    response_text = "\n".join(lines[0:-1])
                response_text = response_text.strip()

            try:
                response_dict = json.loads(response_text)
            except json.JSONDecodeError as e:
                raise Exception(
                    f"Failed to parse assistant's response as JSON: {e}\nResponse Text:\n{response_text}"
                )
            return response_dict

    @staticmethod
    async def extract_key_properties(html_string: str) -> dict:
        properties_to_extract = [
            {
                "name": "duration",
                "prompt": "Find the contract's duration in years or months (e.g., '2 years, 5 months'). Respond only with the duration or 'Not specified'.",
            },
            {
                "name": "indemnity",
                "prompt": "Does the contract mention 'indemnity'? Answer 'True' or 'False'.",
            },
            {
                "name": "discount",
                "prompt": "Extract any discount mentioned (e.g., '10%'). If not found, respond 'Not specified'.",
            },
            {
                "name": "termination",
                "prompt": "Summarize the termination clause in one sentence, focusing on notice periods or conditions.",
            },
            {
                "name": "type",
                "prompt": "Identify the contract type. Choose from 'SERVICE_LEVEL_AGREEMENT', 'MASTER_SERVICE_AGREEMENT', 'NON_DISCLOSURE_AGREEMENT', or respond 'Not specified'.",
            },
            {
                "name": "parties_involved",
                "prompt": "Identify the parties involved in the contract. Provide their names or identifiers.",
            },
            {
                "name": "contract_date",
                "prompt": "Extract the contract's signing or effective date. If not found, respond 'Not specified'.",
            },
            {
                "name": "governing_law",
                "prompt": "Identify the governing law or jurisdiction. If not found, respond 'Not specified'.",
            },
            {
                "name": "payment_terms",
                "prompt": "Summarize the payment terms, including schedules or methods. If not found, respond 'Not specified'.",
            },
            {
                "name": "confidentiality",
                "prompt": "Does the contract include a confidentiality clause? If yes, provide a one-sentence summary.",
            },
        ]

        extracted_properties = {}
        cleaned_text = ContractProcessor.preprocess_html(html_string)
        print("Cleaned Text:", cleaned_text)

        chunks = ContractProcessor.split_into_chunks(cleaned_text)
        print("Chunks:", chunks)

        async with aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {config.openai.api_key}"}
        ) as session:
            tasks = [
                ContractProcessor.extract_multiple_properties(
                    session, chunk, properties_to_extract
                )
                for chunk in chunks
            ]
            chunk_results = await asyncio.gather(*tasks)

            # Frequency-Based Aggregation
            from collections import Counter

            for prop in properties_to_extract:
                results = []
                for res in chunk_results:
                    if isinstance(res, dict):
                        value = res.get(prop["name"], "Not specified")
                        if prop["name"] == "parties_involved":
                            # If it's a list or dict, convert to a sorted string representation
                            if isinstance(value, (dict, list)):
                                value = (
                                    ", ".join(sorted(value))
                                    if isinstance(value, list)
                                    else ", ".join(sorted(value.keys()))
                                )
                            value = str(value)
                        else:
                            value = str(value)
                        results.append(value)
                count = Counter(results)
                extracted_properties[prop["name"]] = (
                    count.most_common(1)[0][0] if count else "Not specified"
                )

        # Validate and default the contract type
        contract_type = extracted_properties.get("type")
        valid_types = {ct.value for ct in ContractType}
        if contract_type not in valid_types:
            extracted_properties["type"] = ContractType.OTHER.value

        return extracted_properties
