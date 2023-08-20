# imports
from os import path
import configparser
import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime

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
        writer.writerow(('Title', 'Year', 'Rating10'))


# write to previously created csv file
def write_to_csv(user, movie):
    csv_path = path.join(path.dirname(path.realpath(__file__)), str(user) + '.csv')
    with open(csv_path, 'a', encoding='UTF-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow((
          movie['title'],
          movie['year'],
          movie['rating']
        ))


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
    movieslist = document.find_all("td", {"class": "plain-list-movie"})
    for current_movie in movieslist:
        new_movie = {'title': None, 'director': None, 'year': None, 'rating': None}
        new_movie['title'] = current_movie.find("a").get_text(strip=True)
        date = current_movie.find_all("span", {"class": "production_info"})
        for d in date:
            chunk = d.get_text()
            date = [int(s) for s in chunk.split() if s.isdigit()]
            new_movie['year'] = date[0]
        new_movie['rating'] = current_movie.find_next_sibling().get_text(strip=True)
        write_to_csv(user, new_movie)


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
