import asyncio
import json
from typing import Optional, List
import httpx
from app.config import settings

class ResilientLLMClient:
    def __init__(self):
        # Models ordered by hierarchy (Primary -> Fallbacks)
        self.gemini_models: List[str] = [
            "gemini-2.5-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-2.5-pro"
        ]
        self.claude_model: str = "claude-3-5-sonnet-20241022"
        self.current_key_index: int = 0

    async def _query_gemini(
        self, 
        client: httpx.AsyncClient, 
        model: str, 
        prompt: str, 
        system_instruction: Optional[str], 
        json_mode: bool,
        api_key: str
    ) -> Optional[str]:
        """Performs raw HTTPS API call to Gemini endpoints using a specific key."""
        if not api_key:
            print("WARNING: Provided Gemini API key is empty.")
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        params = {"key": api_key}
        headers = {"Content-Type": "application/json"}

        # Prepare payload structure
        contents_payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }

        # Add optional system directives
        if system_instruction:
            contents_payload["systemInstruction"] = {
                "parts": [
                    {"text": system_instruction}
                ]
            }

        # Handle JSON mode configurations
        if json_mode:
            contents_payload["generationConfig"] = {
                "responseMimeType": "application/json"
            }

        try:
            response = await client.post(
                url, 
                params=params, 
                headers=headers, 
                json=contents_payload, 
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                text_response = data["candidates"][0]["content"]["parts"][0]["text"]
                return text_response
            elif response.status_code == 429:
                print(f"Gemini API Rate Limited (429) on model '{model}'.")
                return "RATE_LIMIT"
            else:
                print(f"Gemini API Error {response.status_code} on model '{model}': {response.text}")
                return None
        except Exception as e:
            print(f"Exception during Gemini request on '{model}': {e}")
            return None

    async def _query_claude(
        self, 
        client: httpx.AsyncClient, 
        prompt: str, 
        system_instruction: Optional[str]
    ) -> Optional[str]:
        """Performs failover API call to Anthropic Claude endpoints."""
        if not settings.ANTHROPIC_API_KEY:
            print("WARNING: Fallback triggered, but ANTHROPIC_API_KEY is not set.")
            return None

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        payload = {
            "model": self.claude_model,
            "max_tokens": 4096,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        if system_instruction:
            payload["system"] = system_instruction

        print(f"Executing final failover fallback on Anthropic model '{self.claude_model}'...")
        try:
            response = await client.post(
                url, 
                headers=headers, 
                json=payload, 
                timeout=45.0
            )
            
            if response.status_code == 200:
                data = response.json()
                text_response = data["content"][0]["text"]
                return text_response
            else:
                print(f"Anthropic Claude API Error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"Exception during Anthropic Claude request: {e}")
            return None

    async def generate_text(
        self, 
        prompt: str, 
        system_instruction: Optional[str] = None, 
        json_mode: bool = False,
        _http_client: Optional[httpx.AsyncClient] = None
    ) -> str:
        """
        Public text generation API wrapper.
        Cycles through Gemini models hierarchy; rotates API keys upon 429 quota errors;
        falls back to Anthropic Claude as a final gate.
        """
        async def _run(client: httpx.AsyncClient) -> str:
            # Load keys list dynamically from config settings
            keys = settings.gemini_keys_list
            
            # 1. Cycle through Gemini models hierarchy
            for model in self.gemini_models:
                if not keys:
                    print("No Gemini keys found in configurations. Skipping Gemini hierarchy.")
                    break
                
                max_keys = len(keys)
                keys_tried = 0
                retries = 2
                backoff = 0.5  # low initial sleep since key rotation takes precedence
                
                # Try to resolve request on the current model tier by rotating keys if rate limited
                while keys_tried < max_keys and retries > 0:
                    active_key_idx = self.current_key_index
                    active_key = keys[active_key_idx]
                    
                    print(f"Attempting model '{model}' with Key Index {active_key_idx} (Retries left: {retries})...")
                    res = await self._query_gemini(client, model, prompt, system_instruction, json_mode, active_key)
                    
                    if res == "RATE_LIMIT":
                        # Instantly rotate key
                        self.current_key_index = (self.current_key_index + 1) % max_keys
                        print(f"Rotated key index from {active_key_idx} to {self.current_key_index} due to rate limit on model '{model}'.")
                        keys_tried += 1
                        retries -= 1
                        
                        if keys_tried >= max_keys:
                            # We tried all keys on this model tier, wait and let the next model attempt handle it,
                            # or if we have retries left, we wait and try again
                            await asyncio.sleep(backoff)
                            backoff *= 2.0
                            # Reset keys_tried to try the keys again on the next retry loop
                            keys_tried = 0
                        continue
                    elif res is not None:
                        print(f"Successfully generated response from model '{model}' using Key Index {active_key_idx}.")
                        return res
                    else:
                        # Non-429 error (e.g. 400 Bad Request) - break loop to rotate model tier
                        break
            
            # 2. Final Fallback to Anthropic Claude
            res_claude = await self._query_claude(client, prompt, system_instruction)
            if res_claude is not None:
                return res_claude

            # 3. All options exhausted
            raise RuntimeError("CRITICAL: All Gemini models and Anthropic Claude failover options have failed or are unconfigured.")

        # Dispatch: use injected client (tests) or create a real one (production)
        if _http_client is not None:
            return await _run(_http_client)
        else:
            async with httpx.AsyncClient() as client:
                return await _run(client)

# Instantiate global resilient model client
llm_client = ResilientLLMClient()
