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
        isbn = row['ISBN']
        thumbnail_url = f'<a href="/book/{isbn}"><img src={image_link} alt={book_title}>'
        thumbnails.append(thumbnail_url)
    return thumbnails

def get_similar_users(df_users, userid):

    # # Pipeline to SVD the locations
    # loc_pipe = Pipeline([('encoder',DictEncoder('Location')),
    #                 ('vectorizer', DictVectorizer()),
    #                 ('svd', TruncatedSVD(n_components=100))])
    
    # features = loc_pipe.fit_transform(df_users)

    # # Set up KNN for 20 neighbors fitting the locations
    # nn = NearestNeighbors(n_neighbors=500).fit(features)
    # nn.fit(features)

    # # Use the results of the KNN to find other users in a similar location based on truncated SVD
    # dists, indices = nn.kneighbors([features[len(df_users.index)-1]])
    # return df_users.iloc[indices[0]]

    location = df_users['Location'].iloc[userid-1]
    return df_users[df_users['Location'].str.contains(location,na=False)]

def get_recs_by_loc(df_users,df_ratings,userid):
    df_sim_users = get_similar_users(df_users,userid)

    # Filter df_ratings by only the "closest" users
    sim_user_ratings = df_ratings[df_ratings['User-ID'].isin(df_sim_users.index)]
    ratings_grp_mult = sim_user_ratings.groupby('ISBN')['Book-Rating']

    # # Group users with similar ratings
    # by_user_ratings_mult = sim_user_ratings.groupby('User-ID').apply(
    # lambda items: {i[2]: i[3] for i in items.itertuples()})
    # features_mult = DictVectorizer().fit_transform(by_user_ratings_mult)

    # # Just in case the value is smaller than the NearestNeighbors value
    # if features_mult.size <10:
    #     nn_num = features_mult.size
    # else:
    #     nn_num=10

    # # Set up nearest neighbors to identify the book ratings for users in this location
    # nn_mult = NearestNeighbors(n_neighbors=nn_num, metric='cosine', algorithm='brute').fit(features_mult)
    # dists, indices = nn_mult.kneighbors(features_mult)
    # neighbors_mult = [by_user_ratings_mult.index[i] for i in indices[0]][1:]
    # ratings_grp_mult = df_ratings[df_ratings['User-ID'].isin(neighbors_mult)].groupby('ISBN')['Book-Rating']

    # Calculate Bayes sum for user ratings and return top 5 books based on Bayes sum
    return ratings_grp_mult.aggregate(bayes_sum(5,3)).sort_values(ascending = False).head().index.tolist()

def get_recs_by_user(df_users, df_ratings, userid, isbn):
    
    # Set value of rating for book to 5, since the form asks for 5 star book, identify user with 
    # max number of reviews who also rated the preferred book with a 5.
    rating = 5
    sim_user_ratings = df_ratings[(df_ratings['ISBN']==isbn) & (df_ratings['Book-Rating']==rating)]
    uid_max = sim_user_ratings['User-ID'][sim_user_ratings['ratings_count']==sim_user_ratings['ratings_count'].max()]
    uid_max = uid_max.iloc[0]

    # Get ratings for the user with the max
    # One user at a time
    by_user_ratings = df_ratings.groupby('User-ID').apply(
        lambda items: {i[2]: i[3] for i in items.itertuples()})
    features = DictVectorizer().fit_transform(by_user_ratings)

    # Use K Nearest Neighbors to identify top 5 books
    nn = NearestNeighbors(n_neighbors=20, metric='cosine', algorithm='brute').fit(features)
    dists, indices = nn.kneighbors(features[by_user_ratings.index.get_loc(uid_max), :])
    neighbors = [by_user_ratings.index[i] for i in indices[0]][1:]
    ratings_grp = df_ratings[df_ratings['User-ID'].isin(neighbors)].groupby('ISBN')['Book-Rating']

    # Calculate bayes sum aggregation on ratings
    return ratings_grp.aggregate(bayes_sum(5,3)).sort_values(ascending = False).head().index.tolist()