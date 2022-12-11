import argparse
from data_prep import config
from datetime import datetime
from difflib import diff_bytes
from xml.sax import default_parser_list
import joblib
import os
import pandas as pd
import re
import requests
from sklearn.feature_extraction import DictVectorizer
from sklearn.neighbors import NearestNeighbors
import sqlalchemy as sa
import psycopg2
import wget
from zipfile import ZipFile



def titlecase(string):
    regex = re.compile("[a-z]+('[a-z]+)?",re.I)
    return regex.sub(lambda grp: grp.group(0)[0].upper()+grp.group(0)[1:].lower(),string)

def get_author_from_GB(isbn_list):
    ''' Gets author from the Google Books API
        Args: isbn_list (list of ISBNs to be searched)
        Returns: author_list (list of authors to be updated in book data frame)
    '''
    url = "https://www.googleapis.com/books/v1/volumes"
    google_dict = dict()
    author_list = []
    for isbn in isbn_list:
        response = requests.get(url, params={"q": 'isbn:'+isbn})
        json = response.json()
        
        try:
            if json['totalItems']!=0: # title does not exist in Google Books API
                volume_info = json['items'][0]['volumeInfo']
                author_list.append(','.join(volume_info['authors']))
            else:
                author_list.append('')
        except KeyError as k:
            print(k,isbn)
            exit(0)

    return author_list

