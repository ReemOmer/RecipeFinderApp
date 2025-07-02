import nest_asyncio
nest_asyncio.apply()
import requests
import pandas as pd
from DataManager import DataManager
from RecipeEmbedding import RecipeEmbedding

df = pd.read_csv(r'./dataset/recipes.csv')
df = df[['RecipeId', 'Name', 'PrepTime', 'TotalTime', 'Images', 'RecipeCategory', \
         'RecipeIngredientQuantities', 'RecipeIngredientParts', 'AggregatedRating', 'Calories']]

df.dropna(inplace=True)
# df = df[:10]

def combine_ingredients(ingredients_str):
    if isinstance(ingredients_str, str):
        ingredients_list = ingredients_str[3:-2].split('", "')
        return ', '.join(ingredients_list)
    else:
        return ""

def clean_ingredients_column(df, column_name):
    df[column_name] = df[column_name].apply(combine_ingredients)
    
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
            response = requests.post("http://host.docker.internal:11434/api/generate", json=payload)
            response.raise_for_status()
            result = response.json().get('response', '').strip()
            ingredients = [ing.strip().title() for ing in result.split(',') if ing.strip()]
            return ingredients if ingredients else []
        except Exception as e:
            print(f'Ollama request failed: {e}')
            return []
    
    df[column_name] = df[column_name].apply(clean_single)
    return df

df = clean_ingredients_column(df, 'RecipeIngredientParts')
# df.to_csv(r'./dataset/recipes_cleaned.csv', index=False)

recipe_embedding = RecipeEmbedding(model_name='all-MiniLM-L6-v2')
data_manager = DataManager()

for index, row in df.iterrows():
    recipe_id = str(row['RecipeId'])
    recipe_name = str(row['Name'])
    ingredients = row['RecipeIngredientParts']
    
    additional_fields = {
        'prep_time': str(row['PrepTime']) if pd.notna(row['PrepTime']) else None,
        'total_time': str(row['TotalTime']) if pd.notna(row['TotalTime']) else None,
        'images': str(row['Images']) if pd.notna(row['Images']) else None,
        'recipe_category': str(row['RecipeCategory']) if pd.notna(row['RecipeCategory']) else None,
        'ingredient_quantities': str(row['RecipeIngredientQuantities']) if pd.notna(row['RecipeIngredientQuantities']) else None,
        'aggregated_rating': float(row['AggregatedRating']) if pd.notna(row['AggregatedRating']) else None,
        'calories': float(row['Calories']) if pd.notna(row['Calories']) else None,
        'created_at': pd.Timestamp.now().isoformat(),
    }
    
    couchbase_document = recipe_embedding.prepare_for_couchbase(
        recipe_id=recipe_id,
        ingredient_list=ingredients,
        recipe_name=recipe_name,
        additional_fields=additional_fields
    )
    
    document_key = f"recipe::{recipe_id}"
    data_manager.insert(document_key, couchbase_document)
