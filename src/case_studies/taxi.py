"""NYC yellow-cab trips: extract hourly earnings by pickup area, and the airport break-even.

Extract: one pass over a year of TLC trip records (read remotely as parquet), aggregated to
pickup area x day type x hour. The committed snapshot is that aggregate, ~500 rows.

Driver earnings per trip are taken as fare + tip. Tolls, surcharges and taxes pass through to
the city or the toll authority, so they are left out.
"""

import csv
from pathlib import Path

import duckdb

TRIP_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{month}.parquet"
ZONE_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
SNAPSHOT = Path("data/taxi_hourly_2025.csv")
FIELDS = ["area", "to_area", "day_type", "hour", "trips", "earnings", "trip_minutes", "miles"]
# TLC zone ids for the two city airports; Newark is outside the yellow-cab pickup market.
AIRPORTS = {132: "JFK", 138: "LaGuardia"}


def area(zone: str, zones: str) -> str:
    """SQL for the four areas the memo compares."""
    return (
        f"case when {zone} = 132 then 'JFK' when {zone} = 138 then 'LaGuardia' "
        f"when {zones}.Borough = 'Manhattan' then 'Manhattan' else 'Elsewhere' end"
    )


def extract(year: int = 2025, out: Path = SNAPSHOT) -> Path:
    """Aggregate a year of trips into the hourly snapshot (needs network; ~1 minute)."""
    months = [TRIP_URL.format(month=f"{year}-{m:02d}") for m in range(1, 13)]
    connection = duckdb.connect()
    connection.execute("install httpfs; load httpfs")
    connection.execute("set enable_progress_bar = false")
    rows = connection.execute(
        f"""
        with zones as (select * from read_csv(?)),
        trips as (
            select
                tpep_pickup_datetime as pickup,
                date_diff('second', tpep_pickup_datetime, tpep_dropoff_datetime) / 60.0 as minutes,
                fare_amount + tip_amount as earnings,
                trip_distance as miles,
                PULocationID as zone_id,
                DOLocationID as to_zone_id
            from read_parquet(?)
            where fare_amount between 3 and 500 and tip_amount >= 0 and trip_distance > 0
        )
        select
            {area("zone_id", "zones")} as area,
            {area("to_zone_id", "to_zones")} as to_area,
            case when dayofweek(pickup) in (0, 6) then 'weekend' else 'weekday' end as day_type,
            hour(pickup) as hour,
            count(*) as trips,
            round(sum(earnings), 2) as earnings,
            round(sum(minutes), 1) as trip_minutes,
            round(sum(miles), 1) as miles
        from trips
        left join zones on zones.LocationID = trips.zone_id
        left join zones as to_zones on to_zones.LocationID = trips.to_zone_id
        where minutes between 1 and 180 and year(pickup) = ?
        group by all
        order by all
        """,
        [ZONE_URL, months, year],
    ).fetchall()
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(FIELDS)
        writer.writerows(rows)
    return out
