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
        self.recipe_embedding = RecipeEmbedding(model_name='all-MiniLM-L6-v2')
        self.data_manager = DataManager()

    def get_user_embedding(self):
        try:
            user_embedding = self.recipe_embedding.get_embedding(self.user_ingredients)
            self.user_embedding = user_embedding
            return self.user_embedding
        except Exception as e:
            print(f"Failed to vectorize ingredients: {str(e)}")
            return None
            
    def get_doc_from_db(self):
        try:
            return self.data_manager.read_all()
        except Exception as e:
            print(f"Error retrieving documents: {str(e)}")
    
    def find_similar_recipes(self, top_k=3, threshold=0.1):
        try:
            
            all_recipes = self.get_doc_from_db()
            
            if not all_recipes:
                print(self.user_embedding)
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
