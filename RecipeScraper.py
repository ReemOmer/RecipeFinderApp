import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin

class RecipeScraper:
    def __init__(self):
        """Initialize scraper with base URL and session headers"""

        self.base_url = "https://pinchofyum.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_recipe_links(self):
        """Extract recipe links from the main recipes page"""

        page_url = f"{self.base_url}/recipes/all"
        response = self.session.get(page_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        recipe_links = []
        recipe_elements = (
            soup.find_all('article') +
            soup.find_all('div', class_=lambda x: x and 'recipe' in x.lower()) +
            soup.find_all('div', class_=lambda x: x and 'post' in x.lower())
        )
        
        for element in recipe_elements:
            link = element.find('a', href=True)
            if link:
                href = link.get('href')
                if href:
                    if href.startswith('/'):
                        recipe_url = urljoin(self.base_url, href)
                    elif href.startswith('http'):
                        recipe_url = href
                    else:
                        continue
                    
                    if recipe_url not in recipe_links and self.base_url in recipe_url:
                        recipe_links.append(recipe_url)
        
        if not recipe_links:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href')
                if href and href.startswith('/') and href != '/':
                    skip_patterns = ['/about', '/contact', '/recipes/all', '/category', '/tag', '/search', '/page', '/#']
                    if not any(skip in href for skip in skip_patterns):
                        recipe_url = urljoin(self.base_url, href)
                        if recipe_url not in recipe_links and len(href.split('/')) >= 2:
                            recipe_links.append(recipe_url)
        
        return recipe_links[:20]
    
    def extract_title(self, soup):
        """Extract recipe title from soup object"""

        title_element = soup.find('h1', class_='entry-title') or soup.find('h1')
        return title_element.get_text(strip=True) if title_element else "No title found"
    
    def extract_ingredients(self, soup):
        """Extract ingredients list from recipe page"""

        def is_valid_ingredient(text):
            """Check if text looks like an actual ingredient"""
            if not text or len(text.strip()) < 3:
                return False
            
            # Filter out common metadata patterns
            metadata_patterns = [
                'author:', 'total time:', 'prep time:', 'cook time:', 'yield:', 'serves:', 'servings:',
                'calories:', 'difficulty:', 'course:', 'cuisine:', 'keyword:', 'recipe', 'print',
                'save', 'rate this recipe', 'pin recipe', 'share', 'notes:', 'instructions:',
                'method:', 'equipment:', 'storage:', 'tips:', 'nutrition:'
            ]
            
            text_lower = text.lower().strip()
            if any(pattern in text_lower for pattern in metadata_patterns):
                return False
                
            # Filter out very short or very long text
            if len(text) > 200 or len(text) < 3:
                return False
                
            return True

        ingredients = []
        
        # Method 1: Try the existing Tasty Recipes structure
        tasty_div = soup.find('div', {'data-tasty-recipes-customization': 'body-color.color'})
        if tasty_div:
            ingredient_items = tasty_div.find_all('li', {'data-tr-ingredient-checkbox': ''})
            for item in ingredient_items:
                ingredient_text = ""
                for element in item.contents:
                    if hasattr(element, 'get') and element.get('class') and 'tr-ingredient-checkbox-container' in element.get('class', []):
                        continue
                    if hasattr(element, 'get_text'):
                        ingredient_text += element.get_text(strip=True) + " "
                    elif isinstance(element, str):
                        ingredient_text += element.strip() + " "
                
                ingredient_text = ingredient_text.strip()
                if is_valid_ingredient(ingredient_text):
                    ingredients.append(ingredient_text)
        
        # Method 2: Fallback to generic tasty-recipes ingredients
        if not ingredients:
            ingredient_lists = soup.find_all('ul', class_=lambda x: x and 'tasty-recipes-ingredients' in x)
            for ul in ingredient_lists:
                for li in ul.find_all('li'):
                    ingredient_text = li.get_text(strip=True)
                    if is_valid_ingredient(ingredient_text):
                        ingredients.append(ingredient_text)
        
        # Method 3: Look for any list with "ingredient" in class name
        if not ingredients:
            ingredient_containers = soup.find_all(['ul', 'ol'], class_=lambda x: x and 'ingredient' in x.lower())
            for container in ingredient_containers:
                for li in container.find_all('li'):
                    ingredient_text = li.get_text(strip=True)
                    if is_valid_ingredient(ingredient_text):
                        ingredients.append(ingredient_text)
        
        # Method 4: Look for structured data (JSON-LD)
        if not ingredients:
            json_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_scripts:
                try:
                    import json as json_module
                    data = json_module.loads(script.string)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get('@type') == 'Recipe':
                                recipe_ingredients = item.get('recipeIngredient', [])
                                for ing in recipe_ingredients:
                                    if is_valid_ingredient(ing):
                                        ingredients.append(ing)
                    elif isinstance(data, dict) and data.get('@type') == 'Recipe':
                        recipe_ingredients = data.get('recipeIngredient', [])
                        for ing in recipe_ingredients:
                            if is_valid_ingredient(ing):
                                ingredients.append(ing)
                except:
                    continue
        
        # Method 5: Generic list search near recipe content (last resort)
        if not ingredients:
            recipe_containers = soup.find_all(['div', 'section'], class_=lambda x: x and ('recipe' in x.lower()))
            for container in recipe_containers:
                lists = container.find_all(['ul', 'ol'])
                for ul in lists:
                    temp_ingredients = []
                    for li in ul.find_all('li'):
                        ingredient_text = li.get_text(strip=True)
                        if is_valid_ingredient(ingredient_text):
                            temp_ingredients.append(ingredient_text)
                    
                    if len(temp_ingredients) >= 3:
                        ingredients.extend(temp_ingredients)
                        break
                if ingredients:
                    break
        
        return ingredients
    
    def extract_calories(self, soup):
        """Extract calories information from recipe page"""

        body = soup.find('body')
        if body:
            div1 = body.find('div')
            if div1:
                div2 = div1.find('div')
                if div2:
                    div3 = div2.find('div')
                    if div3:
                        header = div3.find('header')
                        if header:
                            divs = header.find_all('div')
                            if len(divs) >= 2:
                                target_div = divs[1]
                                span = target_div.find('span')
                                if span:
                                    calories_text = span.get_text(strip=True)
                                    calories_match = re.search(r'\d+', calories_text)
                                    if calories_match:
                                        return calories_match.group()
        
        calories_div = soup.find('div', class_='label-header-detail calories')
        if calories_div:
            calories_span = calories_div.find('span', class_='calories-detail-value font-bold')
            if calories_span:
                return calories_span.get_text(strip=True)
        
        calories_elem = soup.find('span', class_='calories-detail-value')
        if calories_elem and 'font-bold' in calories_elem.get('class', []):
            return calories_elem.get_text(strip=True)
        
        return None
    
    def extract_image_url(self, soup):
        """Extract main recipe image URL"""
        banner_container = soup.find(class_='tasty-pins-banner-container')
        if banner_container:
            img_elem = banner_container.find('img', src=True)
            if img_elem:
                src = img_elem.get('src')
                if src:
                    if src.startswith('//'):
                        return 'https:' + src
                    elif src.startswith('/'):
                        return urljoin(self.base_url, src)
                    else:
                        return src
        return None
    
    def extract_metadata(self, soup):
        """Extract prep time, cook time, and category metadata"""
        
        prep_time_elem = soup.find('span', class_='tasty-recipes-prep-time')
        cook_time_elem = soup.find('span', class_='tasty-recipes-cook-time')
        category_elem = soup.find('span', class_='tasty-recipes-category')
        
        return {
            'prep_time': prep_time_elem.get_text(strip=True) if prep_time_elem else None,
            'cook_time': cook_time_elem.get_text(strip=True) if cook_time_elem else None,
            'category': category_elem.get_text(strip=True) if category_elem else None
        }
    
    def scrape_recipe(self, recipe_url):
        """Scrape all data from a single recipe URL"""
        response = self.session.get(recipe_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        metadata = self.extract_metadata(soup)
        
        recipe_data = {
            'title': self.extract_title(soup),
            'ingredients': self.extract_ingredients(soup),
            'calories_per_serving': self.extract_calories(soup),
            'image_url': self.extract_image_url(soup),
            'prep_time': metadata['prep_time'],
            'cook_time': metadata['cook_time'],
            'category': metadata['category']
        }
        
        return recipe_data
    
    def scrape_multiple_recipes(self, num_recipes=2):
        """Scrape multiple recipes with rate limiting"""
        recipe_links = self.get_recipe_links()
        print(f"Found {len(recipe_links)} recipe links")
        recipes = []
        
        for i, link in enumerate(recipe_links[:num_recipes]):
            print(f"Scraping recipe {i+1}/{min(num_recipes, len(recipe_links))}: {link}")
            recipe_data = self.scrape_recipe(link)
            
            if recipe_data:
                recipes.append(recipe_data)
                print(f"Successfully scraped: {recipe_data['title']}")
            
            time.sleep(1)
        
        return recipes
    
    def save_recipes_to_json(self, recipes, filename="./dataset/pinch_of_yum_recipes.json"):
        """Save scraped recipes to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(recipes, f, indent=2, ensure_ascii=False)
        print(f"Recipes saved to {filename}")

def main():
    scraper = RecipeScraper()
    recipes = scraper.scrape_multiple_recipes(num_recipes=2)
    
    if recipes:
        print(f"\nSuccessfully scraped {len(recipes)} recipes:")
        for recipe in recipes:
            print(f"- {recipe['title']}")
            print(f"  Prep: {recipe.get('prep_time', 'N/A')}")
            print(f"  Cook: {recipe.get('cook_time', 'N/A')}")
            print(f"  Category: {recipe.get('category', 'N/A')}")
            print(f"  Ingredients: {len(recipe['ingredients'])}")
            print(f"  Calories: {recipe.get('calories_per_serving', 'N/A')}")
            print(f"  Image: {recipe.get('image_url', 'N/A')}")
            print()
        
        scraper.save_recipes_to_json(recipes)
    else:
        print("No recipes were scraped successfully")

if __name__ == "__main__":
    main()