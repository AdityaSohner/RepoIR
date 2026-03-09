import base64
import io
import os
from openai import OpenAI

# 🔑 GET YOUR KEY HERE: https://cloud.sambanova.ai/
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY")

class VisionDescriber:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.sambanova.ai/v1",
            api_key=SAMBANOVA_API_KEY
        )

    def _encode_image(self, image_source):
        """Helper to convert any source into a Base64 string."""
        if isinstance(image_source, str):
            with open(image_source, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
        else:
            # Handle RAM streams (io.BytesIO)
            image_source.seek(0)
            return base64.b64encode(image_source.read()).decode('utf-8')

    def describe(self, image_source) -> str:
        """
        High-Precision Identification: Anime, Cars, Movies, Screenshots.
        """
        try:
            base64_img = self._encode_image(image_source)
            
            # The "Precision Identity" Prompt
            prompt = (
                "Describe this image comprehensively for a semantic search engine. Focus on both content and aesthetic context. "
                "1. IDENTIFICATION: Name specific entities (people, places, objects, brands). Use proper nouns (ex: 'Tanjiro Kamado', 'Ford Mustang 1969'). "
                "2. SUBJECT CATEGORY: State the broad category (ex: Anime, Street Photography, Document Screenshot, Movie Still, Digital Illustration, Shopping Item). "
                "3. AESTHETIC & MOOD: Describe the visual theme and vibe. Use keywords like 'Dark Themed', 'Moody', 'Minimalist', 'Vibrant', 'Vintage', 'Cyberpunk', 'Cinematic'. Mention lighting (ex: 'Dimly lit', 'Neon-glow', 'High contrast'). "
                "4. SPECIFIC DETAILS: "
                "   - If Anime/Movie: Series name, studio style (ex: 'Ufotable'), and thematic elements. "
                "   - If Screenshot/Document: Website/App name, UI layout, and key information found. "
                "   - If Photo: Scene context, color palette, and photographic style. "
                "RULES: "
                "- Write in a dense, descriptive paragraph format (minimum 150, max 250 words). "
                "- Use terms that reflect user search intent (ex: 'Amoled Wallpaper', 'Desktop Background', 'Project Assets'). "
                "- NO bullet points, NO emojis, and NO conversational filler."
            )

            completion = self.client.chat.completions.create(
                model="Llama-4-Maverick-17B-128E-Instruct",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_img}"
                                }
                            }
                        ]
                    }
                ],
                # We limit tokens to 300 to keep it efficient and fast
                max_tokens=300,
                temperature=0.1 # Low temperature = More factual/exact
            )

            return completion.choices[0].message.content
        except Exception as e:
            print(f"❌ SambaNova Vision Error: {e}")
            return ""

