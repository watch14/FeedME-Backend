from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.errors import InvalidId

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['TheMealDB']
meals_collection = db['meal']

app = Flask(__name__)
CORS(app) 


## Fetch Ingredients ##
## TEST ## GET http://127.0.0.1:9000/ingredients
@app.route('/ingredients', methods=['GET'])
def get_ingredients():
    url = "https://www.themealdb.com/api/json/v1/1/list.php?i=list"
    response = requests.get(url)
    data = response.json()

    ingredients = [{"name": ingredient['strIngredient'], "image": f"https://www.themealdb.com/images/ingredients/{ingredient['strIngredient']}-Small.png"} for ingredient in data['meals']]

    # ingredients = [{"name": ingredient['strIngredient'], "image": f"https://www.themealdb.com/images/ingredients/{ingredient['strIngredient']}-Small.png"} for ingredient in data['meals']]

    return jsonify(ingredients)


## Search ##
## TEST ## GET http://127.0.0.1:9000/search/Arrabiata
@app.route('/search/<name>')
def search_meal(name):
    url = f"https://www.themealdb.com/api/json/v1/1/search.php?s={name}"
    response = requests.get(url)
    data = response.json()

    # Check if the meal exists
    if data["meals"] is None:
        return jsonify({"error": "Meal not found"}), 404

    meal_data = data["meals"][0]
    ingredients = []

    # Extracting ingredients and their measures
    for i in range(1, 21):
        ingredient = meal_data.get(f'strIngredient{i}')
        measure = meal_data.get(f'strMeasure{i}')
        if ingredient and ingredient.strip() and measure and measure.strip():
            ingredients.append(f"{ingredient}: {measure}")

    # Constructing the response
    result = {
        "strMeal": meal_data["strMeal"],
        "strCategory": meal_data["strCategory"],
        "strArea": meal_data["strArea"],
        "strInstructions": meal_data["strInstructions"],
        "strMealThumb": meal_data["strMealThumb"],
        "strYoutube": meal_data["strYoutube"],
        "ingredients": ingredients
    }

    return jsonify(result)

## search with ingredient ##
## TEST ## POST http://127.0.0.1:9000/get_food_with_ingredients
## body : json => {"ingredients": ["Chicken", "Salmon"]}
@app.route('/get_food_with_ingredients', methods=['POST'])
def get_food_with_ingredients():
    data = request.json
    ingredients = data.get('ingredients', [])  # List of ingredients

    meal_ids_with_ingredients = set()

    # Fetch meals for each ingredient and find common meals
    for ingredient in ingredients:
        url = f"https://www.themealdb.com/api/json/v1/1/filter.php?i={ingredient}"
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
            meals_data = response.json()
        except requests.RequestException as e:
            return jsonify({'error': str(e)}), 500  # Return an error response if request fails

        if meals_data.get("meals"):
            meal_ids_with_ingredient = {meal["idMeal"] for meal in meals_data["meals"]}
            if not meal_ids_with_ingredients:
                meal_ids_with_ingredients = meal_ids_with_ingredient
            else:
                meal_ids_with_ingredients.intersection_update(meal_ids_with_ingredient)

    # Fetch detailed info for common meals
    meal_details = []
    for meal_id in meal_ids_with_ingredients:
        detail_url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal_id}"
        try:
            response = requests.get(detail_url)
            response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
            detail_data = response.json()
        except requests.RequestException as e:
            return jsonify({'error': str(e)}), 500  # Return an error response if request fails

        if detail_data.get("meals"):
            meal_detail = detail_data["meals"][0]
            ingredients = []
            for i in range(1, 21):
                ingredient = meal_detail.get(f'strIngredient{i}')
                measure = meal_detail.get(f'strMeasure{i}')
                if ingredient and ingredient.strip() and measure and measure.strip():
                    ingredients.append(f"{ingredient}: {measure}")

            meal_details.append({
                "idMeal": meal_id,
                "strMeal": meal_detail["strMeal"],
                "strCategory": meal_detail["strCategory"],
                "strArea": meal_detail["strArea"],
                "strInstructions": meal_detail["strInstructions"],
                "strMealThumb": meal_detail["strMealThumb"],
                "strYoutube": meal_detail["strYoutube"],
                "ingredients": ingredients
            })

    return jsonify(meal_details)





def extract_youtube_id(youtube_url):
    # Assuming the YouTube URL format is https://www.youtube.com/watch?v=VIDEO_ID
    return youtube_url.split("=")[-1]

