import json
import time
import math
from typing import List, Dict, Tuple
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import random


class AddressGeocoder:
    def __init__(self, user_agent="address_geocoder"):
        """Initialize the geocoder with Nominatim (OpenStreetMap)"""
        self.geolocator = Nominatim(user_agent=user_agent)

    def geocode_address(self, address: str) -> Dict:
        """
        Geocode a single address and return GPS coordinates
        """
        try:
            # Add delay to respect rate limits
            time.sleep(1)
            location = self.geolocator.geocode(address)

            if location:
                return {
                    "address": address,
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                    "formatted_address": location.address
                }
            else:
                print(f"Could not geocode: {address}")
                return {
                    "address": address,
                    "latitude": None,
                    "longitude": None,
                    "formatted_address": None,
                    "error": "Address not found"
                }
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"Geocoding error for {address}: {e}")
            return {
                "address": address,
                "latitude": None,
                "longitude": None,
                "formatted_address": None,
                "error": str(e)
            }

    def process_addresses_from_file(self, filename: str) -> List[Dict]:
        """
        Read addresses from file and geocode them
        """
        geocoded_addresses = []

        try:
            with open(filename, 'r') as file:
                addresses = [line.strip() for line in file if line.strip()]
        except FileNotFoundError:
            print(f"File {filename} not found. Using test addresses.")
            addresses = self.get_test_addresses()

        print(f"Processing {len(addresses)} addresses...")

        for i, address in enumerate(addresses, 1):
            print(f"Geocoding {i}/{len(addresses)}: {address}")
            geocoded = self.geocode_address(address)
            geocoded_addresses.append(geocoded)

        return geocoded_addresses

    def get_test_addresses(self) -> List[str]:
        """
        Return 30 test addresses for demonstration
        """
        return [
            # New York City area
            "350 5th Ave, New York, NY 10118",  # Empire State Building
            "1 Times Square, New York, NY 10036",
            "285 Fulton St, New York, NY 10007",
            "30 Rockefeller Plaza, New York, NY 10112",
            "89 E 42nd St, New York, NY 10017",

            # Los Angeles area
            "6925 Hollywood Blvd, Hollywood, CA 90028",
            "100 Universal City Plaza, Universal City, CA 91608",
            "1313 Disneyland Dr, Anaheim, CA 92802",
            "200 Santa Monica Pier, Santa Monica, CA 90401",
            "6060 Center Dr, Los Angeles, CA 90045",

            # Chicago area
            "233 S Wacker Dr, Chicago, IL 60606",  # Willis Tower
            "875 N Michigan Ave, Chicago, IL 60611",
            "1060 W Addison St, Chicago, IL 60613",
            "1901 W Madison St, Chicago, IL 60612",
            "5700 S Lake Shore Dr, Chicago, IL 60637",

            # San Francisco area
            "1 Letterman Dr, San Francisco, CA 94129",
            "Golden Gate Bridge, San Francisco, CA 94129",
            "Pier 39, San Francisco, CA 94133",
            "1 Market St, San Francisco, CA 94105",
            "3601 Lyon St, San Francisco, CA 94123",

            # Boston area
            "4 Jersey St, Boston, MA 02215",  # Fenway Park
            "1 Faneuil Hall Sq, Boston, MA 02109",
            "200 Stuart St, Boston, MA 02116",
            "77 Massachusetts Ave, Cambridge, MA 02139",
            "1 Harvard Yard, Cambridge, MA 02138",

            # Washington DC area
            "1600 Pennsylvania Ave NW, Washington, DC 20500",  # White House
            "2 15th St NW, Washington, DC 20024",
            "Independence Ave SW, Washington, DC 20560",
            "400 Maryland Ave SW, Washington, DC 20202",
            "3001 Connecticut Ave NW, Washington, DC 20008"
        ]