def merge_books():
    ''' Import and merge the datasets from the Goodreads (gr) and Book Crossing (bx) datasets
        Args: None
        Return: df_books (Pandas Data Frame)
    '''
    # import bx books dataset
    df_bx_books = pd.read_csv('BX-Books.csv', encoding='unicode-escape',sep=';',quotechar='"', on_bad_lines='warn')

    # Make X in ISBN with X upper-case
    df_bx_books.loc[:,'ISBN'] = df_bx_books.loc[:,'ISBN'].apply(lambda x: x.strip().upper() if pd.notnull(x) else x)

    # Drop duplicate rows
    df_bx_books.drop_duplicates(inplace=True)

    # Book Author is missing for these 4 rows, creating a weird issue of column shift
    missing_author = df_bx_books.loc[df_bx_books['Year-Of-Publication'].apply(pd.to_numeric,errors='coerce').isna()].index.to_list()
    df_bx_books.loc[missing_author,
                    ['Book-Author','Year-Of-Publication','Publisher','Image-URL-S','Image-URL-M','Image-URL-L']
                    ] = df_bx_books.loc[missing_author].iloc[:,2:].shift(1,axis=1)

    # Some of these books also had the author's name in the title field.
    df_bx_books.loc[missing_author,'Book-Title'] = df_bx_books.loc[missing_author,
        'Book-Title'].apply(lambda x: x.split('";')[0])
    
    # One of these books has part of the author's name in the year of publication
    df_bx_books.loc[missing_author,'Year-Of-Publication'] = df_bx_books.loc[missing_author,
        'Year-Of-Publication'].apply(lambda x: x.split('";')[1].split('"')[0] if len(x.split('";'))==2 else x)
    df_bx_books['Year-Of-Publication'] = df_bx_books['Year-Of-Publication'].apply(pd.to_numeric)

    # Missing authors
    indices = df_bx_books[df_bx_books['Book-Author'].isna()].index.to_list()
    print(indices)
    if indices:
        print('Adding missing authors')
        isbns = df_bx_books.loc[indices,'ISBN'].to_list()
        print(isbns)
        authors = get_author_from_GB(isbns)
        df_bx_books.loc[indices,'Book-Author']=authors
        print(df_bx_books.loc[indices,'Book-Author'])
    
    # Rename columns for parity
    df_bx_books.columns = ['isbn','title','authors','pub_year','publisher','image_s','image_m','image_l']

    # Upon inspection there were over 70,000 books rated that did not have a correlated ISBN in the books list
    bx_missing_books_file = 'missing_books.csv'
    if os.path.exists(bx_missing_books_file):
        # import file
        df_bx_missing_books = pd.read_csv(bx_missing_books_file, encoding='unicode-escape',on_bad_lines='warn')
        df_bx_missing_books.columns = ['google_id','title','google_book_link','isbn',
                                        'pub_year','publisher','authors','num_pages',
                                        'description','genres','ratings_count','average_rating',
                                        'image_s','image_m','language']
        df_bx_books = df_bx_books.merge(df_bx_missing_books,how='outer',on=['isbn','title','authors','pub_year','publisher',
                                                            'image_s','image_m'])
    
    # Update CSV so that this doesn't have to be done repeatedly
    df_bx_books.to_csv('bx_books.csv')

    # import gr books dataset
    gr_books_file = 'books.csv'
    gr_no_isbn_file = 'gr_books2.csv'
    
    if not(os.path.exists(gr_books_file)):
        wget.download('https://raw.githubusercontent.com/zygmuntz/goodbooks-10k/master/books.csv')
    df_gr_books = pd.read_csv(gr_books_file, encoding='unicode-escape', on_bad_lines='warn')

    if os.path.exists(gr_no_isbn_file):
        # import file
        df_gr_no_isbn = pd.read_csv(gr_no_isbn_file, encoding='unicode-escape', on_bad_lines='warn', index_col='goodreads_book_id')
        
        # Set isbn column to integer (get rid of decimals) and then string and then create dictionary
        df_gr_no_isbn.loc[:,'isbn'] = df_gr_no_isbn['isbn'].astype('Int64').astype('str')
        no_isbn = df_gr_no_isbn['isbn'].to_dict()

        # Fix dictionary '<NA>' values to '' so that Pandas recognizes None Type
        for key, value in no_isbn.items():
            if value == '<NA>':
                no_isbn[key]=''

        # Replace values in isbn column of df_gr_books with values from no_isbn dictionary
        df_gr_books.isbn = df_gr_books.isbn.fillna(df_gr_books.goodreads_book_id.map(no_isbn))

    # the ISBN column does not currently have a zfill
    df_gr_books.isbn = df_gr_books.isbn.str.zfill(10)
    df_gr_books.isbn = df_gr_books.isbn.apply(lambda x: str(x).strip().upper() if pd.notnull(x) else x)
    df_gr_books.drop_duplicates(inplace=True)

    df_gr_books.columns = ['book_id', 'goodreads_book_id', 'best_book_id', 'work_id',
       'books_count', 'isbn', 'isbn13', 'authors', 'pub_year',
       'original_title', 'title', 'lang', 'avg_rating',
       'ratings_count', 'work_ratings_count', 'work_text_reviews_count',
       'ratings_1', 'ratings_2', 'ratings_3', 'ratings_4', 'ratings_5',
       'image_m', 'image_s']
    
    # Save CSV to reduce updates
    df_gr_books.to_csv('gr_books.csv')

    if 'ratings_count' in df_bx_books.columns:
        df_books = df_bx_books.merge(df_gr_books,how='outer',on=['isbn','title','authors','pub_year','image_s','image_m','ratings_count','average_rating'])
    else:
        df_books = df_bx_books.merge(df_gr_books,how='outer',on=['isbn','title','authors','pub_year','image_s','image_m'])


    df_books.isbn13 = df_books.isbn13.fillna(0).astype('int')

    # Update missing images in BX image columns (keeping BX as primary and updating M/L both with GR 'image_url')
    df_books['image_l'].fillna(df_books.image_m,inplace=True)

    # Reset index to create Booklovers Friend ID
    df_books.reset_index(inplace=True)
    df_books.rename(columns={'index':'blf_book_id'},inplace=True)
    df_books.blf_book_id += 1

    df_books.title = df_books.title.apply(titlecase)

    print('Book Data Frame Size: ',df_books.shape)

    return df_books

def gr_users(ratings):
    # Create Goodreads users dataframe
    users = ['GR'+str(user).zfill(2) for user in sorted(ratings.user_id.unique())]
    df_gr_users = pd.DataFrame(users,columns=['user_id'])
    df_gr_users['source']='Goodreads'
    df_gr_users[['location','age']]=None

    print('GR Users Data Frame Size: ',df_gr_users.shape)
    return df_gr_users

