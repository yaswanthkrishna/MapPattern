import requests
import time

# Base URL and Candidate ID for the API
BASE_URL = "https://challenge.crossmint.io/api"
CANDIDATE_ID = "144e3add-dc06-46c6-9398-3a85a0be07b4"

# Phase-specific grid sizes
PHASE_1_GRID_SIZE = 11
PHASE_2_GRID_SIZE = 30


class CrossmintAPI:
    """Handles API interactions for placing and deleting entities on the grid."""

    def __init__(self, base_url, candidate_id):
        self.base_url = base_url
        self.candidate_id = candidate_id
        self.headers = {"Content-Type": "application/json"}

    def delete_object(self, row, col):
        """Deletes any entity at a given position (row, col)."""
        endpoints = ["polyanets", "soloons", "comeths"]
        deleted_any = False

        for endpoint in endpoints:
            url = f"{self.base_url}/{endpoint}"
            payload = {"candidateId": self.candidate_id, "row": row, "column": col}

            try:
                response = requests.delete(url, json=payload, headers=self.headers)
                if response.status_code == 200:
                    print(f"Deleted {endpoint} at ({row}, {col})")
                    deleted_any = True
                elif response.status_code != 404:
                    print(f"Failed to delete {endpoint} at ({row}, {col}). Status: {response.status_code}")
                    time.sleep(1)
            except requests.RequestException as e:
                print(f"Error deleting {endpoint} at ({row}, {col}): {e}")
                time.sleep(1)

        return deleted_any

    def place_entity(self, entity_type, row, col, direction=None, color=None):
        """Places an entity on the grid with optional direction and color attributes."""
        endpoint = f"{self.base_url}/{entity_type.lower()}"
        payload = {
            "candidateId": self.candidate_id,
            "row": row,
            "column": col
        }
        if direction:
            payload["direction"] = direction
        if color:
            payload["color"] = color

        while True:
            try:
                response = requests.post(endpoint, json=payload, headers=self.headers)
                if response.status_code == 201:
                    print(f"Placed {entity_type} at ({row}, {col}) with direction={direction}, color={color}")
                    break
                elif response.status_code == 429:
                    print("Rate limit hit. Retrying after a delay...")
                    time.sleep(5)
                else:
                    print(f"Failed to place {entity_type} at ({row}, {col}). Status: {response.status_code}")
                    break
            except requests.RequestException as e:
                print(f"Error placing {entity_type} at ({row}, {col}): {e}")
                break

    def fetch_goal_map(self):
        """Fetches the goal map configuration."""
        url = f"{self.base_url}/map/{self.candidate_id}/goal"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print("Goal map fetched successfully.")
                return response.json()
            else:
                print(f"Failed to fetch goal map. Status: {response.status_code}")
                return None
        except requests.RequestException as e:
            print(f"Error fetching goal map: {e}")
            return None


class Phase1Pattern:
    """Pattern for Phase 1: Places POLYanets along diagonals."""

    def __init__(self, api, grid_size):
        self.api = api
        self.grid_size = grid_size

    def execute(self):
        for i in range(2, self.grid_size - 2):
            self.api.place_entity("polyanets", i, i)
            self.api.place_entity("polyanets", i, self.grid_size - 1 - i)
        print("Finished placing POLYanets for Phase 1.")


class Phase2Pattern:
    """Pattern for Phase 2: Places entities based on the goal map."""

    def __init__(self, api, goal_map):
        self.api = api
        self.goal_map = goal_map

    def execute(self):
        entity_mapping = {
            "POLYANET": lambda row, col: self.api.place_entity("polyanets", row, col),
            "COMETH": lambda row, col, direction: self.api.place_entity("comeths", row, col, direction=direction),
            "SOLOON": lambda row, col, color: self.api.place_entity("soloons", row, col, color=color),
        }

        for row_idx, row in enumerate(self.goal_map["goal"]):
            for col_idx, cell in enumerate(row):
                if cell == "SPACE":
                    continue
                elif cell.startswith("POLYANET"):
                    entity_mapping["POLYANET"](row_idx, col_idx)
                elif cell.endswith("COMETH"):
                    direction = cell.split("_")[0].lower()
                    entity_mapping["COMETH"](row_idx, col_idx, direction)
                elif cell.endswith("SOLOON"):
                    color = cell.split("_")[0].lower()
                    entity_mapping["SOLOON"](row_idx, col_idx, color)
        print("Finished placing entities for Phase 2.")


def delete_all(api, grid_size, goal_map, max_attempts=5):
    """Deletes all entities from the grid if they exist."""
    any_entities = any(cell != "SPACE" for row in goal_map["goal"] for cell in row)
    if not any_entities:
        print("Grid is already empty (only SPACE). Skipping deletion.")
        return

    attempt = 0
    while attempt < max_attempts:
        any_deleted = False
        for row in range(grid_size):
            for col in range(grid_size):
                if goal_map["goal"][row][col] != "SPACE":
                    if api.delete_object(row, col):
                        any_deleted = True
        if not any_deleted:
            print("No more objects found. Grid is clear.")
            break
        print("Objects deleted. Checking grid again...")
        attempt += 1
    if attempt == max_attempts:
        print("Max attempts reached. Stopping deletion.")


def detect_phase(grid_size):
    """Determines the phase based on the grid size."""
    if grid_size == PHASE_1_GRID_SIZE:
        return 1
    elif grid_size == PHASE_2_GRID_SIZE:
        return 2
    else:
        print("Unknown grid size; cannot determine phase.")
        return None


# Main execution
api = CrossmintAPI(BASE_URL, CANDIDATE_ID)
goal_map = api.fetch_goal_map()

if goal_map and "goal" in goal_map:
    grid_size = len(goal_map["goal"])
    print(f"Detected grid size: {grid_size}x{grid_size}")

    phase = detect_phase(grid_size)
    if phase is None:
        print("Unable to determine phase. Exiting.")
    else:
        print(f"Detected Phase {phase}.")

        delete_all(api, grid_size, goal_map)

        if phase == 1:
            Phase1Pattern(api, grid_size).execute()
        elif phase == 2:
            Phase2Pattern(api, goal_map).execute()
else:
    print("Key 'goal' not found in goal_map.")
