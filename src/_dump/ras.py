import os
import django
import sys
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "_project.settings")
django.setup()

from moderation.models import Advert, CarBrand, CarModel


def update_adverts_with_car_brand_and_model():
    # Проходим по всем объявлениям
    for advert in Advert.objects.all():
        # Убираем специальные символы (например, * и другие)
        clean_name = re.sub(r'[^\w\s-]', '', advert.name.strip())  # Удаляем все, что не является буквой, цифрой, пробелом или дефисом

        # Разделяем строку на два слова: марка и модель
        name_parts = clean_name.split(" ", 2)  # Разделяем только по первому пробелу (не больше двух частей)

        if len(name_parts) >= 2:  # Убедимся, что разделено хотя бы на два слова
            car_brand_name = name_parts[0]  # Первое слово - это марка
            car_model_name = name_parts[1]  # Второе слово - это модель

            print(f"Обрабатываем: Марка: {car_brand_name}, Модель: {car_model_name}")  # Отладка

            # Получаем или создаем марку
            car_brand, brand_created = CarBrand.objects.get_or_create(name=car_brand_name)

            if brand_created:
                print(f"Создана новая марка: {car_brand_name}")
            else:
                print(f"Марка {car_brand_name} уже существует")

            # Получаем или создаем модель для этой марки
            car_model, model_created = CarModel.objects.get_or_create(name=car_model_name, brand=car_brand)

            if model_created:
                print(f"Создана новая модель: {car_model_name}")
            else:
                print(f"Модель {car_model_name} уже существует")

            # Теперь обновляем объект Advert и связываем с моделью
            advert.car_brand = car_brand  # Связываем с маркой
            advert.car_model = car_model  # Связываем с моделью

            advert.save()  # Сохраняем изменения

            print(f"Обновлено: {advert.name} -> Марка: {car_brand_name}, Модель: {car_model_name}")
        else:
            print(f"Не удалось разделить название на марку и модель для: {advert.name}")

# Запуск функции обновления
update_adverts_with_car_brand_and_model()