## Get meal by id ##
## TEST ## GET http://127.0.0.1:9000/get_meal_by_id/52928
@app.route('/get_meal_by_id/<meal_id>')
def get_meal_by_id(meal_id):
    url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal_id}"
    response = requests.get(url)
    data = response.json()

    meal_data = data["meals"][0]
    ingredients = []

    # Extracting ingredients and their measures
    for i in range(1, 21):
        ingredient = meal_data.get(f'strIngredient{i}')
        measure = meal_data.get(f'strMeasure{i}')
        if ingredient and ingredient.strip() and measure and measure.strip():
            ingredients.append(f"{ingredient}: {measure}")

    # Constructing the response
    result = {
        "strMeal": meal_data["strMeal"],
        "strCategory": meal_data["strCategory"],
        "strArea": meal_data["strArea"],
        "strInstructions": meal_data["strInstructions"],
        "strMealThumb": meal_data["strMealThumb"],
        "strYoutube": meal_data["strYoutube"],
        "youtube_id": extract_youtube_id(meal_data["strYoutube"]),  # Extract YouTube ID
        "ingredients": ingredients
    }

    return jsonify(result) 



## get meal by area ##
## TEST ## GET http://127.0.0.1:9000/get_meals_by_area/canadian
@app.route('/get_meals_by_area/<area>')
def get_meals_by_area(area):
    url = f"https://www.themealdb.com/api/json/v1/1/filter.php?a={area}"
    response = requests.get(url)
    meals_data = response.json()

    if meals_data["meals"]:
        return jsonify(meals_data["meals"])
    else:
        return jsonify({"error": "No meals found for this area"}), 404


## get 10 random meals ##
## TEST ## GET : http://127.0.0.1:9000/random
@app.route('/random', methods=['GET'])
def get_random_meals():
    random_meals = []
    count = 0

    while count < 8:
        url = "https://www.themealdb.com/api/json/v1/1/random.php"
        response = requests.get(url)
        data = response.json()

        if data["meals"]:
            meal_data = data["meals"][0]
            meal_id = meal_data["idMeal"]
            ingredients = []

            for i in range(1, 21):
                ingredient = meal_data.get(f'strIngredient{i}')
                measure = meal_data.get(f'strMeasure{i}')
                if ingredient and ingredient.strip() and measure and measure.strip():
                    ingredients.append({"ingredient": ingredient, "measure": measure})

            document = {
                "meal_id": meal_id,
                "strMeal": meal_data["strMeal"],
                "strCategory": meal_data["strCategory"],
                "strArea": meal_data["strArea"],
                "strInstructions": meal_data["strInstructions"],
                "strMealThumb": meal_data["strMealThumb"],
                "strYoutube": meal_data["strYoutube"],
                "ingredients": ingredients
            }

            random_meals.append(document)
            count += 1

    return jsonify(random_meals)




## save meal ##
## TEST ## POST : http://127.0.0.1:9000/save/52928        (52965, 52928, 52923)
@app.route('/save/<meal_id>', methods=['POST'])
def save_meal(meal_id):
    # Check if the meal already exists in the database
    if meals_collection.find_one({"meal_id": meal_id}):
        return jsonify({"error": "Meal already exists"}), 409

    url = f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={meal_id}"
    response = requests.get(url)
    data = response.json()

    if data["meals"] is None:
        return jsonify({"error": "Meal not found"}), 404

    meal_data = data["meals"][0]
    ingredients = []

    for i in range(1, 21):
        ingredient = meal_data.get(f'strIngredient{i}')
        measure = meal_data.get(f'strMeasure{i}')
        if ingredient and ingredient.strip() and measure and measure.strip():
            ingredients.append({"ingredient": ingredient, "measure": measure})

    # Preparing the document to be saved, including the meal_id
    document = {
        "meal_id": meal_id,  # Including the meal_id from the request
        "strMeal": meal_data["strMeal"],
        "strCategory": meal_data["strCategory"],
        "strArea": meal_data["strArea"],
        "strInstructions": meal_data["strInstructions"],
        "strMealThumb": meal_data["strMealThumb"],
        "strYoutube": meal_data["strYoutube"],
        "ingredients": ingredients
    }

    # Inserting the document into the collection
    result = meals_collection.insert_one(document)
    return jsonify({"message": "Meal saved successfully", "document_id": str(result.inserted_id)})




## delete saved meal ##
## TEST ## DELETE : http://127.0.0.1:9000/delete/52928
@app.route('/delete/<meal_id>', methods=['DELETE'])
def delete_meal(meal_id):
    result = meals_collection.delete_one({"meal_id": meal_id})

    if result.deleted_count == 0:
        return jsonify({"error": "Meal not found"}), 404

    return jsonify({"message": "Meal deleted successfully"})


## get all saved meals ##
## TEST ## GET : http://127.0.0.1:9000/meals
@app.route('/meals', methods=['GET'])
def get_all_meals():
    meals_cursor = meals_collection.find({})
    meals_list = list(meals_cursor)
    
    # Convert ObjectId() to string since it's not JSON serializable
    for meal in meals_list:
        meal['_id'] = str(meal['_id'])
    
    return jsonify(meals_list)



if __name__ == '__main__':
    app.run(debug=True, port=9000)
