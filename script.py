# imports
from os import path
import configparser
import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime
import html

BASE_URL = "https://www.moviepilot.de"
LOGIN_URL = BASE_URL + "/login?next="
SESSION_POST_URL = BASE_URL + "/api/session"
SEARCH_URI = BASE_URL + "/users/%s/rated/movies?page=%d"


# load config
def get_config():
    config = configparser.ConfigParser()
    config_path = path.join(path.dirname(path.realpath(__file__)), 'config.ini')
    config.read(config_path)    
    return {
        'username': config['login']['username'],
        'password': config['login']['password'],
        'userToParse': config['config']['userToParse']
    }


# create a csv file
def create_csv(user):
    csv_path = path.join(path.dirname(path.realpath(__file__)), str(user) + '.csv')
    with open(csv_path, 'w', encoding='UTF-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(('Title (German)', 'Title (original)', 'Year', 'Rating10', 'IMDb ID'))


# write to previously created csv file
def write_to_csv(user, movie):
    csv_path = path.join(path.dirname(path.realpath(__file__)), str(user) + '.csv')
    with open(csv_path, 'a', encoding='UTF-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow((
            movie['title_german'],
            movie['title_original'],
            movie['year'],
            movie['rating'],
            movie['imdb_id']
        ))


def get_title_original_imdb_id_year(movie_url):
    full_movie_url = BASE_URL + movie_url
    data = requests.get(full_movie_url)
    data_string = str(data.content)

    # year
    year_attribute = '"productionYear":"'
    year_position = data_string.find(year_attribute)
    year_start = year_position + len(year_attribute)
    year_end = data_string.find('"', year_start)
    year = data_string[year_start:year_end]

    # original title
    title_orig_attribute = '"originalTitle":"'
    title_orig_position = data_string.find(title_orig_attribute)
    title_orig_start = title_orig_position + len(title_orig_attribute)
    title_orig_end = data_string.find('"', title_orig_start)
    title_orig = data_string[title_orig_start:title_orig_end]
    # interpret escape sequences
    title_orig = title_orig.encode().decode('unicode-escape').encode('latin1').decode('utf-8')
    title_orig = html.unescape(title_orig)

    # IMDb ID
    imdb_id_attribute = '"imdbId":"'
    imdb_id_position = data_string.find(imdb_id_attribute)
    imdb_id_length = 9
    imdb_id_start = imdb_id_position + len(imdb_id_attribute)
    imdb_id_end = imdb_id_start + imdb_id_length
    imdb_id = data_string[imdb_id_start:imdb_id_end]

    return title_orig, imdb_id, year


# request movies pages for selected user as long there are movies to export
def get_movies(request, user):
    i = 1 
   
    while request.get(SEARCH_URI % (user, i)):
        search_document = request.get(SEARCH_URI % (user, i))
        print("reading: "+SEARCH_URI % (user, i))
        i += 1
        document = BeautifulSoup(search_document.content, 'html.parser')
        scrape_movielist_and_write_to_csv(user, document)
        if not document.find_all("div", {"class": "movie"}):
            # no more movies to export
            break


# find movie infos and write them to csv file
def scrape_movielist_and_write_to_csv(user, document):
    user_short = user[0:7] + "..."
    ratings = []

    ratings_list = document.find_all("div", {"class": "heat_buttons rating"})
    for current_rating in ratings_list:
        current_rating_2 = current_rating.find("span", {"class", "very-small"})
        if current_rating_2:
            content = current_rating_2.contents[0].get_text()
            if (content == user) or (content == user_short):
                ratings.append(current_rating_2.find_next_sibling().get_text(strip=True))

    movies_list = document.find_all("div", {"class": "movie"})

    movies_on_this_page = 0
    for current_movie in movies_list:
        current_movie_2 = current_movie.find("a", {"data-item-type", True})
        if current_movie_2:
            new_movie = {
                'title_german': None,
                'title_original': None,
                'director': None,
                'year': None,
                'rating': None,
                'imdb_id': None
            }
            movie_url = current_movie.a["href"]
            new_movie['title_german'] = current_movie_2.attrs['title']
            title_original, imdb_id, year = get_title_original_imdb_id_year(movie_url)
            new_movie['title_original'] = title_original
            new_movie['imdb_id'] = imdb_id
            new_movie['year'] = year
            new_movie['rating'] = ratings[movies_on_this_page]
            write_to_csv(user, new_movie)
            movies_on_this_page += 1
    print("    number of movies on this page: " + str(movies_on_this_page))


# get moviepilot login
def get_mp_login():
    login = input("Moviepilot login: ")
    return login


# get moviepilot password
def get_mp_password():
    password = input("Moviepilot password: ")
    return password


# create a moviepilot session with given credentials
def login_to_moviepilot(u, p):
    # request session request
    session = requests.session()

    # request login url
    session.get(LOGIN_URL)

    username = u if len(u) > 0 else get_mp_login()
    password = p if len(p) > 0 else get_mp_password()
    
    # create session request payload
    payload = {
        "username": username, 
        "password": password
    }

    # perform login
    session.post(SESSION_POST_URL, data=payload)
    return session


def get_user():
    user = input("Enter the moviepilot username you want to export filmratings for: ")
    print("Search will be done on the user: " + user +
          ". Your csv will be saved in the current directory under the name: "+user+".csv")
    
    return user.lower().strip()


def main():
    # start time measurement
    start_time = datetime.now()

    # get config from file
    config = get_config()
    
    # login
    session = login_to_moviepilot(config['username'], config['password'])

    # get user to export movielist for
    user = config['userToParse'].lower() if len(config['userToParse']) > 0 else get_user()

    # prepare csv for user
    create_csv(user)
    
    # scrape search URL website and write to csv add additional amount of maxpages
    get_movies(session, user)

    # end and print time measurement
    print("Time consumption: " + str(datetime.now() - start_time))


if __name__ == "__main__":
    main()
