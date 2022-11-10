import argparse
from datetime import datetime
import json
import os
import re
import time

from urllib.request import urlopen
from urllib.error import HTTPError
import bs4
import pandas as pd


# def get_all_lists(soup):

#     lists = []
#     list_count_dict = {}

#     if soup.find('a', text='More lists with this book...'):

#         lists_url = soup.find('a', text='More lists with this book...')['href']

#         source = urlopen('https://www.goodreads.com' + lists_url)
#         soup = bs4.BeautifulSoup(source, 'lxml')
#         lists += [' '.join(node.text.strip().split()) for node in soup.find_all('div', {'class': 'cell'})]

#         i = 0
#         while soup.find('a', {'class': 'next_page'}) and i <= 10:

#             time.sleep(2)
#             next_url = 'https://www.goodreads.com' + soup.find('a', {'class': 'next_page'})['href']
#             source = urlopen(next_url)
#             soup = bs4.BeautifulSoup(source, 'lxml')

#             lists += [node.text for node in soup.find_all('div', {'class': 'cell'})]
#             i += 1

#         # Format lists text.
#         for _list in lists:
#             _list_name = _list.split()[:-2][0]
#             _list_count = int(_list.split()[-2].replace(',', ''))
#             list_count_dict[_list_name] = _list_count

#     return list_count_dict


# def get_shelves(soup):

#     shelf_count_dict = {}
    
#     if soup.find('a', text='See top shelves…'):

#         # Find shelves text.
#         shelves_url = soup.find('a', text='See top shelves…')['href']
#         source = urlopen('https://www.goodreads.com' + shelves_url)
#         soup = bs4.BeautifulSoup(source, 'lxml')
#         shelves = [' '.join(node.text.strip().split()) for node in soup.find_all('div', {'class': 'shelfStat'})]
        
#         # Format shelves text.
#         shelf_count_dict = {}
#         for _shelf in shelves:
#             _shelf_name = _shelf.split()[:-2][0]
#             _shelf_count = int(_shelf.split()[-2].replace(',', ''))
#             shelf_count_dict[_shelf_name] = _shelf_count

#     return shelf_count_dict


def get_description(soup):
    all_descriptions = soup.find('div',attrs={'id': 'description'})
    if not(all_descriptions):
        return ''
    elif len(all_descriptions.select('span'))>1:
        return all_descriptions.select('span')[1].text
    return all_descriptions.select('span')[0].text

def get_genres(soup):
    genres = []
    for node in soup.find_all('div', {'class': 'left'}):
        current_genres = node.find_all('a', {'class': 'actionLinkLite bookPageGenreLink'})
        current_genre = ' > '.join([g.text for g in current_genres])
        if current_genre.strip():
            genres.append(current_genre)
    return genres


def get_series_name(soup):
    series = soup.find(id="bookSeries").find("a")
    if series:
        series_name = re.search(r'\((.*?)\)', series.text).group(1)
        return series_name
    else:
        return ""


def get_series_uri(soup):
    series = soup.find(id="bookSeries").find("a")
    if series:
        series_uri = series.get("href")
        return series_uri
    else:
        return ""

def get_top_5_other_editions(soup):
    other_editions = []
    for div in soup.findAll('div', {'class': 'otherEdition'}):
      other_editions.append(div.find('a')['href'])
    return other_editions

def get_isbn(soup):
    try:
        isbn = re.findall(r'nisbn: [0-9]{10}' , str(soup))[0].split()[1]
        return isbn
    except:
        return "isbn not found"

def get_isbn13(soup):
    try:
        isbn13 = re.findall(r'nisbn13: [0-9]{13}' , str(soup))[0].split()[1]
        return isbn13
    except:
        return "isbn13 not found"


def get_rating_distribution(soup):
    distribution = re.findall(r'renderRatingGraph\([\s]*\[[0-9,\s]+', str(soup))[0]
    distribution = ' '.join(distribution.split())
    distribution = [int(c.strip()) for c in distribution.split('[')[1].split(',')]
    distribution_dict = {'5 Stars': distribution[0],
                         '4 Stars': distribution[1],
                         '3 Stars': distribution[2],
                         '2 Stars': distribution[3],
                         '1 Star':  distribution[4]}
    return distribution_dict


def get_num_pages(soup):
    if soup.find('span', {'itemprop': 'numberOfPages'}):
        num_pages = soup.find('span', {'itemprop': 'numberOfPages'}).text.strip()
        return int(num_pages.split()[0])
    return ''


def get_year_first_published(soup):
    year_first_published = soup.find('nobr', attrs={'class':'greyText'})
    if year_first_published:
        year_first_published = year_first_published.string
        return re.search('([0-9]{3,4})', year_first_published).group(1)
    else:
        return ''

