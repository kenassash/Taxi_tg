class Settings:
    distance_rate = 40  # Цена за километр
    time_rate = 10  # Цена за минуту

    fix_price = 30
    free_ride = 10

    @classmethod
    def set_distance_rate(cls, value):
        cls.distance_rate = value

    @classmethod
    def set_time_rate(cls, value):
        cls.time_rate = value

    @classmethod
    def set_fix_price(cls, value):
        cls.fix_price = value

    @classmethod
    def set_ffree_ride(cls, value):
        cls.free_ride = value
