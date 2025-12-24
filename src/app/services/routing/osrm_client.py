"""HTTP client for interacting with OSRM services."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Sequence

import httpx

from ...config import settings

# OSRM table endpoint has URL length limits. Set to 80 for balance between speed and reliability.
# When chunking, we combine source and destination chunks, so 80 means up to 160 coords per URL.
# Public OSRM can handle this, and smaller chunks reduce timeout risk.
DEFAULT_MAX_COORDINATES_PER_REQUEST = 80
# Number of parallel requests to make (speeds up chunk processing significantly)
# Increased to 15 for faster processing while avoiding rate limits
DEFAULT_MAX_PARALLEL_REQUESTS = 15

logger = logging.getLogger(__name__)


class OSRMClient:
    def __init__(
        self,
        base_url: str | None = None,
        profile: str | None = None,
        timeout: float = 60.0,  # Increased timeout for large chunk requests
        max_retries: int | None = None,
        backoff_seconds: float | None = None,
        max_coordinates_per_request: int = DEFAULT_MAX_COORDINATES_PER_REQUEST,
        max_parallel_requests: int = DEFAULT_MAX_PARALLEL_REQUESTS,
    ) -> None:
        self.base_url = base_url or settings.osrm_base_url
        if not self.base_url:
            raise ValueError("OSRM base URL is not configured.")
        self.profile = profile or settings.osrm_profile
        self.max_retries = max_retries if max_retries is not None else settings.osrm_max_retries
        self.backoff_seconds = backoff_seconds if backoff_seconds is not None else settings.osrm_backoff_seconds
        self.max_coordinates_per_request = max_coordinates_per_request
        self.max_parallel_requests = max_parallel_requests
        self.timeout = timeout
        # Don't create a shared client - each thread will create its own
        self._client = None

    def _get_client(self) -> httpx.Client:
        """Get a thread-local HTTP client."""
        # Create a new client for each thread to avoid thread-safety issues
        # Use longer timeout for chunk requests which can be large
        return httpx.Client(
            timeout=httpx.Timeout(self.timeout, connect=10.0),
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=0)
        )

    def _table_single_request(
        self, coordinates: Sequence[tuple[float, float]], sources: Sequence[int] | None = None, destinations: Sequence[int] | None = None
    ) -> dict:
        """Make a single OSRM table request for a subset of coordinates."""
        if len(coordinates) < 1:
            raise ValueError("At least one coordinate is required for OSRM table.")

        coordinate_str = ";".join(f"{lon},{lat}" for lat, lon in coordinates)
        
        # Default to all coordinates if sources/destinations not specified
        if sources is None:
            sources = list(range(len(coordinates)))
        if destinations is None:
            destinations = list(range(len(coordinates)))
        
        index_sequence_sources = ";".join(str(i) for i in sources)
        index_sequence_destinations = ";".join(str(i) for i in destinations)
        
        params = {
            "annotations": "duration,distance",
            "sources": index_sequence_sources,
            "destinations": index_sequence_destinations,
        }
        url = f"{self.base_url}/table/v1/{self.profile}/{coordinate_str}"

        # Use thread-local client
        client = self._get_client()
        try:
            attempt = 0
            while True:
                try:
                    response = client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    if "durations" not in data or "distances" not in data:
                        raise ValueError("OSRM response missing durations/distances.")
                    return data
                except httpx.HTTPStatusError as e:
                    # Handle 414 Request-URI Too Large specifically
                    if e.response.status_code == 414:
                        raise ValueError(
                            f"OSRM request URL too large ({len(coordinates)} coordinates). "
                            f"Try reducing max_coordinates_per_request (current: {self.max_coordinates_per_request})"
                        ) from e
                    attempt += 1
                    if attempt > self.max_retries:
                        raise
                    time.sleep(self.backoff_seconds * attempt)
                except (httpx.TimeoutException, httpx.ReadTimeout) as e:
                    # Handle timeouts with retry
                    attempt += 1
                    if attempt > self.max_retries:
                        logger.warning(f"OSRM request timed out after {self.max_retries} attempts: {e}")
                        raise
                    wait_time = self.backoff_seconds * (2 ** (attempt - 1))  # Exponential backoff
                    logger.debug(f"OSRM request timeout, retrying in {wait_time:.1f}s (attempt {attempt}/{self.max_retries})")
                    time.sleep(wait_time)
                except (httpx.ConnectError, httpx.NetworkError, OSError) as e:
                    # Network errors (DNS failures, connection refused, etc.)
                    attempt += 1
                    if attempt > self.max_retries:
                        error_msg = str(e)
                        if "getaddrinfo failed" in error_msg or "11002" in error_msg:
                            raise ConnectionError(
                                f"OSRM service is not reachable (DNS/network error). "
                                f"Check that {self.base_url} is accessible and the network connection is working. "
                                f"Error: {error_msg}"
                            ) from e
                        raise ConnectionError(
                            f"Failed to connect to OSRM service at {self.base_url}: {error_msg}"
                        ) from e
                    wait_time = self.backoff_seconds * (2 ** (attempt - 1))  # Exponential backoff
                    logger.debug(f"OSRM network error, retrying in {wait_time:.1f}s (attempt {attempt}/{self.max_retries}): {e}")
                    time.sleep(wait_time)
                except (httpx.HTTPError, ValueError) as error:
                    attempt += 1
                    if attempt > self.max_retries:
                        raise
                    time.sleep(self.backoff_seconds * attempt)
        finally:
            client.close()

    def _process_chunk_request(
        self,
        chunks: list[list[tuple[float, float]]],
        chunk_ranges: list[tuple[int, int]],
        src_chunk_idx: int,
        dst_chunk_idx: int,
        src_start: int,
        src_end: int,
        dst_start: int,
        dst_end: int,
    ) -> tuple[int, int, int, int, dict | None]:
        """Process a single chunk request and return the result with indices."""
        try:
            # Get coordinates for this chunk pair
            chunk_coords = chunks[src_chunk_idx] + chunks[dst_chunk_idx]
            
            # Map indices: sources are first chunk, destinations are second chunk
            src_indices = list(range(len(chunks[src_chunk_idx])))
            dst_indices = list(range(len(chunks[src_chunk_idx]), len(chunk_coords)))

            result = self._table_single_request(chunk_coords, src_indices, dst_indices)
            return (src_start, src_end, dst_start, dst_end, result)
        except Exception as e:
            logger.warning(
                f"Failed to get OSRM data for chunk [{src_start}:{src_end}] -> [{dst_start}:{dst_end}]: {e}"
            )
            return (src_start, src_end, dst_start, dst_end, None)

    def table(self, coordinates: Sequence[tuple[float, float]]) -> dict:
        """Get distance/duration matrix for coordinates, with automatic chunking and parallel requests."""
        if len(coordinates) < 2:
            raise ValueError("At least two coordinates are required for OSRM table.")

        # If coordinates fit in one request, use simple path
        if len(coordinates) <= self.max_coordinates_per_request:
            return self._table_single_request(coordinates)

        # For large coordinate lists, chunk the requests
        start_time = time.time()
        logger.info(
            f"Chunking OSRM table request: {len(coordinates)} coordinates "
            f"(max per request: {self.max_coordinates_per_request}, parallel: {self.max_parallel_requests})"
        )

        # Split coordinates into chunks
        chunk_size = self.max_coordinates_per_request
        chunks: list[list[tuple[float, float]]] = []
        chunk_ranges: list[tuple[int, int]] = []
        
        for i in range(0, len(coordinates), chunk_size):
            chunk = list(coordinates[i : i + chunk_size])
            chunks.append(chunk)
            chunk_ranges.append((i, i + len(chunk)))

        # Build full matrix by requesting chunks in parallel
        n = len(coordinates)
        durations: list[list[float | None]] = [[None] * n for _ in range(n)]
        distances: list[list[float | None]] = [[None] * n for _ in range(n)]

        total_requests = len(chunks) * len(chunks)
        logger.info(f"Making {total_requests} chunk requests in parallel (max {self.max_parallel_requests} concurrent)")

        # Prepare all chunk requests
        chunk_requests = []
        for src_chunk_idx, (src_start, src_end) in enumerate(chunk_ranges):
            for dst_chunk_idx, (dst_start, dst_end) in enumerate(chunk_ranges):
                chunk_requests.append((
                    chunks, chunk_ranges, src_chunk_idx, dst_chunk_idx,
                    src_start, src_end, dst_start, dst_end
                ))

        # Process requests in parallel
        completed = 0
        failed_chunks = 0
        network_errors = []
        
        with ThreadPoolExecutor(max_workers=self.max_parallel_requests) as executor:
            # Submit all requests
            future_to_request = {
                executor.submit(self._process_chunk_request, *req): req
                for req in chunk_requests
            }
            
            # Process completed requests as they finish
            for future in as_completed(future_to_request):
                completed += 1
                if completed % 10 == 0 or completed == total_requests:
                    logger.info(f"Progress: {completed}/{total_requests} chunk requests completed ({failed_chunks} failed)")
                
                try:
                    src_start, src_end, dst_start, dst_end, result = future.result()
                    
                    if result is None:
                        failed_chunks += 1
                        continue  # Error already logged
                    
                    # Map results back to full matrix
                    result_durations = result["durations"]
                    result_distances = result["distances"]
                    
                    # Map from local chunk indices to global indices
                    for local_src_idx, global_src_idx in enumerate(range(src_start, src_end)):
                        for local_dst_idx, global_dst_idx in enumerate(range(dst_start, dst_end)):
                            if (local_src_idx < len(result_durations) and 
                                local_dst_idx < len(result_durations[local_src_idx])):
                                durations[global_src_idx][global_dst_idx] = result_durations[local_src_idx][local_dst_idx]
                                distances[global_src_idx][global_dst_idx] = result_distances[local_src_idx][local_dst_idx]
                except Exception as e:
                    failed_chunks += 1
                    error_msg = str(e)
                    if "getaddrinfo failed" in error_msg or "11002" in error_msg or "Connection" in str(type(e)):
                        network_errors.append(error_msg)
                    logger.error(f"Error processing chunk result: {e}")

        elapsed = time.time() - start_time
        
        # Check if we have too many failures
        failure_rate = failed_chunks / total_requests if total_requests > 0 else 1.0
        critical_failure_threshold = 0.5  # If more than 50% of chunks fail, it's critical
        
        if network_errors:
            # If we have network errors, check if it's a systemic issue
            unique_network_errors = set(network_errors)
            if len(unique_network_errors) > 0:
                logger.error(
                    f"Network errors detected in {len(network_errors)} chunk requests. "
                    f"OSRM service may be unreachable. Errors: {unique_network_errors}"
                )
        
        if failure_rate > critical_failure_threshold:
            error_msg = (
                f"Critical failure: {failed_chunks}/{total_requests} chunk requests failed ({failure_rate*100:.1f}%). "
                f"This suggests OSRM service is unavailable or experiencing issues. "
            )
            if network_errors:
                error_msg += f"Network errors detected: {set(network_errors)}. "
            error_msg += "Please check OSRM connectivity and try again."
            raise ConnectionError(error_msg)
        elif failed_chunks > 0:
            logger.warning(
                f"Partial failure: {failed_chunks}/{total_requests} chunk requests failed. "
                f"Some routes may be marked as unreachable. "
                f"Elapsed time: {elapsed:.2f}s"
            )
        else:
            logger.info(
                f"Completed OSRM table request: {total_requests} chunk requests in {elapsed:.2f}s "
                f"({total_requests/elapsed:.1f} requests/sec)"
            )

        return {
            "durations": durations,
            "distances": distances,
        }

    def route(self, coordinates: Sequence[tuple[float, float]]) -> dict:
        """Get route geometry between coordinates using OSRM route endpoint.
        
        Returns the route path that follows streets, including geometry as polyline.
        
        Args:
            coordinates: Sequence of (lat, lon) tuples for the route waypoints
            
        Returns:
            Dictionary with route information including 'geometry' (polyline) and 'routes'
        """
        if len(coordinates) < 2:
            raise ValueError("At least two coordinates are required for OSRM route.")
        
        # OSRM route endpoint expects coordinates as "lon,lat;lon,lat;..."
        coordinate_str = ";".join(f"{lon},{lat}" for lat, lon in coordinates)
        
        params = {
            "overview": "full",  # Get full geometry
            "geometries": "polyline",  # Use polyline encoding
            "steps": "false",  # Don't need step-by-step instructions
        }
        url = f"{self.base_url}/route/v1/{self.profile}/{coordinate_str}"
        
        client = self._get_client()
        try:
            attempt = 0
            while True:
                try:
                    response = client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get("code") != "Ok":
                        error_msg = data.get("message", "Unknown OSRM route error")
                        raise ValueError(f"OSRM route request failed: {error_msg}")
                    
                    return data
                except httpx.HTTPStatusError as e:
                    attempt += 1
                    if attempt > self.max_retries:
                        raise
                    time.sleep(self.backoff_seconds * attempt)
                except (httpx.TimeoutException, httpx.ReadTimeout) as e:
                    attempt += 1
                    if attempt > self.max_retries:
                        logger.warning(f"OSRM route request timed out after {self.max_retries} attempts: {e}")
                        raise
                    wait_time = self.backoff_seconds * (2 ** (attempt - 1))
                    logger.debug(f"OSRM route timeout, retrying in {wait_time:.1f}s (attempt {attempt}/{self.max_retries})")
                    time.sleep(wait_time)
                except (httpx.ConnectError, httpx.NetworkError, OSError) as e:
                    attempt += 1
                    if attempt > self.max_retries:
                        error_msg = str(e)
                        raise ConnectionError(
                            f"Failed to connect to OSRM service at {self.base_url}: {error_msg}"
                        ) from e
                    wait_time = self.backoff_seconds * (2 ** (attempt - 1))
                    logger.debug(f"OSRM network error, retrying in {wait_time:.1f}s (attempt {attempt}/{self.max_retries}): {e}")
                    time.sleep(wait_time)
                except (httpx.HTTPError, ValueError) as error:
                    attempt += 1
                    if attempt > self.max_retries:
                        raise
                    time.sleep(self.backoff_seconds * attempt)
        finally:
            client.close()


def decode_polyline(polyline: str) -> list[tuple[float, float]]:
    """Decode Google polyline string to list of (lat, lon) coordinates.
    
    OSRM uses Google's polyline encoding format for route geometry.
    
    Args:
        polyline: Encoded polyline string
        
    Returns:
        List of (latitude, longitude) tuples
    """
    coordinates = []
    index = 0
    lat = 0
    lon = 0
    
    while index < len(polyline):
        # Decode latitude
        shift = 0
        result = 0
        while True:
            b = ord(polyline[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += dlat
        
        # Decode longitude
        shift = 0
        result = 0
        while True:
            b = ord(polyline[index]) - 63
            index += 1
            result |= (b & 0x1f) << shift
            shift += 5
            if b < 0x20:
                break
        dlon = ~(result >> 1) if (result & 1) else (result >> 1)
        lon += dlon
        
        coordinates.append((lat / 1e5, lon / 1e5))
    
    return coordinates


def build_coordinate_list(
    depot_lat: float, 
    depot_lon: float, 
    customers: Sequence[tuple[float, float]],
    start_from_depot: bool = True,
) -> list[tuple[float, float]]:
    """Build coordinate list for OSRM requests.
    
    Args:
        depot_lat: Depot latitude
        depot_lon: Depot longitude
        customers: Sequence of (lat, lon) tuples for customers
        start_from_depot: If True, prepend depot to the list. If False, return only customers.
    
    Returns:
        List of (lat, lon) tuples. If start_from_depot=True: [depot, *customers], 
        otherwise: [*customers]
    """
    if start_from_depot:
        return [(depot_lat, depot_lon), *customers]
    else:
        return list(customers)


def check_health(base_url: str | None = None) -> bool:
    """Check OSRM service health by making a simple table request.
    
    Public OSRM endpoints may not have a /health endpoint, so we test
    connectivity by making a minimal table request with two coordinates.
    """
    base = base_url or settings.osrm_base_url
    if not base:
        return False
    try:
        # Use a simple test with two coordinates (Berlin area)
        # This works with both public and self-hosted OSRM instances
        test_coords = "13.388860,52.517037;13.385983,52.496891"
        profile = settings.osrm_profile
        url = f"{base}/table/v1/{profile}/{test_coords}"
        params = {"annotations": "duration"}
        
        response = httpx.get(url, params=params, timeout=5.0)
        response.raise_for_status()
        data = response.json()
        # Check if we got a valid response with durations
        return "durations" in data and isinstance(data.get("durations"), list)
    except httpx.HTTPError:
        return False
    except Exception:
        # Catch any other errors (JSON parsing, etc.)
        return False
