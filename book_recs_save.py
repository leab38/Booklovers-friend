import argparse
import joblib
import pandas as pd
from sklearn import base
from sklearn.feature_extraction import DictVectorizer
from sklearn.neighbors import NearestNeighbors

def save_model(df_ratings):
    ''' Uses K-Nearest Neighbors to get the top 5 books based on other users who have highly rated the same book.
        Args: users (Pandas Data Frame), ratings (Pandas Data Frame), userid (int), isbn (string)
        Return: Pandas Data Frame with 5 recommended books
    '''

    # Get ratings (as dictionary) for the user with the max number of reviewed books
    by_user_ratings = df_ratings.groupby('user_id').apply(
        lambda items: {i[6]: i[3] for i in items.itertuples()})
    features = DictVectorizer().fit_transform(by_user_ratings)

    # Use K Nearest Neighbors to identify top 5 books
    nn = NearestNeighbors(n_neighbors=20, metric='cosine', algorithm='brute').fit(features)
    joblib.dump(nn, 'nn.pkl')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output_directory_path', type=str)
    parser.add_argument('--ratings', type=str)
    args = parser.parse_args()

    df_ratings = pd.read_csv(args.ratings)

    save_model(df_ratings)



if __name__ == '__main__':
    main()