def merge_ratings(books):
    '''Merge Goodreads and Book Crossing data frames and create Goodreads user data frame
        Args: books (Pandas Data Frame)
        Returns: df_ratings (Pandas Data Frame), df_gr_users (Pandas Data Frame)'''
    # import bx ratings dataset
    df_bx_ratings = pd.read_csv('BX-Book-Ratings.csv', low_memory=False, encoding='unicode_escape',sep=";", quotechar='"')

    # NOT SURE: Add count of ratings for the user - will do this in the data transformation earlier in the future
    # df_bx_ratings['ratings_count']=df_bx_ratings.groupby('User-ID')['User-ID'].transform('count')

    # import gr ratings dataset
    gr_ratings_file = 'ratings.csv'
    if not(os.path.exists(gr_ratings_file)):
        wget.download('https://raw.githubusercontent.com/zygmuntz/goodbooks-10k/master/ratings.csv')
    
    # Create Goodreads book ratings dataframe
    df_gr_book_ratings = pd.read_csv('ratings.csv', encoding='unicode-escape', on_bad_lines='warn')

    # Rename columns for parity between data frames
    df_bx_ratings.columns = ['uid','isbn','book_rating']

    # Rescale BX ratings to 0-5 scale to match GR (currently BX scale is 0-10)
    df_bx_ratings.book_rating *= .5

    # Create user_id column from uid with prepend of 'BX' (zfill for uid <10, ex: uid=2 --> zfill=02)
    df_bx_ratings['user_id']=df_bx_ratings.uid.apply(lambda x: 'BX'+str(x).zfill(2) if pd.notnull(x) else x)

    # Add book_id (from GR dataset) and blf_book_id (Booklover's Friend ID) column for parity
    df_bx_ratings = df_bx_ratings.merge(books[['book_id','isbn','blf_book_id']], how='left', on=['isbn'])

    # Update Goodreads Ratings column names
    df_gr_book_ratings.columns = ['uid','book_id','book_rating']

    # Update df_gr_book_ratings rating column to a float
    df_gr_book_ratings = df_gr_book_ratings.astype(dtype={'book_rating':'Float64'})

    # Create user_id column from uid with prepend of 'GR'
    df_gr_book_ratings['user_id'] = df_gr_book_ratings.uid.apply(lambda x: 'GR'+str(x).zfill(2))

    # Add isbn and blf_book_id column for parity to GR Ratings data frame
    df_gr_book_ratings = df_gr_book_ratings.merge(books[['book_id','isbn','blf_book_id']], how='left', on=['book_id'])

    df_ratings = df_bx_ratings.merge(df_gr_book_ratings,how='outer',on=['blf_book_id','user_id','book_rating','isbn','book_id','uid'])
    df_ratings[['book_id','blf_book_id']] = df_ratings[['book_id','blf_book_id']].astype('Int64')
    df_ratings = df_ratings[~df_ratings.blf_book_id.isna()]

    print('Ratings Data Frame Size: ', df_ratings.shape)
    return df_ratings, gr_users(df_gr_book_ratings)

def merge_users(df2):
    ''' Merge user data frames into a single user dataframe.
        Args: None
        Returns: df_users (Pandas Data Frame)'''

    # import bx users dataset
    df_bx_users = pd.read_csv('BX-Users.csv', low_memory=False, encoding='unicode_escape',sep=";", quotechar='"')

    # Rename columns for parity between data frames
    df_bx_users.columns = ['uid','location','age']

    # Create a unique user_id by prepending 'BX' to the user id (with a zero fill for user_id<10)
    df_bx_users['user_id'] = df_bx_users.uid.apply(lambda x: 'BX'+str(x).zfill(2))
    df_bx_users['source'] = 'Book Crossing'

    df2.age = df2.age.astype('float')

    df_users = df_bx_users.merge(df2,how='outer',on=['user_id', 'location', 'age', 'source'])

    print('User Data Frame Size: ',df_users.shape)
    return df_users

def cover(df):
    ''' Creates a 'cover' column that includes the image of the book cover with a link to the site's book page.
        Args: df (Pandas Data Frame) - contains final book list
        Returns: list of thumbnail links to be appended to the books data frame
    '''
    print('creating cover html')
    thumbnails = []
    for index,row in df.iterrows():
        image_link = row['image_s']
        book_title = row['title']
        blf_book_id = row['blf_book_id']
        thumbnail_url = f'<a href="/book/{blf_book_id}"><img src={image_link} alt={book_title}>'
        thumbnails.append(thumbnail_url)
    return thumbnails

