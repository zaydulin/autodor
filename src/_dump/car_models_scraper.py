import requests
import json

def fetch_all_makes():
    url = 'https://vpic.nhtsa.dot.gov/api/vehicles/getallmakes?format=json'
    response = requests.get(url)
    return response.json()['Results'] if response.status_code == 200 else []

def fetch_models_for_make(make):
    url = f'https://vpic.nhtsa.dot.gov/api/vehicles/getmodelsformake/{make}?format=json'
    response = requests.get(url)
    return response.json()['Results'] if response.status_code == 200 else []

def save_to_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def main():
    makes = fetch_all_makes()  # Получаем все марки автомобилей
    all_data = []

    # Получаем модели для каждой марки и сохраняем данные
    for make in makes:
        make_name = make['Make_Name']
        print(f"Загружаем модели для марки {make_name}...")

        models = fetch_models_for_make(make_name)
        all_data.append({'make': make_name, 'models': models})

    # Сохраняем данные в JSON файл
    save_to_json(all_data, 'car_brands_and_models.json')

if __name__ == '__main__':
    main()
