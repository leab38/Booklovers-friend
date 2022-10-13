# Add the new information (location) to the user database, receives dataframe and location, returns dataframe
def add_user(df, location):
    data = [location, None]
    df.loc[len(df)+1]=data
    return df #new user id

def add_rating(df, userid, isbn, rating=4):
    # Assuming enjoyed = rating of at least 4
    data=[userid, isbn, rating]
    df.loc[len(df)+1]=data
    return df

def get_isbn(df, book_title):
    return df[df['Book-Title']==book_title]['ISBN'].iloc[0]
