"""
2023-07-23
Script to compile and organize concerts for various performers.
"""
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
            locations[i] = loc.title()
            if locations[i] in ["Usa", "U.S.", "US", "U.S.A.", "United States"]:
                locations[i] = "USA"
            elif locations[i] in ["Uk", "UK", "U.K."]:
                locations[i] = "United Kingdom"


def get_inputs():
    """
    Get user inputs
    """
    artist_names = [
        name.strip()
        for name in str(
            input(
                "Input the name(s) of the performer(s) you'd like to see, separated by commas. \
            (Hint: check that your artist(s) appear as on-tour on either \
            https://www.deutschegrammophon.com/en/artists/a-z/a or \
            https://www.deccaclassics.com/en/artists/a-z/a.)",
                type=TEXT,
            )
        ).split(",")
    ]
    input_locations = [
        loc.strip()
        for loc in str(
            input(
                "Input the desired concert location(s), e.g., city name(s) (without the state) \
            or country name(s) (e.g., USA, United Kingdom), separated by commas.\
            Or type ANY if no preference. It may take up to ~4 seconds per performer \
            to generate your results.",
                type=TEXT,
            )
        ).split(",")
    ]
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


def update_for_artist(all_concerts, query):
    """
    Update unsorted list of concerts for individual performer
    """
    for search_result in search(query, tld="co.in", num=10, stop=10, pause=2):
        if (
            "deutschegrammophon.com" in search_result
            or "deccaclassics.com" in search_result
        ):
            website = search_result
            break

    content = requests.get(website, timeout=5).text
    pretty_soup = BeautifulSoup(content, "lxml").prettify()
    if "Tour Dates" not in pretty_soup:  # performer does not appear on-tour on website
        return

    events = pretty_soup.split("MusicEvent")[1:]
    events[-1] = events[-1].split('"performer":')[0]

    for event in events:
        concert = {}
        date = event.split('"startDate":"')[1].split("T00:00:00")[0]
        venue_name = event.split('"@type":"Place","name":"')[1].split('","address":')[0]
        piece = pretty_soup.split(venue_name)[-1].split("\n")[4].strip()
        address = event.split('"address":"')[1].split('"},"offers":')[0]
        ticket_site = event.split('"@type":"Offer","url":"')[1].split(
            '","availability":"'
        )[0]
        image_url = event.split('"ImageObject","url":"')[1].split('","headline":"')[0]
        concert["performer"] = query.split("concerts")[0].strip().title()
        concert["date"] = date
        concert["piece"] = piece
        concert["venue_name"] = venue_name
        concert["address"] = address
        concert["ticket_site"] = ticket_site
        concert["image_url"] = image_url
        all_concerts.append(concert)


def get_all_concerts():
    """
    Get unsorted list of all concerts, regardless of location.
    Returns list of concerts and list of preferred location(s).
    """
    artist_names, input_locations = get_inputs()
    with put_loading():
        queries = [f"{name} concerts" for name in artist_names]
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
