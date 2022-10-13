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

@app.route('/data/', methods = ['POST','GET'])
def data():
    if request.method == 'GET':
        return f"You are trying to access /data directly, try going to /form instead to submit form."
    if request.method == 'POST':
        form_data = request.form
        new_df_bx_users = form_info.add_user(df_bx_users,form_data['Location'])
        userid = len(new_df_bx_users)
        new_df_bx_ratings = form_info.add_rating(df_bx_ratings,userid, form_info.get_isbn(df_bx_books,form_data['Book-Title']))
        sim_users = book_recs.get_similar_users(new_df_bx_users,userid)
        book_rec_isbn = book_recs.get_recs_by_loc(new_df_bx_ratings,sim_users)

        # book_list=df_bx_books[df_bx_books['ISBN'].isin(book_rec_isbn)][['Book-Title','Book-Author']].to_dict('records')
        book_list_html=df_bx_books[df_bx_books['ISBN'].isin(book_rec_isbn)][['Book-Title','Book-Author']].to_html(index=False)
        book_list = book_list_html.replace('table border="1"','table border="0"').replace('<tr style="text-align: right;">', '<tr style="text-align: left;">').replace('<th>', '<th align="left">')

        return render_template('data.html',book_list = book_list)