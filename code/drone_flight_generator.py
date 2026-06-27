import json
import math
import numpy as np
from typing import Dict, List, Tuple, Any
from datetime import datetime


class DroneFlightGenerator:
    """Automated drone flight plan generator with zoning-based property calculations"""

    def __init__(self):
        # Shot type definitions (distances in feet)
        self.shot_types = {
            'CU': {'distance': 92.6, 'fill': 0.95, 'name': 'Close Up'},
            'MS': {'distance': 146.7, 'fill': 0.60, 'name': 'Medium Shot'},
            'LS': {'distance': 352.0, 'fill': 0.25, 'name': 'Long Shot'},
            'XLS': {'distance': 880.0, 'fill': 0.10, 'name': 'Extreme Long Shot'}
        }

        # Default zoning data (Emerald Isle standards)
        self.default_zoning = {
            "R-5W": {
                "district_name": "Waterfront Residential District",
                "min_lot_area_sqft": 5000,
                "min_lot_width_ft": 50,
                "front_setback_ft": 15,
                "rear_setback_ft": 15,
                "side_setback_ft": 7,
                "side_yard_street_ft": 10,
                "max_height_ft": 50
            },
            "R-10": {
                "district_name": "Residential District (water & sewer)",
                "min_lot_area_sqft": 10000,
                "min_lot_width_ft": 60,
                "front_setback_ft": 20,
                "rear_setback_ft": 25,
                "side_setback_ft": 10,
                "side_yard_street_ft": 20,
                "max_height_ft": 50
            },
            "R-15": {
                "district_name": "Single-family Residential (water & sewer)",
                "min_lot_area_sqft": 15000,
                "min_lot_width_ft": 80,
                "front_setback_ft": 20,
                "rear_setback_ft": 25,
                "side_setback_ft": 10,
                "side_yard_street_ft": 20,
                "max_height_ft": 50
            }
        }

        # Video flight types
        self.video_flight_types = {
            'tornado': {'pattern': 'vortex'},
            'nadir_ortho': {'pattern': 'grid'},
            'corkscrew': {'pattern': 'helix'},
            'undulation': {'pattern': 'sine_wave'},
            'boomerang': {'pattern': 'parabola'},
            'rise': {'pattern': 'vertical_rise'},
            'fall': {'pattern': 'vertical_fall'},
            'vortex': {'pattern': 'spiral_in'},
            'pedestal': {'pattern': 'vertical_smooth'}
        }

        # Photo flight types
        self.photo_flight_types = {
            'strafe_left_low': {'pattern': 'lateral', 'direction': 'left', 'altitude': 30},
            'strafe_left_medium': {'pattern': 'lateral', 'direction': 'left', 'altitude': 60},
            'strafe_left_high': {'pattern': 'lateral', 'direction': 'left', 'altitude': 100},
            'strafe_right_low': {'pattern': 'lateral', 'direction': 'right', 'altitude': 30},
            'strafe_right_medium': {'pattern': 'lateral', 'direction': 'right', 'altitude': 60},
            'strafe_right_high': {'pattern': 'lateral', 'direction': 'right', 'altitude': 100},
            'pan_in_low': {'pattern': 'pan', 'direction': 'in', 'altitude': 30},
            'pan_in_medium': {'pattern': 'pan', 'direction': 'in', 'altitude': 60},
            'pan_in_high': {'pattern': 'pan', 'direction': 'in', 'altitude': 100},
            'pan_out_low': {'pattern': 'pan', 'direction': 'out', 'altitude': 30},
            'pan_out_medium': {'pattern': 'pan', 'direction': 'out', 'altitude': 60},
            'pan_out_high': {'pattern': 'pan', 'direction': 'out', 'altitude': 100},
            'staircase_curve': {'pattern': 'staircase'},
            'orbit': {'pattern': 'circle', 'altitude': 60},
            'rise': {'pattern': 'vertical_rise'},
            'fall': {'pattern': 'vertical_fall'},
            'overhead': {'pattern': 'nadir', 'altitude': 80},
            'xls': {'pattern': 'circle', 'altitude': 120, 'shot_type': 'XLS'}
        }

    def feet_to_meters(self, feet: float) -> float:
        return feet * 0.3048

    def meters_to_feet(self, meters: float) -> float:
        return meters / 0.3048

    def calculate_property_envelope(self, zoning_district: str = "R-5W") -> Dict:
        """Calculate property and building dimensions from zoning"""
        zoning = self.default_zoning.get(zoning_district, self.default_zoning["R-5W"])

        # Calculate minimum lot depth
        min_lot_depth_ft = zoning["min_lot_area_sqft"] / zoning["min_lot_width_ft"]

        # Calculate buildable area (subtract setbacks)
        buildable_width_ft = zoning["min_lot_width_ft"] - (2 * zoning["side_setback_ft"])
        buildable_depth_ft = min_lot_depth_ft - zoning["front_setback_ft"] - zoning["rear_setback_ft"]

        return {
            "property": {
                "width_ft": zoning["min_lot_width_ft"],
                "depth_ft": min_lot_depth_ft,
                "area_sqft": zoning["min_lot_area_sqft"],
                "width_m": self.feet_to_meters(zoning["min_lot_width_ft"]),
                "depth_m": self.feet_to_meters(min_lot_depth_ft)
            },
            "building": {
                "width_ft": buildable_width_ft,
                "depth_ft": buildable_depth_ft,
                "height_ft": zoning["max_height_ft"],
                "width_m": self.feet_to_meters(buildable_width_ft),
                "depth_m": self.feet_to_meters(buildable_depth_ft),
                "height_m": self.feet_to_meters(zoning["max_height_ft"])
            },
            "setbacks": {
                "front_ft": zoning["front_setback_ft"],
                "rear_ft": zoning["rear_setback_ft"],
                "side_ft": zoning["side_setback_ft"]
            }
        }

    def add_distance_to_gps(self, lat: float, lon: float, distance_m: float, bearing_deg: float) -> Tuple[float, float]:
        """Add distance in meters at a bearing to GPS coordinates"""
        R = 6378137.0
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        bearing_rad = math.radians(bearing_deg)

        new_lat_rad = math.asin(
            math.sin(lat_rad) * math.cos(distance_m / R) +
            math.cos(lat_rad) * math.sin(distance_m / R) * math.cos(bearing_rad)
        )

        new_lon_rad = lon_rad + math.atan2(
            math.sin(bearing_rad) * math.sin(distance_m / R) * math.cos(lat_rad),
            math.cos(distance_m / R) - math.sin(lat_rad) * math.sin(new_lat_rad)
        )

        return math.degrees(new_lat_rad), math.degrees(new_lon_rad)

    def create_property_perimeter(self, center_lat: float, center_lon: float,
                                  width_m: float, depth_m: float) -> List[Tuple[float, float]]:
        """Create rectangular property boundary"""
        half_width = width_m / 2
        half_depth = depth_m / 2

        corners = []
        # NW corner
        lat, lon = self.add_distance_to_gps(center_lat, center_lon, half_depth, 0)
        lat, lon = self.add_distance_to_gps(lat, lon, half_width, 270)
        corners.append((lat, lon))

        # NE corner
        lat, lon = self.add_distance_to_gps(center_lat, center_lon, half_depth, 0)
        lat, lon = self.add_distance_to_gps(lat, lon, half_width, 90)
        corners.append((lat, lon))

        # SE corner
        lat, lon = self.add_distance_to_gps(center_lat, center_lon, half_depth, 180)
        lat, lon = self.add_distance_to_gps(lat, lon, half_width, 90)
        corners.append((lat, lon))

        # SW corner
        lat, lon = self.add_distance_to_gps(center_lat, center_lon, half_depth, 180)
        lat, lon = self.add_distance_to_gps(lat, lon, half_width, 270)
        corners.append((lat, lon))

        corners.append(corners[0])  # Close the polygon
        return corners

    # VIDEO FLIGHT PATTERNS

    def generate_vortex_pattern(self, center_lat: float, center_lon: float,
                                building_dims: Dict, shot_type: str) -> List[List[float]]:
        """Tornado/Vortex - Decreasing radius spiral"""
        base_distance = self.shot_types[shot_type]['distance']
        max_radius_m = self.feet_to_meters(base_distance)
        min_radius_m = max_radius_m * 0.3

        waypoints = []
        num_points = 40
        turns = 3
        t_values = np.linspace(0, turns * 2 * np.pi, num_points)

        for i, t in enumerate(t_values):
            progress = i / (num_points - 1)
            radius_m = max_radius_m - (max_radius_m - min_radius_m) * progress ** 2

            x_local = radius_m * math.cos(t)
            y_local = radius_m * math.sin(t)
            distance = math.sqrt(x_local ** 2 + y_local ** 2)
            bearing = math.degrees(math.atan2(x_local, y_local))

            lat, lon = self.add_distance_to_gps(center_lat, center_lon, distance, bearing)
            altitude = 25 + (125 - 25) * progress
            heading = (math.degrees(t) + 90) % 360

            waypoints.append([lat, lon, altitude, heading])

        return waypoints

    def generate_grid_pattern(self, center_lat: float, center_lon: float,
                              building_dims: Dict, shot_type: str) -> List[List[float]]:
        """Nadir Ortho - Grid pattern over building"""
        building_width_m = building_dims['width_m']
        building_depth_m = building_dims['depth_m']

        altitude = 60
        overlap = 0.75

        # Calculate grid spacing based on camera FOV at altitude
        fov_coverage_m = 2 * altitude * math.tan(math.radians(42))  # ~60m at 60ft
        spacing = fov_coverage_m * (1 - overlap)

        waypoints = []

        # Expand grid beyond building
        grid_width = building_width_m + 20
        grid_depth = building_depth_m + 20

        num_lines = int(grid_depth / spacing) + 1

        for i in range(num_lines):
            y_offset = -grid_depth / 2 + i * spacing

            if i % 2 == 0:  # Left to right
                x_start, x_end = -grid_width / 2, grid_width / 2
            else:  # Right to left
                x_start, x_end = grid_width / 2, -grid_width / 2

            num_points = int(grid_width / spacing) + 1
            for j in range(num_points):
                progress = j / (num_points - 1)
                x_offset = x_start + (x_end - x_start) * progress

                lat, lon = self.add_distance_to_gps(center_lat, center_lon, abs(y_offset), 0 if y_offset >= 0 else 180)
                lat, lon = self.add_distance_to_gps(lat, lon, abs(x_offset), 90 if x_offset >= 0 else 270)

                waypoints.append([lat, lon, altitude, 0])

        return waypoints

    def generate_helix_pattern(self, center_lat: float, center_lon: float,
                               building_dims: Dict, shot_type: str) -> List[List[float]]:
        """Corkscrew - Ascending helix"""
        base_distance = self.shot_types[shot_type]['distance']
        radius_m = self.feet_to_meters(base_distance)

        waypoints = []
        num_points = 40
        turns = 2.5
        t_values = np.linspace(0, turns * 2 * np.pi, num_points)

        for i, t in enumerate(t_values):
            x_local = radius_m * math.cos(t)
            y_local = radius_m * math.sin(t)
            distance = math.sqrt(x_local ** 2 + y_local ** 2)
            bearing = math.degrees(math.atan2(x_local, y_local))

            lat, lon = self.add_distance_to_gps(center_lat, center_lon, distance, bearing)
            altitude = 25 + (125 - 25) * (i / (num_points - 1))
            heading = (math.degrees(t) + 90) % 360

            waypoints.append([lat, lon, altitude, heading])

        return waypoints

    def generate_sine_wave_pattern(self, center_lat: float, center_lon: float,
                                   building_dims: Dict, shot_type: str) -> List[List[float]]:
        """Undulation - Sine wave around building perimeter"""
        building_width_m = building_dims['width_m']
        building_depth_m = building_dims['depth_m']
        perimeter_m = 2 * (building_width_m + building_depth_m)

        base_distance = self.shot_types[shot_type]['distance']
        standoff_m = self.feet_to_meters(base_distance * 0.5)

        waypoints = []
        num_points = 40

        for i in range(num_points):
            progress = i / num_points
            perimeter_pos = progress * perimeter_m

            # Determine which side of building
            if perimeter_pos < building_width_m:  # North side
                x_offset = -building_width_m / 2 + perimeter_pos
                y_offset = building_depth_m / 2 + standoff_m
                bearing = math.degrees(math.atan2(x_offset, y_offset))
            elif perimeter_pos < building_width_m + building_depth_m:  # East side
                x_offset = building_width_m / 2 + standoff_m
                y_offset = building_depth_m / 2 - (perimeter_pos - building_width_m)
                bearing = math.degrees(math.atan2(x_offset, y_offset))
            elif perimeter_pos < 2 * building_width_m + building_depth_m:  # South side
                x_offset = building_width_m / 2 - (perimeter_pos - building_width_m - building_depth_m)
                y_offset = -building_depth_m / 2 - standoff_m
                bearing = math.degrees(math.atan2(x_offset, y_offset))
            else:  # West side
                x_offset = -building_width_m / 2 - standoff_m
                y_offset = -building_depth_m / 2 + (perimeter_pos - 2 * building_width_m - building_depth_m)
                bearing = math.degrees(math.atan2(x_offset, y_offset))

            distance = math.sqrt(x_offset ** 2 + y_offset ** 2)
            lat, lon = self.add_distance_to_gps(center_lat, center_lon, distance, bearing)

            altitude = 40 + 20 * math.sin(progress * 4 * math.pi)
            heading = (bearing + 180) % 360

            waypoints.append([lat, lon, altitude, heading])

        waypoints.append(waypoints[0])
        return waypoints

    def generate_parabola_pattern(self, center_lat: float, center_lon: float,
                                  building_dims: Dict, shot_type: str) -> List[List[float]]:
        """Boomerang - Parabolic arc out and back"""
        base_distance = self.shot_types[shot_type]['distance']
        max_distance_m = self.feet_to_meters(base_distance * 2)

        waypoints = []
        num_points = 30

        for i in range(num_points):
            progress = i / (num_points - 1)
            # Parabolic distance: goes out then comes back
            t = 2 * progress - 1  # -1 to 1
            distance = max_distance_m * (1 - t ** 2)

            bearing = 0  # North
            lat, lon = self.add_distance_to_gps(center_lat, center_lon, distance, bearing)

            altitude = 25 + 75 * (1 - t ** 2)
            heading = 180 if progress < 0.5 else 0

            waypoints.append([lat, lon, altitude, heading])

        return waypoints

    def generate_vertical_rise(self, center_lat: float, center_lon: float,
                               building_dims: Dict, shot_type: str) -> List[List[float]]:
        """Rise - Vertical ascent from ground level"""
        base_distance = self.shot_types[shot_type]['distance']
        standoff_m = self.feet_to_meters(base_distance)

        waypoints = []
        num_points = 25

        # Position at standoff distance
        lat, lon = self.add_distance_to_gps(center_lat, center_lon, standoff_m, 0)

        for i in range(num_points):
            progress = i / (num_points - 1)
            altitude = 10 + 110 * progress
            heading = 180
            waypoints.append([lat, lon, altitude, heading])

        return waypoints

    def generate_vertical_fall(self, center_lat: float, center_lon: float,
                               building_dims: Dict, shot_type: str) -> List[List[float]]:
        """Fall - Vertical descent from high altitude"""
        base_distance = self.shot_types[shot_type]['distance']
        standoff_m = self.feet_to_meters(base_distance)

        waypoints = []
        num_points = 25

        lat, lon = self.add_distance_to_gps(center_lat, center_lon, standoff_m, 0)

        for i in range(num_points):
            progress = i / (num_points - 1)
            altitude = 120 - 110 * progress
            heading = 180
            waypoints.append([lat, lon, altitude, heading])

        return waypoints

    def generate_vertical_smooth(self, center_lat: float, center_lon: float,
                                 building_dims: Dict, shot_type: str) -> List[List[float]]:
        """Pedestal - Smooth vertical tracking"""
        base_distance = self.shot_types[shot_type]['distance']
        standoff_m = self.feet_to_meters(base_distance * 0.8)

        waypoints = []
        num_points = 20

        lat, lon = self.add_distance_to_gps(center_lat, center_lon, standoff_m, 0)

        for i in range(num_points):
            progress = i / (num_points - 1)
            # Ease in/out
            eased = (math.sin((progress - 0.5) * math.pi) + 1) / 2
            altitude = 15 + 65 * eased
            heading = 180
            waypoints.append([lat, lon, altitude, heading])

        return waypoints

    # PHOTO FLIGHT PATTERNS

    def generate_lateral_pattern(self, center_lat: float, center_lon: float,
                                 building_dims: Dict, flight_config: Dict, shot_type: str) -> List[List[float]]:
        """Strafe - Lateral movement parallel to building"""
        base_distance = self.shot_types[shot_type]['distance']
        standoff_m = self.feet_to_meters(base_distance)
        building_width_m = building_dims['width_m']

        altitude = flight_config['altitude']
        direction = flight_config['direction']
        bearing = 270 if direction == 'left' else 90

        # Position at standoff distance from building
        lat_start, lon_start = self.add_distance_to_gps(center_lat, center_lon, standoff_m, 0)

        # Start offset
        start_bearing = (bearing + 180) % 360
        lat_start, lon_start = self.add_distance_to_gps(lat_start, lon_start, building_width_m * 0.7, start_bearing)

        waypoints = []
        num_points = 20
        travel_distance = building_width_m * 1.4

        for i in range(num_points):
            progress = i / (num_points - 1)
            distance_traveled = progress * travel_distance
            lat, lon = self.add_distance_to_gps(lat_start, lon_start, distance_traveled, bearing)
            heading = bearing
            waypoints.append([lat, lon, altitude, heading])

        return waypoints

    def generate_pan_pattern(self, center_lat: float, center_lon: float,
                             building_dims: Dict, flight_config: Dict, shot_type: str) -> List[List[float]]:
        """Pan - Forward/backward movement toward/away from subject"""
        base_distance = self.shot_types[shot_type]['distance']
        direction = flight_config['direction']
        altitude = flight_config['altitude']

        if direction == 'in':
            start_distance_m = self.feet_to_meters(base_distance * 2.5)
            end_distance_m = self.feet_to_meters(base_distance * 0.8)
        else:  # out
            start_distance_m = self.feet_to_meters(base_distance * 0.8)
            end_distance_m = self.feet_to_meters(base_distance * 2.5)

        waypoints = []
        num_points = 25
        bearing = 0  # Approach from south

        for i in range(num_points):
            progress = i / (num_points - 1)
            distance = start_distance_m + (end_distance_m - start_distance_m) * progress
            lat, lon = self.add_distance_to_gps(center_lat, center_lon, distance, bearing)
            heading = 0 if direction == 'in' else 180
            waypoints.append([lat, lon, altitude, heading])

        return waypoints

    def generate_staircase_pattern(self, center_lat: float, center_lon: float,
                                   building_dims: Dict, shot_type: str) -> List[List[float]]:
        """Staircase - Stepped altitude changes"""
        base_distance = self.shot_types[shot_type]['distance']
        radius_m = self.feet_to_meters(base_distance)

        waypoints = []
        steps = 5
        points_per_step = 6

        for step in range(steps):
            altitude = 25 + (100 - 25) * (step / (steps - 1))
            angle_start = (step / steps) * 2 * math.pi

            for i in range(points_per_step):
                progress = i / (points_per_step - 1)
                angle = angle_start + progress * (2 * math.pi / steps)

                x_local = radius_m * math.cos(angle)
                y_local = radius_m * math.sin(angle)
                distance = math.sqrt(x_local ** 2 + y_local ** 2)
                bearing = math.degrees(math.atan2(x_local, y_local))

                lat, lon = self.add_distance_to_gps(center_lat, center_lon, distance, bearing)
                heading = (bearing + 180) % 360
                waypoints.append([lat, lon, altitude, heading])

        return waypoints

    def generate_circle_pattern(self, center_lat: float, center_lon: float,
                                building_dims: Dict, flight_config: Dict, shot_type: str) -> List[List[float]]:
        """Orbit/Circle - Circular pattern around subject"""
        if 'shot_type' in flight_config:
            shot_type = flight_config['shot_type']

        base_distance = self.shot_types[shot_type]['distance']
        radius_m = self.feet_to_meters(base_distance)
        altitude = flight_config.get('altitude', 60)

        waypoints = []
        num_points = 36
        t_values = np.linspace(0, 2 * np.pi, num_points)

        for t in t_values:
            x_local = radius_m * math.cos(t)
            y_local = radius_m * math.sin(t)
            distance = math.sqrt(x_local ** 2 + y_local ** 2)
            bearing = math.degrees(math.atan2(x_local, y_local))

            lat, lon = self.add_distance_to_gps(center_lat, center_lon, distance, bearing)
            heading = (bearing + 180) % 360
            waypoints.append([lat, lon, altitude, heading])

        waypoints.append(waypoints[0])
        return waypoints

    def generate_nadir_pattern(self, center_lat: float, center_lon: float,
                               building_dims: Dict, flight_config: Dict) -> List[List[float]]:
        """Overhead - Direct nadir shot"""
        altitude = flight_config.get('altitude', 80)
        waypoints = [[center_lat, center_lon, altitude, 0]]
        return waypoints

    def generate_flight_for_type(self, center_lat: float, center_lon: float,
                                 flight_type: str, flight_config: Dict,
                                 building_dims: Dict, shot_type: str = 'MS') -> List[List[float]]:
        """Generate waypoints for a specific flight type"""
        pattern = flight_config['pattern']

        # Video patterns
        if pattern == 'vortex':
            return self.generate_vortex_pattern(center_lat, center_lon, building_dims, shot_type)
        elif pattern == 'grid':
            return self.generate_grid_pattern(center_lat, center_lon, building_dims, shot_type)
        elif pattern == 'helix':
            return self.generate_helix_pattern(center_lat, center_lon, building_dims, shot_type)
        elif pattern == 'sine_wave':
            return self.generate_sine_wave_pattern(center_lat, center_lon, building_dims, shot_type)
        elif pattern == 'parabola':
            return self.generate_parabola_pattern(center_lat, center_lon, building_dims, shot_type)
        elif pattern == 'vertical_rise':
            return self.generate_vertical_rise(center_lat, center_lon, building_dims, shot_type)
        elif pattern == 'vertical_fall':
            return self.generate_vertical_fall(center_lat, center_lon, building_dims, shot_type)
        elif pattern == 'spiral_in':
            return self.generate_vortex_pattern(center_lat, center_lon, building_dims, shot_type)
        elif pattern == 'vertical_smooth':
            return self.generate_vertical_smooth(center_lat, center_lon, building_dims, shot_type)

        # Photo patterns
        elif pattern == 'lateral':
            return self.generate_lateral_pattern(center_lat, center_lon, building_dims, flight_config, shot_type)
        elif pattern == 'pan':
            return self.generate_pan_pattern(center_lat, center_lon, building_dims, flight_config, shot_type)
        elif pattern == 'staircase':
            return self.generate_staircase_pattern(center_lat, center_lon, building_dims, shot_type)
        elif pattern == 'circle':
            return self.generate_circle_pattern(center_lat, center_lon, building_dims, flight_config, shot_type)
        elif pattern == 'nadir':
            return self.generate_nadir_pattern(center_lat, center_lon, building_dims, flight_config)

        else:
            altitude = flight_config.get('altitude', 60)
            return [[center_lat, center_lon, altitude, 0]]

    def process_addresses(self, input_json: Dict, mission_type: str = 'video',
                          shot_type: str = 'MS', zoning_district: str = "R-5W") -> Dict:
        """Process addresses and generate complete flight plans"""
        envelope = self.calculate_property_envelope(zoning_district)
        flight_types = self.video_flight_types if mission_type == 'video' else self.photo_flight_types

        mission_data = {
            "mission_info": {
                "type": mission_type,
                "shot_type": shot_type,
                "zoning_district": zoning_district,
                "generated_at": datetime.now().isoformat(),
                "group_id": input_json.get("group_id"),
                "center_location": {
                    "latitude": input_json["stats"]["center_latitude"],
                    "longitude": input_json["stats"]["center_longitude"]
                }
            },
            "property_envelope": envelope,
            "subjects": []
        }

        for address_data in input_json["addresses"]:
            property_perimeter = self.create_property_perimeter(
                address_data["latitude"],
                address_data["longitude"],
                envelope["property"]["width_m"],
                envelope["property"]["depth_m"]
            )

            subject = {
                "name": address_data["address"],
                "type": "standard",
                "latitude": address_data["latitude"],
                "longitude": address_data["longitude"],
                "formatted_address": address_data.get("formatted_address", address_data["address"]),
                "property_boundary": property_perimeter,
                "dimensions": envelope,
                "flight_types": {}
            }

            for flight_name, flight_config in flight_types.items():
                waypoints = self.generate_flight_for_type(
                    address_data["latitude"],
                    address_data["longitude"],
                    flight_name,
                    flight_config,
                    envelope["building"],
                    shot_type
                )

                formatted_name = flight_name.replace('_', ' ').title()

                subject["flight_types"][formatted_name] = {
                    "exists": True,
                    "pattern_type": flight_config['pattern'],
                    "specs": {
                        "shot_type": shot_type,
                        "shot_distance_ft": self.shot_types[shot_type]['distance'],
                        "num_waypoints": len(waypoints),
                        "altitude_range": f"{min(w[2] for w in waypoints):.1f}-{max(w[2] for w in waypoints):.1f} ft"
                    },
                    "waypoints": [
                        {
                            "latitude": w[0],
                            "longitude": w[1],
                            "altitude_ft": w[2],
                            "heading_deg": w[3]
                        } for w in waypoints
                    ]
                }

            mission_data["subjects"].append(subject)

        return mission_data


# Example usage
if __name__ == "__main__":
    import sys

    # Load your actual JSON file
    with open('input_addresses.json', 'r') as f:
        sample_input = json.load(f)

    generator = DroneFlightGenerator()

    video_mission = generator.process_addresses(
        sample_input,
        mission_type='video',
        shot_type='MS',
        zoning_district='R-5W'
    )

    photo_mission = generator.process_addresses(
        sample_input,
        mission_type='photo',
        shot_type='CU',
        zoning_district='R-5W'
    )

    with open('video_mission_output.json', 'w') as f:
        json.dump(video_mission, f, indent=2)

    with open('photo_mission_output.json', 'w') as f:
        json.dump(photo_mission, f, indent=2)

    print(f"✓ Generated video mission: {len(video_mission['subjects'])} subjects")
    print(f"✓ Generated photo mission: {len(photo_mission['subjects'])} subjects")
    print(f"\nProperty: {video_mission['property_envelope']['property']}")
    print(f"Building: {video_mission['property_envelope']['building']}")