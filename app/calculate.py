import math
import asyncio
from haversine import haversine, Unit
x1 = (50.348587, 129.132247)
x2 = (50.381621, 129.095030)
print(haversine(x1, x2))



async def main():
    async def length_way(longitude_start, latitude_start, longitude_end, latitude_end):
        x1, y1 = longitude_start, latitude_start
        x2, y2 = longitude_end, latitude_end

        y = math.radians((y1 + y2) / 2)
        x = math.cos(y)
        n = abs(x1 - x2) * 111000 * x
        n2 = abs(y1 - y2) * 111000
        length_way = round(math.sqrt(n * n + n2 * n2))
        return length_way / 1000

    result = await length_way(50.348587, 129.132247, 50.381621, 129.095030)
    print(result)

asyncio.run(main())
