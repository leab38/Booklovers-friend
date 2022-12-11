import argparse
from datetime import datetime
import json
import os
import re
import requests
import time

from urllib.request import urlopen
from urllib.error import HTTPError
import bs4
import pandas as pd
def get_id(json):
    return json['items'][0]['id']

def get_volume_info(volume_info, key):
    if key in volume_info.keys():
        return volume_info[key]
    
    else:
        return None

def get_thumbnail(imageLinks, type):
    if imageLinks and (type in imageLinks.keys()):
        return imageLinks[type]
    
    else:
        return None

def scrape_book(isbn):
    if isbn: # BX dataset only has ISBN. Most of the GR dataset also, but some... do not.
        url = 'https://www.googleapis.com/books/v1/volumes'
    else:
        return ''
        
    response = requests.get(url, params={"q": 'isbn:'+isbn})
    json = response.json()
    time.sleep(3)

    try: 
        if json['totalItems']!=0 and 'volumeInfo' in json['items'][0].keys():
            volume_info = json['items'][0]['volumeInfo']
            return {'goog_id':              get_id(json),
                    'book_title':           get_volume_info(volume_info,'title'),
                    'book_link':            get_volume_info(volume_info, 'infoLink'),
                    'isbn':                 isbn,
                    'year_first_published': get_volume_info(volume_info,'publishedDate'),
                    'publisher':            get_volume_info(volume_info,'publisher'),
                    'author':               get_volume_info(volume_info,'authors'),
                    'num_pages':            get_volume_info(volume_info,'pageCount'),
                    'description':          get_volume_info(volume_info,'description'),
                    'genres':               get_volume_info(volume_info,'categories'),
                    'num_ratings':          get_volume_info(volume_info,'ratingsCount'),
                    'average_rating':       get_volume_info(volume_info,'averageRating'),
                    'image-S':              get_thumbnail(get_volume_info(volume_info,'imageLinks'),'smallThumbnail'),
                    'image':                get_thumbnail(get_volume_info(volume_info,'imageLinks'),'thumbnail'),
                    'language':             get_volume_info(volume_info,'language')}
        else:
            return ''

    except KeyError as e:
        print(e, isbn)
        exit(0)    

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
    parser.add_argument('--filename', type=str)
    args = parser.parse_args()

    df_books = pd.read_csv(args.filename, encoding='unicode-escape')

    book_ids              = df_books['isbn'].apply(lambda x: x.strip().upper().zfill(10)).values
    books_already_scraped =  [file_name.replace('_book-metadata.json', '').split('-')[0].upper() for file_name in os.listdir(args.output_directory_path) if file_name.endswith('.json') and not file_name.startswith('all_books')]
    books_to_scrape       = [isbn.upper() for isbn in book_ids if isbn.upper() not in books_already_scraped]
    condensed_books_path   = args.output_directory_path + '/all_books'

    for i, isbn in enumerate(books_to_scrape):
        try:
            print(str(datetime.now()) + ' ' + script_name + ': getting isbn:' + str(isbn) + '...')
            print(str(datetime.now()) + ' ' + script_name + ': #' + str(i+1+len(books_already_scraped)) + ' out of ' + str(len(book_ids)) + ' books')

            book = scrape_book(isbn)
            
            # Add book metadata to file name to be more specific
            filename = args.output_directory_path + '/' + str(isbn).upper() + '-' + '_book-metadata.json'
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
