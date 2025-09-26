import requests
import json


def get_all_car_brands():
    # Получаем список всех марок автомобилей
    url = "https://vpic.nhtsa.dot.gov/api/vehicles/getallmakes?format=json"
    response = requests.get(url)

    if response.status_code == 200:
        try:
            # Возвращаем список марок
            return response.json()['Results']
        except json.JSONDecodeError:
            print("Ошибка при декодировании JSON")
            return []
    else:
        print(f"Ошибка при получении марок: {response.status_code}")
        return []


def get_models_for_brand(brand):
    # Получаем модели для конкретной марки
    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/getmodelsformake/{brand}?format=json"
    response = requests.get(url)

    if response.status_code == 200:
        try:
            # Проверяем, если данные получены корректно
            return response.json()['Results']
        except json.JSONDecodeError:
            print(f"Ошибка при декодировании JSON для марки {brand}")
            return []
    else:
        print(f"Ошибка при получении моделей для {brand}: {response.status_code}")
        return []


def save_to_json(data, filename="car_brands_and_models_nhtsa.json"):
    # Записываем данные в JSON файл
    with open(filename, 'a', encoding='utf-8') as f:  # Используем 'a' для дозаписи в файл
        json.dump(data, f, ensure_ascii=False, indent=4)
        f.write("\n")  # Добавляем новую строку после записи каждого объекта


def main():
    car_brands = get_all_car_brands()

    if car_brands:
        # Создаем новый файл или открываем для дозаписи
        for brand in car_brands:
            brand_name = brand['Make_Name']
            print(f"Загружаем модели для марки {brand_name}...")

            models = get_models_for_brand(brand_name)

            if models:
                data = {brand_name: models}
                save_to_json(data)  # Записываем данные в файл сразу после запроса
            else:
                print(f"Нет данных о моделях для марки {brand_name}")

        print("Данные успешно сохранены в car_brands_and_models_nhtsa.json")
    else:
        print("Не удалось получить данные о марках автомобилей.")


if __name__ == "__main__":
    main()
