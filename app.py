from flask import Flask, render_template,request
import pandas as pd
import form_info
import book_recs

app = Flask(__name__)

# bx = Book Crossing
# import bx ratings dataset
df_bx_ratings = pd.read_csv('BX-Book-Ratings.csv', low_memory=False, encoding='unicode_escape',sep=";", quotechar='"')

# import bx books dataset
df_bx_books = pd.read_csv('BX-Books-fixed.csv', encoding='unicode-escape',sep=';',quotechar='"', error_bad_lines=False)

# import bx users dataset
df_bx_users = pd.read_csv('BX-Users.csv', index_col = 'User-ID', low_memory=False, encoding='unicode_escape',sep=";", quotechar='"')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/form')
def form():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/data/', methods = ['POST','GET'])
def data():
    if request.method == 'GET':
        return f"You are trying to access /data directly, try going to <a href='\'>the homepage</a> instead to submit form."
    if request.method == 'POST':
        # Get data submitted to the form
        form_data = request.form
        location = form_data['Location']
        book = form_data['Book-Title']

        # Add location as "new user" to users dataframe and get new user's ID
        new_df_bx_users = form_info.add_user(df_bx_users,location)
        userid = len(new_df_bx_users)

        # Add rating line for "new user" with book submitted
        new_df_bx_ratings = form_info.add_rating(df_bx_ratings,userid, form_info.get_isbn(df_bx_books,book))

        # Based on location, get similar users and then recommendations based on similar users
        book_rec_isbn = book_recs.get_recs_by_loc(new_df_bx_users,new_df_bx_ratings,userid)

        # Filter booklist by ISBNs of book recs and add a cover column with image html
        new_df_bx_books = df_bx_books[df_bx_books['ISBN'].isin(book_rec_isbn)]
        # new_df_bx_books['Cover']=book_recs.thumbnails(new_df_bx_books)
        new_df_bx_books.loc[:,('Cover')]=book_recs.thumbnails(new_df_bx_books)


        # Translate dataframe to table format in HTML (render_links = True, escape = False to make covers display)
        book_list_loc_html=new_df_bx_books[['Cover','Book-Title','Book-Author']].to_html(index=False,render_links=True,escape=False)
        book_list_loc = book_list_loc_html.replace('table border="1"','table border="0"').replace('<tr style="text-align: right;">', '<tr style="text-align: left;">').replace('<th>', '<th align="left">')

        return render_template('data.html',book_list_loc = book_list_loc, book=book, location=location)

@app.route('/book/<isbn>')
def bookdetails(isbn):
    book = df_bx_books[df_bx_books['ISBN']==isbn].to_dict(orient='records')[0]
    return render_template('book_details.html', book = book)