from RecipeEmbedding import RecipeEmbedding
from DataManager import DataManager
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import os
from dotenv import load_dotenv

class SimilaritySearch:

    def __init__(self, user_ingredients):
        self.user_ingredients = user_ingredients
        self.user_embedding = None
        self.recipe_embedding = None
        self.data_manager = None
        self.load_models()

    def load_models(self):
        try:
            self.recipe_embedding = RecipeEmbedding(model_name='all-MiniLM-L6-v2')
            self.data_manager = DataManager()
            return True
        except Exception as e:
            print(f"Error loading models: {str(e)}")
            return False

    def get_user_embedding(self):
        try:
            if self.recipe_embedding is None:
                self.load_models()
                
            user_embedding = self.recipe_embedding.get_embedding(self.user_ingredients)
            self.user_embedding = user_embedding
            return self.user_embedding
        except Exception as e:
            print(f"Failed to vectorize ingredients: {str(e)}")
            return None
            
    def get_doc_from_db(self):
        try:
            if self.data_manager is None:
                self.load_models()
                
            return self.data_manager.read_all()
        except Exception as e:
            print(f"Error retrieving documents: {str(e)}")
            return []
    
    def find_similar_recipes(self, top_k=3, threshold=0.5):
        try:
            if self.data_manager is None or self.recipe_embedding is None:
                if not self.load_models():
                    return []
            
            if self.user_embedding is None:
                self.user_embedding = self.get_user_embedding()
                if self.user_embedding is None:
                    print("Could not generate user embedding")
                    return []
            
            all_recipes = self.get_doc_from_db()
            
            if not all_recipes:
                print("No recipes found in the database")
                return []
            
            user_embedding_np = np.array(self.user_embedding).reshape(1, -1)
            
            similar_recipes = []
            for recipe in all_recipes:
                if 'embedding' not in recipe:
                    continue
                
                recipe_embedding = recipe['embedding']
                
                try:
                    recipe_embedding_np = np.array(recipe_embedding).reshape(1, -1)
                    
                    similarity = float(cosine_similarity(user_embedding_np, recipe_embedding_np)[0][0])
                    
                    if similarity >= threshold:
                        similar_recipes.append({
                            'recipe': recipe,
                            'similarity_score': similarity
                        })
                except Exception as e:
                    print(f"Error calculating similarity for recipe: {e}")
                    continue
            
            similar_recipes.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            return similar_recipes[:top_k]
            
        except Exception as e:
            print(f"Error finding similar recipes: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
