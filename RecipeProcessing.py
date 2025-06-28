import json
import uuid
import random
from datetime import datetime
from RecipeEmbedding import RecipeEmbedding
from DataManager import DataManager

class RecipeProcessing:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.recipe_embedding = RecipeEmbedding(model_name)
        self.processed_recipes = []
        self.data_manager = None
    
    def load_scraped_data(self, json_file_path: str):
        with open(json_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def generate_recipe_id(self, recipe_index: int):
        return f"recipe_{10001 + recipe_index}"
    
    def clean_ingredients(self, ingredients: list):
        if not ingredients:
            return []
        
        cleaned = []
        for ingredient in ingredients:
            if ingredient and isinstance(ingredient, str):
                ingredient = ingredient.strip()
                if ingredient and not any(skip in ingredient.lower() for skip in 
                    ['author:', 'total time:', 'yield:', 'prep time:', 'cook time:', 
                     'category:', 'method:', 'cuisine:']):
                    cleaned.append(ingredient)
        return cleaned
    
    def extract_ingredient_names_only(self, ingredients: list):
        import requests
        
        if not ingredients:
            return []
        
        ingredients_text = ', '.join([str(ing) for ing in ingredients if ing and isinstance(ing, str)])
        
        if not ingredients_text.strip():
            return []
        
        def clean_single(text):
            prompt = f"Extract only core ingredient names from: {text}\n \
            Return only ingredient names separated by commas, if you could not \
            get the ingredient names then return empty string, no other text:"
            payload = {
                "model": "llama3.2:3b",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "max_tokens": 200}
            }
            try:
                response = requests.post("http://localhost:11434/api/generate", json=payload)
                result = response.json().get('response', '').strip()
                ingredients = [ing.strip().title() for ing in result.split(',') if ing.strip()]
                return ingredients if ingredients else []
            except Exception as e:
                print(f"Error calling Llama model: {e}")
                return []
        
        clean_names = clean_single(ingredients_text)
        
        seen = set()
        unique_names = []
        for name in clean_names:
            name_lower = name.lower()
            if name_lower not in seen and len(name_lower) > 2:
                seen.add(name_lower)
                unique_names.append(name_lower)
        
        return unique_names
    
    def generate_random_calories(self):
        return random.randint(100, 300)
    
    def extract_numeric_value(self, value_str):
        if not value_str:
            return None
        if isinstance(value_str, str):
            import re
            numeric = re.search(r'\d+', value_str)
            return int(numeric.group()) if numeric else None
        return value_str
    
    def convert_to_iso_duration(self, minutes):
        if not minutes:
            return ""
        return f"PT{minutes}M"
    
    def calculate_total_time_iso(self, prep_time_minutes, cook_time_minutes):
        prep = prep_time_minutes or 0
        cook = cook_time_minutes or 0
        total = prep + cook
        return f"PT{total}M" if total > 0 else ""
    
    def format_images_c_notation(self, image_url):
        if not image_url:
            return ""
        return f'c("{image_url}")'
    
    def extract_ingredient_quantities(self, ingredients):
        quantities = []
        import re
        
        for ingredient in ingredients:
            quantity_match = re.search(r'^(\d+(?:\s*[-–]\s*\d+)?|\d+/\d+|\d+\.\d+)', ingredient.strip())
            if quantity_match:
                quantities.append(f'"{quantity_match.group(1)}"')
            else:
                quantities.append('""')
        
        if quantities:
            return f"c({', '.join(quantities)})"
        return ""
    
    def process_single_recipe(self, recipe_data: dict):
        title = recipe_data.get('title', 'Unknown Recipe')
        raw_ingredients = self.clean_ingredients(recipe_data.get('ingredients', []))
        
        if not raw_ingredients:
            print(f"Warning: No valid ingredients found for recipe '{title}', skipping...")
            return None
        
        clean_ingredient_names = self.extract_ingredient_names_only(raw_ingredients)
        if not clean_ingredient_names:
            print(f"Warning: No clean ingredient names extracted for recipe '{title}', skipping...")
            return None
        
        recipe_id = self.generate_recipe_id(len(self.processed_recipes))
        embedding = self.recipe_embedding.get_embedding(clean_ingredient_names)
        ingredients_text = ", ".join(clean_ingredient_names)
        
        prep_time_numeric = self.extract_numeric_value(recipe_data.get('prep_time'))
        cook_time_numeric = self.extract_numeric_value(recipe_data.get('cook_time'))
        
        random_calories = self.generate_random_calories()
        
        prep_time_iso = self.convert_to_iso_duration(prep_time_numeric)
        total_time_iso = self.calculate_total_time_iso(prep_time_numeric, cook_time_numeric)
        images_formatted = self.format_images_c_notation(recipe_data.get('image_url'))
        ingredient_quantities_formatted = self.extract_ingredient_quantities(raw_ingredients)
        
        processed_recipe = {
            "type": "recipe",
            "recipe_id": recipe_id,
            "recipe_name": title,
            "ingredients": clean_ingredient_names,
            "ingredients_text": ingredients_text,
            "embedding": embedding,
            "embedding_model": self.recipe_embedding.model_name,
            "embedding_dim": self.recipe_embedding.embedding_dim,
            "prep_time": prep_time_iso,
            "total_time": total_time_iso,
            "images": images_formatted,
            "recipe_category": recipe_data.get('category', ''),
            "ingredient_quantities": ingredient_quantities_formatted,
            "aggregated_rating": None,
            "calories": random_calories,
            "created_at": datetime.now().isoformat()
        }
        
        return processed_recipe
    
    def process_all_recipes(self, json_file_path: str):
        scraped_data = self.load_scraped_data(json_file_path)
        
        self.processed_recipes = []
        
        for recipe_data in scraped_data:
            processed = self.process_single_recipe(recipe_data)
            if processed:
                self.processed_recipes.append(processed)
        
        print(f"Successfully processed {len(self.processed_recipes)} recipes out of {len(scraped_data)} total")
        return self.processed_recipes
    
    def save_processed_data(self, output_file_path: str):
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.processed_recipes, f, indent=2, ensure_ascii=False)
        print(f"Processed recipes saved to {output_file_path}")
    
    def get_couchbase_documents(self):
        documents = {}
        for recipe in self.processed_recipes:
            recipe_id = recipe['recipe_id']
            documents[recipe_id] = recipe
        return documents
    
    def validate_processed_data(self):
        valid_count = 0
        for recipe in self.processed_recipes:
            if (recipe.get('recipe_id') and 
                recipe.get('recipe_name') and 
                recipe.get('ingredients') and 
                recipe.get('embedding') and
                len(recipe.get('embedding', [])) == self.recipe_embedding.embedding_dim):
                valid_count += 1
            else:
                print(f"Invalid recipe: {recipe.get('recipe_name', 'Unknown')}")
        
        print(f"Validation: {valid_count}/{len(self.processed_recipes)} recipes are valid")
        return valid_count == len(self.processed_recipes)
    
    def init_couchbase_connection(self):
        try:
            self.data_manager = DataManager()
            print("Successfully connected to Couchbase")
            return True
        except Exception as e:
            print(f"Failed to connect to Couchbase: {e}")
            return False
    
    def store_recipes_in_couchbase(self):
        if not self.data_manager:
            if not self.init_couchbase_connection():
                return False
        
        stored_count = 0
        failed_count = 0
        
        for recipe in self.processed_recipes:
            try:
                recipe_id = recipe['recipe_id']
                result = self.data_manager.insert(recipe_id, recipe)
                if result:
                    stored_count += 1
                    print(f"Stored recipe: {recipe['recipe_name']}")
                else:
                    print(f"Recipe already exists: {recipe['recipe_name']}")
            except Exception as e:
                failed_count += 1
                print(f"Failed to store recipe {recipe['recipe_name']}: {e}")
        
        print(f"Storage complete: {stored_count} new recipes stored, {failed_count} failed")
        return stored_count, failed_count

def main():
    processor = RecipeProcessing()
    
    recipes = processor.process_all_recipes('./dataset/pinch_of_yum_recipes.json')
    
    if processor.validate_processed_data():
        print("\nAll recipes are valid, proceeding with storage...")
        
        processor.save_processed_data('./dataset/processed_pinch_of_yum_recipes.json')
        
        stored_count, failed_count = processor.store_recipes_in_couchbase()
        
        if recipes:
            print("\nSample processed recipe:")
            sample = recipes[0]
            print(f"ID: {sample['recipe_id']}")
            print(f"Name: {sample['recipe_name']}")
            print(f"Ingredients: {len(sample['ingredients'])} items")
            print(f"Embedding dim: {len(sample['embedding'])}")
            print(f"Category: {sample['recipe_category']}")
            print(f"Calories: {sample['calories']}")
            print(f"Total time: {sample['total_time']}")
    else:
        print("Some recipes failed validation, not storing to Couchbase")

if __name__ == "__main__":
    main()