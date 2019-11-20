import pickle
import sys
import webbrowser
from contextlib import contextmanager
from pathlib import Path

import click

from .api import address_search, get_route_url, get_gmaps_nav_url, refine_address_coordinates


ADDRESS_CACHE_PATH = Path(__file__).parent / "address-cache.pkl"


@click.command()
@click.argument("start")
@click.argument("goal")
@click.option("-s", "--skip-cache", is_flag=True)
@click.option("-o", "--open-browser", is_flag=True)
@click.option("-g", "--google-maps", is_flag=True)
def find_bicycle_route(start, goal, skip_cache, open_browser, google_maps):
    start_address = get_cache(start) if not skip_cache else None
    if start_address is None:
        start_candidates = address_search(start)
        start_address = address_choice(start_candidates, "Choose a starting address:")
        refine_address_coordinates(start_address)
        save_cache(start, start_address)

    goal_address = get_cache(goal) if not skip_cache else None
    if goal_address is None:
        goal_candidates = address_search(goal)
        goal_address = address_choice(goal_candidates, "Choose a destination address:")
        refine_address_coordinates(goal_address)
        save_cache(goal, goal_address)

    if google_maps:
        route_url = get_gmaps_nav_url(start_address, goal_address)
    else:
        route_url = get_route_url(start_address, goal_address)

    print(f"Route from {start_address.name} to {goal_address.name}...")
    if open_browser:
        webbrowser.open(route_url)
    else:
        print(route_url)


@click.command()
@click.argument("query")
@click.option("-n", "--name", type=str, default=None)
def save_address(query, name):
    candidates = address_search(query)
    address = address_choice(candidates, "Choose an address:")
    refine_address_coordinates(address)
    save_cache(query, address)
    if name is not None:
        save_cache(name, address)


def address_choice(candidates, desc):
    if not candidates:
        print("Address not found :(")
        sys.exit(1)
    if len(candidates) == 1:
        return candidates[0]
    print(desc)
    for i, candidate in enumerate(candidates):
        print(f"[{i}] {candidate.name}")
    while True:
        try:
            idx = int(input("Chosen index: ").strip())
            return candidates[idx]
        except (ValueError, IndexError):
            print("Please enter a valid index")


@contextmanager
def loaded_cache(readonly=False):
    try:
        with open(ADDRESS_CACHE_PATH, "rb") as f:
            cache = pickle.load(f)
    except OSError:
        cache = {}
    yield cache
    if not readonly:
        with open(ADDRESS_CACHE_PATH, "wb") as f:
            pickle.dump(cache, f)


def get_cache(query):
    with loaded_cache(readonly=True) as cache:
        return cache.get(query)


def save_cache(query, address):
    with loaded_cache() as cache:
        cache[query] = address