class AddressClusterer:
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the Haversine distance between two GPS coordinates in kilometers
        """
        R = 6371  # Earth's radius in kilometers

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    @staticmethod
    def group_by_proximity(addresses: List[Dict], max_group_size: int = 5) -> List[List[Dict]]:
        """
        Group addresses by proximity using a simple clustering algorithm
        """
        # Filter out addresses that couldn't be geocoded
        valid_addresses = [addr for addr in addresses
                           if addr.get('latitude') is not None
                           and addr.get('longitude') is not None]

        if not valid_addresses:
            print("No valid geocoded addresses to group")
            return []

        # Create groups using a greedy clustering approach
        groups = []
        unassigned = valid_addresses.copy()

        while unassigned:
            # Start a new group with a random unassigned address
            current_group = [unassigned.pop(0)]

            # Find nearest neighbors for this group
            while len(current_group) < max_group_size and unassigned:
                # Calculate center of current group
                center_lat = sum(addr['latitude'] for addr in current_group) / len(current_group)
                center_lon = sum(addr['longitude'] for addr in current_group) / len(current_group)

                # Find nearest unassigned address to group center
                min_distance = float('inf')
                nearest_addr = None
                nearest_idx = -1

                for idx, addr in enumerate(unassigned):
                    distance = AddressClusterer.haversine_distance(
                        center_lat, center_lon,
                        addr['latitude'], addr['longitude']
                    )
                    if distance < min_distance:
                        min_distance = distance
                        nearest_addr = addr
                        nearest_idx = idx

                if nearest_addr:
                    current_group.append(nearest_addr)
                    unassigned.pop(nearest_idx)

            groups.append(current_group)

        return groups

    @staticmethod
    def calculate_group_stats(group: List[Dict]) -> Dict:
        """
        Calculate statistics for a group of addresses
        """
        if not group:
            return {}

        lats = [addr['latitude'] for addr in group]
        lons = [addr['longitude'] for addr in group]

        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)

        # Calculate max distance from center
        max_distance = 0
        for addr in group:
            distance = AddressClusterer.haversine_distance(
                center_lat, center_lon,
                addr['latitude'], addr['longitude']
            )
            max_distance = max(max_distance, distance)

        return {
            "center_latitude": center_lat,
            "center_longitude": center_lon,
            "max_radius_km": max_distance,
            "address_count": len(group)
        }


def main():
    # Initialize geocoder
    geocoder = AddressGeocoder()

    # Process addresses (from file or test data)
    print("=" * 50)
    print("STEP 1: Geocoding Addresses")
    print("=" * 50)

    # Try to read from file, otherwise use test addresses
    geocoded_addresses = geocoder.process_addresses_from_file("addresses.txt")

    # Save raw geocoded data to JSON
    with open("raw_repo.json", "w") as f:
        json.dump(geocoded_addresses, f, indent=2)
    print(f"\n✅ Saved {len(geocoded_addresses)} geocoded addresses to raw_repo.json")

    # Group addresses by proximity
    print("\n" + "=" * 50)
    print("STEP 2: Grouping by Proximity")
    print("=" * 50)

    groups = AddressClusterer.group_by_proximity(geocoded_addresses, max_group_size=5)

    # Display groups
    print(f"\n📍 Created {len(groups)} groups (max 5 addresses per group):\n")

    for i, group in enumerate(groups, 1):
        print(f"GROUP {i} ({len(group)} addresses)")
        print("-" * 40)

        # Calculate and display group statistics
        stats = AddressClusterer.calculate_group_stats(group)
        print(f"Center: ({stats['center_latitude']:.4f}, {stats['center_longitude']:.4f})")
        print(f"Max radius: {stats['max_radius_km']:.2f} km")
        print("\nAddresses in this group:")

        for j, addr in enumerate(group, 1):
            print(f"  {j}. {addr['address']}")
            print(f"     GPS: ({addr['latitude']:.4f}, {addr['longitude']:.4f})")

        print()

    # Save grouped data to separate JSON files
    for i, group in enumerate(groups, 1):
        filename = f"group_{i}.json"
        with open(filename, "w") as f:
            json.dump({
                "group_id": i,
                "stats": AddressClusterer.calculate_group_stats(group),
                "addresses": group
            }, f, indent=2)

    print(f"✅ Saved {len(groups)} group files (group_1.json, group_2.json, etc.)")

    # Create summary file
    summary = {
        "total_addresses": len(geocoded_addresses),
        "successfully_geocoded": len([a for a in geocoded_addresses if a.get('latitude')]),
        "total_groups": len(groups),
        "groups": []
    }

    for i, group in enumerate(groups, 1):
        summary["groups"].append({
            "group_id": i,
            "size": len(group),
            "stats": AddressClusterer.calculate_group_stats(group),
            "addresses": [addr['address'] for addr in group]
        })

    with open("groups_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("✅ Saved groups_summary.json with all grouping information")


if __name__ == "__main__":
    main()