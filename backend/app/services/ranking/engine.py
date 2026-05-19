from datetime import datetime

CURRENT_YEAR = datetime.now().year


def score_car(car: dict, filters: dict) -> int:
    score = 0

    car_price = car.get("price")
    max_price = filters.get("max_price")
    min_price = filters.get("min_price")

    if max_price and car_price:
        if car_price <= max_price:
            score += 30
        elif car_price <= max_price * 1.08:
            score += 12  # just slightly over budget
        else:
            score -= 25  # clearly over budget

    if min_price and car_price and car_price < min_price:
        score -= 10

    wanted_trans = (filters.get("transmission") or "").lower()
    car_trans = (car.get("transmission") or "").lower()
    if wanted_trans and car_trans:
        if wanted_trans in car_trans or car_trans in wanted_trans:
            score += 20
        else:
            score -= 15

    wanted_city = (filters.get("city") or "").lower()
    car_city = (car.get("city") or "").lower()
    if wanted_city and car_city:
        if wanted_city in car_city or car_city in wanted_city:
            score += 20
        else:
            score -= 5

    car_mileage = car.get("mileage")
    max_mileage = filters.get("max_mileage")
    if car_mileage is not None:
        if max_mileage and car_mileage > max_mileage:
            score -= 10
        if car_mileage < 30_000:
            score += 15
        elif car_mileage < 60_000:
            score += 10
        elif car_mileage < 100_000:
            score += 5

    car_year = car.get("year")
    min_year = filters.get("min_year")
    if car_year:
        if min_year and car_year < min_year:
            score -= 10
        # If user specified a year, reward exact/close matches more than recency
        if min_year and abs(car_year - min_year) <= 2:
            score += 20  # exact era match is highly relevant
        elif min_year and abs(car_year - min_year) <= 4:
            score += 10
        elif not min_year:
            # No year specified — reward newer cars normally
            age = CURRENT_YEAR - car_year
            if age <= 2:
                score += 15
            elif age <= 4:
                score += 12
            elif age <= 6:
                score += 8
            elif age <= 8:
                score += 4

    car_title = (car.get("title") or "").lower()
    make = (filters.get("make") or "").lower()
    if make:
        if make in car_title:
            score += 25
        else:
            score -= 45  # wrong brand — disqualifying

    model_name = (filters.get("model_name") or "").lower()
    if model_name:
        if model_name in car_title:
            score += 25
        else:
            score -= 55  # wrong model — disqualifying

    wanted_fuel = (filters.get("fuel_type") or "").lower()
    car_fuel = (car.get("fuel_type") or "").lower()
    if wanted_fuel and car_fuel and wanted_fuel in car_fuel:
        score += 8

    return score


def rank_cars(cars: list, filters: dict) -> list:
    for car in cars:
        car["score"] = score_car(car, filters)
    return sorted(cars, key=lambda x: x["score"], reverse=True)
