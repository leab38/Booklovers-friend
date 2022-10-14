import pandas as pd
from sklearn import base
from sklearn.feature_extraction import DictVectorizer
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.neighbors import NearestNeighbors
from sklearn.decomposition import TruncatedSVD

class DictEncoder(base.BaseEstimator, base.TransformerMixin):
    def __init__(self,col):
        self.col = col
        
    def fit(self, X, y=None):
        return self
    
    def transform(self, X):
        def to_dict(s):
            try: 
                return {x:1 for x in s.split(',')}
            except: 
                return {}
        return X[self.col].apply(to_dict)

def bayes_sum(N, mu):
    return lambda x: (x.sum() + mu*N) / (x.count() + N)

def thumbnails(df):
    thumbnails = []
    for index,row in df.iterrows():
        image_link = row['Image-URL-S']
        book_title = row['Book-Title']
        thumbnail_url = f"<img src='{image_link}' alt='{book_title}'>"
        thumbnails.append(thumbnail_url)
    return thumbnails

def get_similar_users(df_users, userid):

    # Pipeline to SVD the locations
    loc_pipe = Pipeline([('encoder',DictEncoder('Location')),
                    ('vectorizer', DictVectorizer()),
                    ('svd', TruncatedSVD(n_components=100))])
    
    features = loc_pipe.fit_transform(df_users)

    # Set up KNN for 20 neighbors fitting the locations
    nn = NearestNeighbors(n_neighbors=20).fit(features)
    nn.fit(features)

    # Use the results of the KNN to find other users in a similar location based on truncated SVD
    dists, indices = nn.kneighbors([features[len(df_users.index)-1]])
    return df_users.iloc[indices[0]]

def get_recs_by_loc(df_ratings,df_sim_users):

    # Filter df_ratings by only the "closest" users
    sim_user_ratings = df_ratings[df_ratings['User-ID'].isin(df_sim_users.index)]

    # Group users with similar ratings
    by_user_ratings_mult = sim_user_ratings.groupby('User-ID').apply(
    lambda items: {i[2]: i[3] for i in items.itertuples()})
    features_mult = DictVectorizer().fit_transform(by_user_ratings_mult)

    # Set up nearest neighbors to identify the book ratings for users in this location
    nn_mult = NearestNeighbors(n_neighbors=8, metric='cosine', algorithm='brute').fit(features_mult)
    dists, indices = nn_mult.kneighbors(features_mult)
    neighbors_mult = [by_user_ratings_mult.index[i] for i in indices[0]][1:]
    ratings_grp_mult = df_ratings[df_ratings['User-ID'].isin(neighbors_mult)].groupby('ISBN')['Book-Rating']

    # Calculate Bayes sum for user ratings and return top 5 books based on Bayes sum
    ratings_grp_mult.aggregate(bayes_sum(5,3)).sort_values(ascending = False)
    return ratings_grp_mult.aggregate(bayes_sum(5,3)).sort_values(ascending = False).head().index.tolist()