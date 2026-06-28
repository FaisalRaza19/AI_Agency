import os
import aiofiles
from abc import ABC, abstractmethod
from typing import Dict, Any

class StorageProvider(ABC):
    @abstractmethod
    async def save_file(self, filename: str, content: str) -> str:
        """Saves file content to the store and returns its path/identifier."""
        pass

    @abstractmethod
    async def read_file(self, filename: str) -> str:
        """Reads and returns file content from the store."""
        pass

class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: str = "storage/contracts"):
        self.base_dir = base_dir
        # Ensure private storage directory exists outside of any public webroot
        os.makedirs(self.base_dir, exist_ok=True)

    async def save_file(self, filename: str, content: str) -> str:
        # Sanitize filename to prevent directory traversal
        safe_name = os.path.basename(filename)
        filepath = os.path.join(self.base_dir, safe_name)
        async with aiofiles.open(filepath, "w", encoding="utf-8") as f:
            await f.write(content)
        return filepath

    async def read_file(self, filename: str) -> str:
        safe_name = os.path.basename(filename)
        filepath = os.path.join(self.base_dir, safe_name)
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Contract file '{filename}' not found.")
        async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
            return await f.read()

# Default local storage provider (can be swapped config-side for S3/Supabase storage easily)
storage_provider = LocalStorageProvider()

class DocumentGeneratorService:
    def __init__(self, provider: StorageProvider = storage_provider):
        self.storage = provider

    async def generate_contract(self, lead_id: str, company: str, agreed_price: float) -> str:
        """
        Assembles a premium SLA contract HTML document with the owner's digital signature,
        saves it securely using the StorageProvider, and returns the filepath.
        """
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>SLA Agreement - {company}</title>
    <style>
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: #0c0d0e;
            color: #e3e4e6;
            padding: 40px;
            max-width: 800px;
            margin: auto;
            border: 1px solid #1a1c1e;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        }}
        h1 {{
            color: #4285f4;
            font-family: monospace;
            text-transform: uppercase;
            border-bottom: 2px solid #1a1c1e;
            padding-bottom: 10px;
        }}
        .clause {{
            margin-bottom: 20px;
            line-height: 1.6;
        }}
        .amount {{
            font-size: 1.2em;
            color: #34a853;
            font-weight: bold;
        }}
        .signature-block {{
            margin-top: 50px;
            display: flex;
            justify-content: space-between;
            border-top: 1px solid #1a1c1e;
            padding-top: 20px;
        }}
        .signature {{
            font-family: 'Brush Script MT', cursive, sans-serif;
            font-size: 1.8em;
            color: #4285f4;
        }}
    </style>
</head>
<body>
    <h1>Master Service Level Agreement</h1>
    <p>This document constitutes a binding agreement between <strong>UABE Operations</strong> ("Provider") and <strong>{company}</strong> ("Client").</p>
    
    <div class="clause">
        <h3>1. Services Rendered</h3>
        <p>Provider will execute autonomous outbound lead generation, SEO optimization, and web presence scaling in alignment with agreed campaign parameters.</p>
    </div>

    <div class="clause">
        <h3>2. Financial Terms</h3>
        <p>Client agrees to subscribe to services at a monthly rate of <span class="amount">${agreed_price:,.2f} USD</span> per month, billed recurringly via Stripe.</p>
    </div>

    <div class="clause">
        <h3>3. Confidentiality & Security</h3>
        <p>Both parties agree to hold mutual proprietary information in strict confidence.</p>
    </div>

    <div class="signature-block">
        <div>
            <p><strong>Approved by Provider:</strong></p>
            <p class="signature">UABE Executive Brain</p>
        </div>
        <div>
            <p><strong>Approved by Client:</strong></p>
            <p class="signature">Pending Client E-Sign</p>
        </div>
    </div>
</body>
</html>
"""
        filename = f"{lead_id}_contract.html"
        # Save via StorageProvider abstraction to prevent public S3/FastAPI leak issues
        filepath = await self.storage.save_file(filename, html_content)
        return filepath

document_generator = DocumentGeneratorService()
