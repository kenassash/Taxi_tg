import math
import asyncio

from app.change_price import Settings

# x1 = (50.348587, 129.132247)
# x2 = (50.381621, 129.095030)
# print(haversine(x1, x2))


async def length_way(longitude_start, latitude_start, longitude_end, latitude_end):
    x1, y1 = longitude_start, latitude_start
    x2, y2 = longitude_end, latitude_end

    y = math.radians((y1 + y2) / 2)
    x = math.cos(y)
    n = abs(x1 - x2) * 111000 * x
    n2 = abs(y1 - y2) * 111000
    length_way = round(math.sqrt(n * n + n2 * n2))
    time_way = round(length_way / (20 * 1000) * 60) # Время в мин
    distance = length_way / 1000 # Расстояние в км

    price = round(distance * Settings.distance_rate + Settings.time_rate * time_way) # Цена
    return distance, time_way, price

#     result = await length_way(50.348587, 129.132247, 50.381621, 129.095030)
#     print(result)
#
# asyncio.run(main())
