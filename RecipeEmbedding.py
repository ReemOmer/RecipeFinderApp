import numpy as np
from sentence_transformers import SentenceTransformer
import ast

class RecipeEmbedding:

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

    def _parse_ingredients(self, ingredient_list):
        if isinstance(ingredient_list, str):
            ingredient_list = ast.literal_eval(ingredient_list) if ingredient_list.startswith('[') else [ing.strip() for ing in ingredient_list.split(',')]
        return ingredient_list if isinstance(ingredient_list, list) else [ingredient_list]

    def _clean_ingredients(self, ingredients):
        return [ingredient.strip().lower() for ingredient in ingredients if ingredient.strip()]

    def _ingredients_to_text(self, ingredients):
        return ", ".join(ingredients)

    def get_embedding(self, ingredient_list):
        ingredients = self._parse_ingredients(ingredient_list)
        cleaned = self._clean_ingredients(ingredients)
        text = self._ingredients_to_text(cleaned)
        embedding = self.model.encode(text)
        return embedding.tolist()

    def calculate_similarity(self, embedding1, embedding2):
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        dot_product = np.dot(vec1, vec2)
        norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        return float(dot_product / norm_product) if norm_product != 0 else 0.0

    def find_similar_recipes(self, user_ingredients, recipe_embeddings, recipe_data, top_k, min_similarity):
        user_embedding = self.get_embedding(user_ingredients)
        similarities = []
        for i, recipe_embedding in enumerate(recipe_embeddings):
            sim = self.calculate_similarity(user_embedding, recipe_embedding)
            if sim >= min_similarity:
                result = recipe_data[i].copy()
                result['similarity_score'] = sim
                result['rank'] = i
                similarities.append(result)
        similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
        return similarities[:top_k]

    def prepare_for_couchbase(self, recipe_id, ingredient_list, recipe_name, additional_fields):
        ingredients = self._parse_ingredients(ingredient_list)
        embedding = self.get_embedding(ingredient_list)
        document = {
            "type": "recipe",
            "recipe_id": recipe_id,
            "recipe_name": recipe_name,
            "ingredients": ingredients,
            "ingredients_text": self._ingredients_to_text(self._clean_ingredients(ingredients)),
            "embedding": embedding,
            "embedding_model": self.model_name,
            "embedding_dim": self.embedding_dim
        }
        if additional_fields:
            document.update(additional_fields)
        return document