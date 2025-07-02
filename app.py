import os
import re
os.environ["STREAMLIT_WATCHER_TYPE"] = "none"
os.environ["STREAMLIT_SERVER_RUN_ON_SAVE"] = "false"
from SimilaritySearch import SimilaritySearch
import streamlit as st


def extract_first_image_url(images_string):
    """
    Extract the first image URL from a string in the format:
    c("https://url1.jpg", "https://url2.jpg")
    """
    if not images_string or not isinstance(images_string, str):
        return None
        
    # Use regex to extract URLs from the string
    # This pattern specifically looks for URLs inside quotes
    urls = re.findall(r'"(https?://[^"]+)"', images_string)
    
    if urls and len(urls) > 0:
        return urls[0]
    return None

st.title("🍳 Recipe Similarity Finder")
st.write("Find recipes similar to your available ingredients!")

with st.form("recipe_search_form"):
    user_ingredients = st.text_input(
        "Enter your ingredients separated by comma:",
        placeholder="e.g., chicken, tomato, onion, garlic")

    col1, col2 = st.columns(2)
    with col1:
        top_k = st.slider("Number of recipes to show:", min_value=1, max_value=20, value=5)
    with col2:
        min_similarity = st.slider("Minimum similarity:", min_value=0.0, max_value=1.0, value=0.1, step=0.1)

    submitted = st.form_submit_button("🔍 Find Similar Recipes")

if submitted:
    if user_ingredients.strip():
        st.info("Searching for similar recipes...")

        similarity_search = SimilaritySearch(user_ingredients)            
        
        if similarity_search:
            try:
                user_embedding = similarity_search.get_user_embedding()
                st.success("Successfully processed your ingredients!")
            except Exception as e:
                st.error(f"Error processing ingredients: {str(e)}")
                st.stop()
            
            try:
                
                similar_recipes = similarity_search.find_similar_recipes(top_k=top_k, threshold=min_similarity)
                
                if similar_recipes and len(similar_recipes) > 0:
                    st.success(f"Found {len(similar_recipes)} potential recipes!")
                    
                    for i, item in enumerate(similar_recipes, 1):
                        recipe = item.get('recipe', item)  # Fallback to item itself if 'recipe' key doesn't exist
                        similarity_score = item.get('similarity_score', 0.0)
                        
                        recipe_name = "Unknown Recipe"
                        if isinstance(recipe, dict):
                            recipe_name = recipe.get('recipe_name', 
                                         recipe.get('name', 
                                         recipe.get('title', f"Recipe {i}")))
                        
                        with st.expander(f"{i}. {recipe_name} (Similarity: {similarity_score:.3f})"):
                            if isinstance(recipe, dict) and 'images' in recipe:
                                image_url = extract_first_image_url(recipe['images'])
                                if image_url:
                                    try:
                                        st.image(image_url, use_container_width=True)
                                    except Exception as img_err:
                                        st.error(f"Error displaying image: {img_err}")
                                        st.write(f"Image URL: {image_url}")
                            
                            # Only proceed with column layout if recipe is a dictionary
                            if isinstance(recipe, dict):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.write(f"**Category:** {recipe.get('recipe_category', recipe.get('category', 'Unknown'))}")
                                    
                                    if 'cuisine' in recipe:
                                        st.write(f"**Cuisine:** {recipe['cuisine']}")
                                    if 'cooking_time' in recipe:
                                        st.write(f"**Cooking Time:** {recipe['cooking_time']}")
                                    if 'difficulty' in recipe:
                                        st.write(f"**Difficulty:** {recipe['difficulty']}")
                                    if 'servings' in recipe:
                                        st.write(f"**Servings:** {recipe['servings']}")
                                    if 'calories' in recipe:
                                        st.write(f"**Calories:** {recipe['calories']}")

                                with col2:
                                    ingredients = recipe.get('ingredients', recipe.get('ingredient_list', []))
                                    
                                    st.write("**Ingredients:**")
                                    if ingredients and isinstance(ingredients, list):
                                        for ingredient in ingredients[:10]:
                                            st.write(f"• {ingredient}")
                                        if len(ingredients) > 10:
                                            st.write(f"... and {len(ingredients) - 10} more")
                                    else:
                                        st.write("No ingredients listed")
                                
                                if 'instructions' in recipe or 'steps' in recipe:
                                    st.write("**Instructions:**")
                                    instructions = recipe.get('instructions', recipe.get('steps', []))
                                    
                                    if isinstance(instructions, list):
                                        for j, step in enumerate(instructions[:5], 1):
                                            st.write(f"{j}. {step}")
                                        if len(instructions) > 5:
                                            st.write(f"... and {len(instructions) - 5} more steps")
                                    else:
                                        st.write(instructions)
                                
                                if 'recipe_id' in recipe:
                                    st.caption(f"Recipe ID: {recipe['recipe_id']}")
                else:
                    st.warning("No matching recipes found in the database.")

            except Exception as e:
                st.error(f"Error retrieving recipes: {str(e)}")
                import traceback
                st.error(traceback.format_exc())
    else:
        st.warning("Please enter some ingredients to search for similar recipes.")

st.sidebar.markdown("### How to use:")
st.sidebar.markdown("1. Enter ingredients you have at home")
st.sidebar.markdown("2. Adjust the number of results and similarity threshold")
st.sidebar.markdown("3. Click 'Find Similar Recipes' to get recommendations")
st.sidebar.markdown("4. Explore the recipe details in the expandable sections")
