from difflib import diff_bytes
from xml.sax import default_parser_list
import os
import pandas as pd
from zipfile import ZipFile
import wget

def merge_books(df1,df2):
    df2.rename(columns={'isbn':'ISBN'}, inplace=True)
    print(df2.columns)
    df_books = df1.merge(df2,how='outer',left_on=['ISBN','Book-Author','Year-Of-Publication','Image-URL-S','Image-URL-M'],right_on=['ISBN','authors','original_publication_year','small_image_url','image_url'])

    # Update missing authors in GR 'Book-Author' column and merge to single column (taking GR as primary author)
    df_books['Book-Author'].fillna(df_books.authors,inplace=True)
    df_books.drop(['Book-Author'],axis=1,inplace=True)

    # Update missing titles in BX 'title' column and merge to a single column (taking BX as primary title)
    df_books['Book-Title'].fillna(df_books.title,inplace=True)
    df_books.drop(['title'],axis=1,inplace=True)

    # Update missing images in BX image columns (keeping BX as primary and updating M/L both with GR 'image_url')
    df_books['Image-URL-S'].fillna(df_books.small_image_url,inplace=True)
    df_books['Image-URL-L'].fillna(df_books.image_url,inplace=True)
    df_books['Image-URL-M'].fillna(df_books.image_url,inplace=True)
    df_books.drop(['small_image_url','image_url'],axis=1,inplace=True)

    return df_books

def merge_users(df1, df2):
    df_users = df1.merge(df2,how='outer',left_on=['user_id'],right_on=['user_id'])

def cover(df):
    thumbnails = []
    for index,row in df.iterrows():
        image_link = row['Image-URL-S']
        book_title = row['Book-Title']
        isbn = row['ISBN']
        thumbnail_url = f'<a href="/book/{isbn}"><img src={image_link} alt={book_title}>'
        thumbnails.append(thumbnail_url)
    return thumbnails
def main():
    # bx = Book Crossing
    fileExists = os.path.exists('BX-CSV-Dump.zip')
    if not(fileExists):
        wget.download('http://www2.informatik.uni-freiburg.de/~cziegler/BX/BX-CSV-Dump.zip')
        with ZipFile('BX-CSV-Dump.zip') as zip:
            zip.extractall()
    
    # import bx ratings dataset
    df_bx_ratings = pd.read_csv('BX-Book-Ratings.csv', low_memory=False, encoding='unicode_escape',sep=";", quotechar='"')

    # Add count of ratings for the user - will do this in the data transformation earlier in the future
    df_bx_ratings['ratings_count']=df_bx_ratings.groupby('User-ID')['User-ID'].transform('count')

    # import bx books dataset
    df_bx_books = pd.read_csv('BX-Books.csv', encoding='unicode-escape',sep=';',quotechar='"', on_bad_lines='warn')

    # Add cover html for link + cover image column - NEED to run this after merge
    # df_bx_books.loc[:,('Cover')]=cover(df_bx_books)

    # import bx users dataset
    df_bx_users = pd.read_csv('BX-Users.csv', low_memory=False, encoding='unicode_escape',sep=";", quotechar='"')
    df_bx_users.columns = ['user_id','location','age']
    bx_users = ['BX'+str(user).zfill(2) for user in df_bx_users.user_id.array]
    df_bx_users['user_id'] = bx_users
    df_bx_users['source'] = 'Book Crossing'

    gr_books_file = 'books.csv'
    gr_bt_file = 'book_tags.csv'
    gr_ratings_file = 'ratings.csv'
    gr_tags_file = 'tags.csv'

    if not(os.path.exists(gr_books_file)):
        wget.download('https://raw.githubusercontent.com/zygmuntz/goodbooks-10k/master/books.csv')
    if not(os.path.exists(gr_bt_file)):
        wget.download('https://raw.githubusercontent.com/zygmuntz/goodbooks-10k/master/book_tags.csv')
    if not(os.path.exists(gr_ratings_file)):
        wget.download('https://raw.githubusercontent.com/zygmuntz/goodbooks-10k/master/ratings.csv')
    if not(os.path.exists(gr_tags_file)):
        wget.download('https://raw.githubusercontent.com/zygmuntz/goodbooks-10k/master/tags.csv')

    #gr = GoodReads
    # Create Goodreads book list dataframe
    df_gr_books = pd.read_csv('books.csv', encoding='utf-8', on_bad_lines='warn')

    # Create Goodreads book tag dataframe
    df_gr_book_tags = pd.read_csv('book_tags.csv', encoding='unicode-escape', on_bad_lines='warn')

    # Create Goodreads book ratings dataframe
    df_gr_book_ratings = pd.read_csv('ratings.csv', encoding='unicode-escape', on_bad_lines='warn')

    # Create Goodreads tags dataframe
    df_gr_tags = pd.read_csv('tags.csv', encoding='unicode-escape', on_bad_lines='warn')

    # Create Goodreads users dataframe
    users = ['GR'+str(user).zfill(2) for user in sorted(df_gr_book_ratings.user_id.unique())]
    df_gr_users = pd.DataFrame(users,columns=['user_id'])
    df_gr_users['source']='Goodreads'
    df_gr_users[['location','age']]=None
    # Not sure if we want the user_id to be the index...
    # df_gr_users.set_index('user_id',inplace=True)

    # Merge books and save file
    books_final = merge_books(df_bx_books, df_gr_books)
    books_final.to_csv('books_final.csv', index=False)

    # Merge users and save file
    users_final = merge_users(df_bx_users,df_gr_users)
    users_final.to_csv('users_final.csv', index=False)

    # Merge ratings and save file


if __name__ == '__main__':
    main()
