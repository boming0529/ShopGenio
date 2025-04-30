import json
import uuid
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Any
import google.generativeai as genai
import tomllib  # Python 3.11+
    
# --- Entities ---
class ProductEntity(BaseModel):
    """define master product entity for ECommerceCraft"""
    # id: uuid.UUID = Field(description="product id", default_factory=lambda: uuid.uuid4())
    name: str = Field(description="product name")
    description: str = Field(description="description, about 50 to 100 words")
    price: float = Field(description="sale price")
    category: str = Field(description="product category")
    tags: List[str] = Field(description="product tags")

    @classmethod
    def get_gemini_schema(cls) -> dict:
        """Generate a Gemini-compatible JSON Schema without unsupported fields"""
        def clean_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
            """Recursively remove unsupported fields (title, $defs, default, etc.)"""
            cleaned = {}
            for key, value in schema.items():
                # Skip unsupported fields
                if key in {"title", "$defs", "default"}:
                    continue
                # Recursively clean nested dictionaries
                if isinstance(value, dict):
                    cleaned[key] = clean_schema(value)
                # Recursively clean lists (e.g., items in arrays)
                elif isinstance(value, list):
                    cleaned[key] = [clean_schema(item) if isinstance(item, dict) else item for item in value]
                else:
                    cleaned[key] = value
            return cleaned

        schema = cls.model_json_schema()
        return clean_schema(schema)

# --- Adapters ---
class GeminiAdapter:
    """turn Gemini API JSON into Product Entity"""
    @staticmethod
    def to_product(gemini_response: dict) -> ProductEntity:
        try:
            return ProductEntity.model_validate(gemini_response)
        except ValidationError as e:
            raise ValueError(f"Gemini API response is not Product schema: {e}")

# --- Infrastructure ---
class ConfigManager:
    def __init__(self, config_path: str = "config.toml"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """from toml fetch"""
        try:
            with open(self.config_path, 'rb') as file:
                return tomllib.load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"config file {self.config_path} is not exits")
        except tomllib.TOMLDecodeError:
            raise ValueError(f"config file {self.config_path} format error")

    def get_api_key(self) -> str:
        """fetch Gemini API Key"""
        return self.config.get("gemini", {}).get("api_key")
    
class GeminiClient:
    """Gemini API client for ECommerceCraft"""
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": ProductEntity.get_gemini_schema()
            }
        )

    def generate_product(self, prompt: str) -> dict:
        """call Gemini API generation product"""
        response = self.model.generate_content(prompt)
        return json.loads(response.text)

# --- Use Cases ---
class GenerateProductUseCase:
    """generate product business for shopGenio"""
    def __init__(self, gemini_client: GeminiClient, gemini_adapter: GeminiAdapter):
        self.gemini_client = gemini_client
        self.gemini_adapter = gemini_adapter

    def execute(self, product_name: str, keywords: List[str]) -> dict:
        """according to key words to generate product master data"""
        keywords_str = ", ".join(keywords)
        prompt = f"""
        Generate a structured product record for an e-commerce product named '{product_name}'. The record must include the following fields:
        - name: Product name
        - description: Product description (50-100 words, incorporating keywords: {keywords_str})
        - price: Reasonable price (in New Taiwan Dollars, based on market rates)
        - category: Product category
        - tags: List of tags including {keywords_str}
        The response must be in JSON format, adhering to the specified structure.
        """
        gemini_response = self.gemini_client.generate_product(prompt)
        return self.gemini_adapter.to_product(gemini_response)
    
# --- Main ---
def main():
    """shop genio"""
    try:
        # init infra
        config_manager = ConfigManager()
        api_key = config_manager.get_api_key()
        gemini_client = GeminiClient(api_key)
        gemini_adapter = GeminiAdapter()

        # use case 
        use_case = GenerateProductUseCase(gemini_client, gemini_adapter)

        # product key word
        product_name = "Wireless Bluetooth Earphones"
        keywords = ["High-Quality Sound", "Stylish", "Portable"]

        # execute use case
        product = use_case.execute(product_name, keywords)

        # response
        print(json.dumps(product.model_dump(), indent=2, ensure_ascii=False))

        # {
        #     "name": "Wireless Bluetooth Earphones",
        #     "description": "Experience music like never before with our Wireless Bluetooth Earphones. Enjoy High-Quality Sound with deep bass and crystal-clear treble. The Stylish and sleek design makes them a fashion statement. These earphones are incredibly Portable, perfect for workouts, commutes, and travel. Enjoy the freedom of wireless connectivity and long-lasting battery life.",
        #     "price": 1500.0,
        #     "category": "Electronics",
        #     "tags": [
        #         "High-Quality Sound",
        #         "Stylish",
        #         "Portable"
        #     ]
        # }

    except Exception as e:
        print(f"error: {str(e)}")

if __name__ == "__main__":
    main()