def save_model(df_ratings):
    ''' Saves K-Nearest Neighbors model for use in getting book recommendations.
        Args: ratings (Pandas Data Frame)
    '''
    print('saving model')
    # Get ratings by user (as a dictionary in the form blf_bookid: ratings), vectorize for fitting the model
    by_user_ratings = df_ratings[~df_ratings.blf_book_id.isna()].groupby('user_id').apply(
    lambda items: {i[6]: i[3] for i in items.itertuples()})
    features = DictVectorizer().fit_transform(by_user_ratings)

    # Use K Nearest Neighbors to identify top 5 books
    nn = NearestNeighbors(n_neighbors=20, metric='cosine', algorithm='brute').fit(features)
    joblib.dump(nn, 'nn.pkl')
    joblib.dump(by_user_ratings, 'by_user_ratings.pkl')
    joblib.dump(features, 'features.pkl')
    print('model saved!')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output_directory_path', type=str)
    parser.add_argument('--format', type=str, action="store", default="csv",
                        dest="format", choices=["sql", "csv"],
                        help="set file output format")
    parser.add_argument('--update_files',type=str)
    parser.add_argument('--sql_books', type=str)
    parser.add_argument('--sql_users', type=str)
    parser.add_argument('--sql_ratings', type=str)
    args = parser.parse_args()

    books_filepath = 'books_final.csv'
    ratings_filepath = 'ratings_final.csv'
    users_filepath = 'users_final.csv'

    if args.update_files=='Yes':
        # bx = Book Crossing
        fileExists = os.path.exists('BX-CSV-Dump.zip')
        print('BX-CSV-Dump exists: ' + str(fileExists))
        if not(fileExists):
            wget.download('http://www2.informatik.uni-freiburg.de/~cziegler/BX/BX-CSV-Dump.zip')
            with ZipFile('BX-CSV-Dump.zip') as zip:
                zip.extractall()

        print('merging books')
        # Merge books and save file
        books_final = merge_books()

        print('adding covers')
        # Add cover html for link + cover image column - NEED to run this after merge
        books_final['cover']=cover(books_final)
        
        print('merging ratings')
        # Merge ratings and save file
        ratings_final, df_gr_users = merge_ratings(books_final)
        
        print('merging users')
        # Merge users and save file
        users_final = merge_users(df_gr_users)

        # Fit KNN model with updated data
        save_model(ratings_final)

    else:
        print('Update files argument was not yes')
        books_final = pd.read_csv(books_filepath, dtype={'pub_year':'Int64', 'original_title':str, 'lang':str})
        ratings_final = pd.read_csv(ratings_filepath,usecols=['blf_book_id','user_id','book_rating'],dtype={'blf_book_id': 'Int32', 'user_id': str, 'book_rating':'Float32'})
        users_final = pd.read_csv(users_filepath)

    if args.format == 'csv':
        books_final.to_csv('books_final.csv', index=False)
        ratings_final.to_csv('ratings_final.csv', index=False)
        users_final.to_csv('users_final.csv', index=False)
        print('CSVs saved!')
    
    elif args.format == 'sql':
        print('starting SQL table updates', str(datetime.now()))
        sql_url = config.sql_url
        conn = sa.create_engine(sql_url)
        # metadata = sa.MetaData(bind=conn)

        books_tname = 'books'
        users_tname = 'users'
        ratings_tname = 'ratings'

        if args.sql_books == 'Yes':
            print('updating books')
            # Add data to BOOKS table
            time1 = datetime.now()
            books_final.to_sql(name=books_tname,con=conn, if_exists='replace', chunksize=5000, method='multi', index=False)
            time2 = datetime.now()
            print('time to add books:',time2-time1)
            print('Book table updated!',str(datetime.now()))

        # USERS
        if args.sql_users == 'Yes':
            print('updating users')
            
            # Add data to USERS table
            time1 = datetime.now()
            users_final.to_sql(name=users_tname, con=conn, if_exists='replace', chunksize=50000, method='multi', index=False)
            time2 = datetime.now()
            print('time to add users:',time2-time1)
            print('User table updated!')

        
        # RATINGS
        if args.sql_ratings == "Yes":
            print('updating ratings')
            
            # Add data to RATINGS table
            time1 = datetime.now()
            ratings_final.to_sql(name=ratings_tname,con=conn, if_exists='replace', chunksize=5000, method='multi', index=False)
            time2 = datetime.now()
            print('time to add ratings:',time2-time1)
            print('Ratings table updated!')
        
        conn.dispose()
        print('SQL updated!')
        
if __name__ == '__main__':
    main()
