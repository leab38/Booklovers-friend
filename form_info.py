import os
import psycopg2
from psycopg2.extras import RealDictCursor

sql_url = os.environ.get('blf_sql')
# Add the new information (location) to the user database, receives dataframe and location, returns dataframe
def add_user(df, location):
    data = [location, None]
    df.loc[len(df)+1]=data
    return df #new user id

def add_rating(df, userid, isbn, rating=5,count=1):
    # Form ask for last 5 star book, hence rating = 5
    data=[userid, isbn, rating, count]
    df.loc[len(df)+1]=data
    return df

def get_isbn(df, book_title):
    return df[df['Book-Title']==book_title]['ISBN'].iloc[0]

def get_blf_book_id(title):
    
    conn = None
    error = None
    updated_rows = 0

    params = {'title':title}

    try:
        # Open connection to database
        conn = psycopg2.connect(sql_url)
        cursor = conn.cursor()

        # select only users from that location
        query = "SELECT blf_book_id FROM books INNER JOIN ratings using(blf_book_id) WHERE book_rating=5 AND title LIKE %(title)s ESCAPE '' ORDER BY blf_book_id LIMIT 1"
        cursor.execute(query, params)
        blf_book_id = cursor.fetchall()
        updated_rows = cursor.rowcount
        print(updated_rows,'rows updated!')

        conn.close()
        
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    
    finally:
        if conn is not None:
            conn.close()
        if error:
            exit(0)
    
    return blf_book_id[0][0]
