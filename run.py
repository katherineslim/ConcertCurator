"""
2023-07-23
Script to compile and organize concerts for various performers.
"""
import re
import requests
from bs4 import BeautifulSoup
from googlesearch import search
from pywebio import start_server
from pywebio.input import input, TEXT
from pywebio.output import put_text, put_markdown, put_loading


def correct_locations(locations):
    """
    Correct location capitalization and alternative country names.
    """
    for i, loc in enumerate(locations):
        if loc != "USA":
            if "d'" not in loc:
                locations[i] = loc.title()
            if locations[i] in ["Usa", "U.S.", "US", "U.S.A.", "United States"]:
                locations[i] = "USA"
            elif locations[i] in ["Uk", "UK", "U.K."]:
                locations[i] = "United Kingdom"


def get_list_from_input(input_string):
    """
    Parse input into a list of strings
    """
    return [elt.strip() for elt in str(input_string).split(",")]


def check_artists(input_names):
    """
    Validate artist names
    """
    for name in get_list_from_input(input_names):
        if not concerts_on_website(get_pretty_soup(get_website(querify_name(name)))):
            return f"'{name}' was not found on-tour on \
                https://www.deutschegrammophon.com or https://www.deccaclassics.com"
    return None


def get_inputs():
    """
    Get user inputs
    """
    artist_names = get_list_from_input(
        input(
            "Input the name(s) of the performer(s) you'd like to see, separated by commas.",
            type=TEXT,
            help_text="(Hint: Check that your artist(s) appear as on-tour on either \
                https://www.deutschegrammophon.com/en/artists/a-z/a or \
                https://www.deccaclassics.com/en/artists/a-z/a.)",
            # validate=check_artists,
        )
    )
    input_locations = get_list_from_input(
        input(
            "Input the desired concert location(s), e.g., city name(s) and/or country name(s), \
                separated by commas. Type ANY if no preference.",
            type=TEXT,
            help_text="City examples: Paris, Buenos Aires, Zürich. \
                        Country examples: USA, United Kingdom, Germany. \
                        Make sure spelling(s) are correct, including any special characters. \
                        It may take up to ~4 seconds per performer to generate your results.",
        )
    )
    correct_locations(input_locations)

    return artist_names, input_locations


def sort_concerts(all_concerts, input_locations):
    """
    Sort concerts by date and location.
    """
    all_concerts.sort(key=lambda concert: concert["date"])
    if input_locations not in (["Any"], [""]):
        concerts_near_me = [
            concert
            for concert in all_concerts
            if any(location in concert["address"] for location in input_locations)
        ]
    else:
        concerts_near_me = all_concerts

    return concerts_near_me


def print_output(concerts_near_me):
    """
    Print results
    """
    if not concerts_near_me:
        put_text("No matching concerts found.")
    else:
        put_markdown("# **Upcoming concerts**")

    for concert in concerts_near_me:
        put_markdown(f'## **{concert["date"]}**')
        put_markdown(f'**{concert["performer"]}**')
        if concert["piece"] != "</div>":
            put_markdown(f'*{concert["piece"]}*')
        put_text(concert["venue_name"])
        put_text(concert["address"])
        put_markdown(f'Tickets: {concert["ticket_site"]}')
        put_text("\n")


def get_website(query):
    """
    Get record label website that matches the query
    Returns None if matching website not found
    """
    for search_result in search(query, tld="co.in", num=10, stop=10, pause=2):
        if (
            "deutschegrammophon.com" in search_result
            or "deccaclassics.com" in search_result
        ):
            website = search_result
            return website
    return None


def get_pretty_soup(website):
    """
    Get website content
    """
    content = requests.get(website, timeout=5).text
    pretty_soup = BeautifulSoup(content, "lxml").prettify()
    return pretty_soup


def concerts_on_website(pretty_soup):
    """
    Check whether website displays upcoming concerts
    """
    if "Tour Dates" not in pretty_soup:
        return False
    return True


def update_for_artist(all_concerts, query):
    """
    Update unsorted list of concerts for individual performer
    """
    website = get_website(query)
    pretty_soup = get_pretty_soup(website)
    if not concerts_on_website(pretty_soup):
        return

    events = pretty_soup.split("MusicEvent")[1:]
    events[-1] = events[-1].split('"performer":')[0]

    for event in events:
        concert = {}
        performer = pretty_soup.split("Tour Dates - ")[1].split(" in Concert")[0]
        date = re.split("T..:..:..", event.split('"startDate":"')[1])[0]
        venue_name = event.split('"@type":"Place","name":"')[1].split('","address":')[0]
        piece = pretty_soup.split(venue_name)[-1].split("\n")[4].strip()
        address = event.split('"address":"')[1].split('"},"offers":')[0]
        ticket_site = event.split('"@type":"Offer","url":"')[1].split(
            '","availability":"'
        )[0]
        image_url = event.split('"ImageObject","url":"')[1].split('","headline":"')[0]
        concert["performer"] = performer
        concert["date"] = date
        concert["piece"] = piece
        concert["venue_name"] = venue_name
        concert["address"] = address
        concert["ticket_site"] = ticket_site
        concert["image_url"] = image_url
        all_concerts.append(concert)


def querify_name(name):
    """
    Turn name into query for concerts
    """
    return f"{name} concerts"


def get_all_concerts():
    """
    Get unsorted list of all concerts, regardless of location.
    Returns list of concerts and list of preferred location(s).
    """
    artist_names, input_locations = get_inputs()
    with put_loading():
        queries = [querify_name(name) for name in artist_names]
        all_concerts = []

        for query in queries:
            update_for_artist(all_concerts, query)

        return all_concerts, input_locations


def get_concerts():
    """
    ConcertCurator:
    Get list of upcoming concerts, sorted by date.
    """
    all_concerts, input_locations = get_all_concerts()
    with put_loading():
        concerts_near_me = sort_concerts(all_concerts, input_locations)
    print_output(concerts_near_me)


if __name__ == "__main__":
    start_server(get_concerts, port=80)
