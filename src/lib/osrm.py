import logging
import math

import aiohttp

logger = logging.getLogger("myride.osrm")

PUBLIC_OSRM_MATCH_URL = "http://router.project-osrm.org/match/v1/driving"


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def calculate_coords_distance_miles(coords: list[tuple[float, float]]) -> float:
    if len(coords) < 2:
        return 0.0
    total = 0.0
    for i in range(len(coords) - 1):
        total += haversine_miles(coords[i][1], coords[i][0], coords[i + 1][1], coords[i + 1][0])
    return round(total, 2)


def filter_and_downsample_points(
    raw_coords: list[tuple[float, float]], max_points: int = 80
) -> list[tuple[float, float]]:
    if not raw_coords:
        return []

    # Filter out stationary / duplicate points (< ~10 meters apart)
    filtered = [raw_coords[0]]
    for pt in raw_coords[1:]:
        last = filtered[-1]
        dist = haversine_miles(last[1], last[0], pt[1], pt[0])
        if dist > 0.005:  # > ~8 meters
            filtered.append(pt)

    if len(filtered) <= max_points:
        return filtered

    # Evenly sample if still exceeding max_points for OSRM URL limits
    step = len(filtered) / (max_points - 1)
    sampled = [filtered[int(i * step)] for i in range(max_points - 1)]
    sampled.append(filtered[-1])
    return sampled


async def match_route_osrm(raw_coords: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if len(raw_coords) < 2:
        return raw_coords

    sampled_coords = filter_and_downsample_points(raw_coords, max_points=80)
    coord_str = ";".join(f"{lon:.6f},{lat:.6f}" for lon, lat in sampled_coords)
    url = f"{PUBLIC_OSRM_MATCH_URL}/{coord_str}?overview=full&geometries=geojson"

    try:
        timeout = aiohttp.ClientTimeout(total=5.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("code") == "Ok" and data.get("matchings"):
                        matched_coords = data["matchings"][0]["geometry"]["coordinates"]
                        logger.info(
                            "Successfully matched route with OSRM (%d input points -> %d snapped vector points)",
                            len(sampled_coords),
                            len(matched_coords),
                        )
                        return [tuple(pt) for pt in matched_coords]
                logger.warning("OSRM Match API returned non-OK status: %s", resp.status)
    except Exception as e:
        logger.warning("Failed to match route via public OSRM API (using raw points fallback): %s", e)

    return raw_coords
