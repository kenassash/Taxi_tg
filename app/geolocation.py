#!/usr/bin/env python
# coding: utf-8

import aiohttp
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()


async def coords_to_address(x, y):
    geocoder_request = f"https://geocode-maps.yandex.ru/1.x/?apikey={os.getenv('YANDEX')}&geocode={x},{y}&format=json"

    async with aiohttp.ClientSession() as session:
        async with session.get(geocoder_request) as response:
            if response.status == 200:
                json_response = await response.json()

                toponym = json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
                toponym_address = toponym["metaDataProperty"]["GeocoderMetaData"]["text"]
                trimmed_string = ", ".join(toponym_address.split(", ")[2:])


                return trimmed_string
            else:
                print("Ошибка выполнения запроса:")
                print(geocoder_request)
                print("Http статус:", response.status, "(", response.reason, ")")


async def addess_to_coords(address):
    geocoder_request = f"https://geocode-maps.yandex.ru/1.x/?apikey={os.getenv('YANDEX')}&geocode={os.getenv('LOCATION')}+{address}&format=json"

    async with aiohttp.ClientSession() as session:
        async with session.get(geocoder_request) as response:
            if response.status == 200:
                json_response = await response.json()

                toponym = json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
                toponym_address = toponym["metaDataProperty"]["GeocoderMetaData"]["text"]
                toponym_coodrinates = toponym["Point"]["pos"]

                longitude_end, latitude_end = [float(x) for x in toponym_coodrinates.split()] # убирает запятую между координатами
                trimmed_string = ", ".join(toponym_address.split(", ")[2:])  # Убирает Россиия и Амурская область

                return longitude_end, latitude_end, trimmed_string
            else:
                print("Ошибка выполнения запроса:")
                print(geocoder_request)
                print("Http статус:", response.status, "(", response.reason, ")")


