# from data_prep import config
import joblib
import numpy as np
import os
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from sklearn.feature_extraction import DictVectorizer
from sklearn.neighbors import NearestNeighbors

sql_url = os.environ.get('blf_sql')

def bayes_sum(N, mu):
    return lambda x: (x.sum() + mu*N) / (x.count() + N)

def get_books(id_list):
    '''Get books from PostgreSQL database based on list of blf_book_ids
       Args: id_list - list of blf_book_ids recommended
       Returns: Pandas Data Frame with book details'''
    params = {'id_list': tuple(id_list)}
    print(params)

    conn = None
    error = None
    updated_rows = 0

    try:
        # Open connection to database
        conn = psycopg2.connect(sql_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # select only users from that location
        query = """SELECT blf_book_id, title, cover, authors, pub_year, publisher, image_m
                    FROM books 
                    WHERE blf_book_id in %(id_list)s"""
        cursor.execute(query, params)
        book_dict = cursor.fetchall()
        updated_rows = cursor.rowcount
        conn.close()

    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    
    finally:
        if conn is not None:
            conn.close()
        if error:
            exit(0)
    
    books = pd.DataFrame(book_dict)
    return books

def get_similar_users(location):
    '''Find all users with a location containing the string entered in the form field -- future plan 
        is to autopopulate field as the person types to reduce the possibility of no match.'''
    # Define query parameters
    params = {'location': location+'%'}

    conn = None
    error = None
    updated_rows = 0

    try:
        # Open connection to database
        conn = psycopg2.connect(sql_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # select only users from that location
        query = "SELECT * FROM users WHERE location LIKE %(location)s"
        cursor.execute(query, params)
        # print(cursor.query)
        user_dict = cursor.fetchall()
        updated_rows = cursor.rowcount
        conn.close()

    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    
    finally:
        if conn is not None:
            conn.close()
        if error:
            exit(0)

    sim_users = pd.DataFrame(user_dict)
    sim_users.set_index('user_id', inplace=True)

    return sim_users

def get_recs_by_loc(location):
    ''' At the moment this function always returns the same list of books for any user in that location
        Future plan: the book entered will also be part of the recommendation.
        Args: user (Pandas data frame), ratings (Pandas data frame), userid (int)
        Returns: Pandas data frame with the top 5 books rated for the location.
    '''
    df_sim_users = get_similar_users(location)
    params = {'users': tuple(df_sim_users.index.to_list())}
    conn = None
    error = None
    updated_rows = 0

    try:
        conn = psycopg2.connect(sql_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = "SELECT blf_book_id, user_id, book_rating FROM ratings WHERE user_id in %(users)s"
        cursor.execute(query, params)
        ratings_dict = cursor.fetchall()
        updated_rows = cursor.rowcount
        conn.close()

    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    
    finally:
        if conn is not None:
            conn.close()
        if error:
            exit(0)

    # Filter df_ratings by only the "closest" users
    sim_user_ratings = pd.DataFrame(ratings_dict)
    print(sim_user_ratings.head())
    ratings_grp_mult = sim_user_ratings.groupby('blf_book_id')['book_rating']

    # Calculate Bayes sum for user ratings and return top 5 books based on Bayes sum
    return ratings_grp_mult.aggregate(bayes_sum(5,3)).sort_values(ascending = False).head().index.tolist()

def get_recs_by_user(blf_book_id,title):
    ''' Uses K-Nearest Neighbors to get the top 5 books based on other users who have highly rated the same book.
        Args: users (Pandas Data Frame), ratings (Pandas Data Frame), userid (int), isbn (string)
        Return: Pandas Data Frame with 5 recommended books
    '''
    # Set value of rating for book to 5, since the form asks for 5 star book 
    rating = 5.0

    # Create params for SQL query
    params = {'blf_book_id': blf_book_id, 'book_rating': rating,'title': title}
    print(params)

    error = None
    conn = None
    updated_rows = 0

    # Find all similar users who rated this book a 5
    # Start with connection to the database
    try:
        conn = psycopg2.connect(sql_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """WITH ratings_rc AS (
                SELECT ROW_NUMBER() over () AS rn,
                        user_id,
                        blf_book_id,
                        book_rating
                FROM ratings
            )
            SELECT rn, user_id
            FROM ratings_rc
            INNER JOIN books using (blf_book_id)
            WHERE blf_book_id = %(blf_book_id)s and book_rating = %(book_rating)s and title != %(title)s"""
        cursor.execute(query, params)
        ratings_dict = cursor.fetchall()

        sim_user_ratings = pd.DataFrame(ratings_dict)
        print(sim_user_ratings)

        # Get ratings (as dictionary) for the user with the max number of reviewed books
        by_user_ratings = joblib.load('by_user_ratings.pkl')
        features = joblib.load('features.pkl')

        # Load the model from the file
        nn = joblib.load('nn.pkl')
        
        # Use the loaded model to make predictions
        dists, indices = nn.kneighbors(features[])
        neighbors = [sim_user_ratings.rn[i] for i in indices[0]][1:]

        params = {'neighbors': tuple(neighbors), 'blf_book_id': blf_book_id}
        print(neighbors)
        query = "SELECT * FROM ratings WHERE user_id IN %(neighbors)s and blf_book_id != %(blf_book_id)s"
        cursor.execute(query, params)
        ratings_grp_dict = cursor.fetchall()
        updated_rows = cursor.rowcount
        ratings_grp = pd.DataFrame(ratings_grp_dict).groupby('blf_book_id')['book_rating']
        
        conn.close()

    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    
    finally:
        if conn is not None:
            conn.close()
        if error:
            exit(0)

    # Calculate bayes sum aggregation on ratings
    return ratings_grp.aggregate(bayes_sum(5,3)).sort_values(ascending = False).head().index.tolist()