def get_id(url):
    # Complete
    if url.startswith('https://www.goodreads.com/search/?q='):
        return ''
    pattern = re.compile("\/(\d+).")
    return pattern.search(url).group(1)
    
def scrape_book(isbn,book_id):
    if isbn: # BX dataset only has ISBN. Most of the GR dataset also, but some... do not.
        url = 'https://www.goodreads.com/search/?q='+isbn
        
    elif book_id: # GR dataset items missing ISBN
        url = 'https://www.goodreads.com/book/show/' + book_id

    source = urlopen(url)
    soup = bs4.BeautifulSoup(source, 'html.parser')
    time.sleep(3)

    if soup.find('h1', {'id': 'bookTitle'}):
        return {'book_id':              get_id(source.url),
                'book_title':           ' '.join(soup.find('h1', {'id': 'bookTitle'}).text.split()),
                "book_series":          get_series_name(soup),
                "book_series_uri":      get_series_uri(soup),
                'top_5_other_editions': get_top_5_other_editions(soup),
                'isbn':                 get_isbn(soup),
                'isbn13':               get_isbn13(soup),
                'year_first_published': get_year_first_published(soup),
                'authorlink':           soup.find('a', {'class': 'authorName'})['href'],
                'author':               ' '.join(soup.find('span', {'itemprop': 'name'}).text.split()),
                'num_pages':            get_num_pages(soup),
                'description':          get_description(soup),
                'genres':               get_genres(soup),
                # 'shelves':              get_shelves(soup),
                # 'lists':                get_all_lists(soup),
                'num_ratings':          soup.find('meta', {'itemprop': 'ratingCount'})['content'].strip(),
                'num_reviews':          soup.find('meta', {'itemprop': 'reviewCount'})['content'].strip(),
                'average_rating':       soup.find('span', {'itemprop': 'ratingValue'}).text.strip(),
                'rating_distribution':  get_rating_distribution(soup)}
    else:
        return ''

def condense_books(books_directory_path):

    books = []
    
    # Look for all the files in the directory and if they contain "book-metadata," then load them all and condense them into a single file
    for file_name in os.listdir(books_directory_path):
        if file_name.endswith('.json') and not file_name.startswith('.') and file_name != "all_books.json" and "book-metadata" in file_name:
            _book = json.load(open(books_directory_path + '/' + file_name, 'r')) #, encoding='utf-8', errors='ignore'))
            books.append(_book)

    return books

def main():

    start_time = datetime.now()
    script_name = os.path.basename(__file__)

    parser = argparse.ArgumentParser()
    parser.add_argument('--output_directory_path', type=str)
    parser.add_argument('--format', type=str, action="store", default="json",
                        dest="format", choices=["json", "csv"],
                        help="set file output format")
    args = parser.parse_args()

    df_books = pd.read_csv('books_final.csv')

    book_ids              = df_books[['ISBN','book_id']].values
    books_already_scraped =  [file_name.replace('_book-metadata.json', '').split('-')[0] for file_name in os.listdir(args.output_directory_path) if file_name.endswith('.json') and not file_name.startswith('all_books')]
    books_to_scrape       = [[isbn, book_id] for isbn, book_id in book_ids if isbn not in books_already_scraped]
    condensed_books_path   = args.output_directory_path + '/all_books'

    for i, bid in enumerate(books_to_scrape):
        try:
            isbn, book_id = bid
            print(str(datetime.now()) + ' ' + script_name + ': Scraping isbn:' + str(isbn) + ' book_id:' + str(book_id) + '...')
            print(str(datetime.now()) + ' ' + script_name + ': #' + str(i+1+len(books_already_scraped)) + ' out of ' + str(len(book_ids)) + ' books')

            book = scrape_book(isbn, book_id)

            if book != '':
                if book['isbn']=='isbn not found':
                    print('isbn not found')
            
            # Add book metadata to file name to be more specific
            filename = args.output_directory_path + '/' + str(isbn) + '-' + str(book_id) + '_book-metadata.json'
            json.dump(book, open(filename,'w'))

            print('=============================')

        except HTTPError as e:
            print(e)
            exit(0)


    books = condense_books(args.output_directory_path)
    if args.format == 'json':
        json.dump(books, open(f"{condensed_books_path}.json", 'w'))
    elif args.format == 'csv':
        json.dump(books, open(f"{condensed_books_path}.json", 'w'))
        book_df = pd.read_json(f"{condensed_books_path}.json")
        book_df.to_csv(f"{condensed_books_path}.csv", index=False, encoding='utf-8')
        
    print(str(datetime.now()) + ' ' + script_name + f':\n\n🎉 Success! All book metadata scraped. 🎉\n\nMetadata files have been output to /{args.output_directory_path}\nGoodreads scraping run time = ⏰ ' + str(datetime.now() - start_time) + ' ⏰')



if __name__ == '__main__':
    main()
