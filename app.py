import form_info
import book_recs_pred

from flask import Flask, render_template,request
import pandas as pd



app = Flask(__name__)

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
        return f"You are trying to access /data directly, try going to <a href='/'>the homepage</a> instead to submit form."
    if request.method == 'POST':
        # Get data submitted to the form
        form_data = request.form
        location = form_data['location']
        book = form_data['title']
        id = form_info.get_blf_book_id(book)

        # Based on location, get similar users and then recommendations based on similar users
        book_rec_loc_id = book_recs_pred.get_recs_by_loc(location)

        # Based on book, get similar users and then recommendations based on similar users
        book_rec_book_id = book_recs_pred.get_recs_by_user(id,book)
        print(book_rec_book_id)

        # Get books from database with IDs in the book_rec_book_id
        new_df_bx_books_book = book_recs_pred.get_books(book_rec_book_id)
        book_rec_loc_books = book_recs_pred.get_books(book_rec_loc_id)

        # Translate dataframe to table format in HTML (render_links = True, escape = False to make covers display)
        book_list_loc_html=book_rec_loc_books[['cover','title','authors']].to_html(index=False,render_links=True,escape=False)
        book_list_loc = book_list_loc_html.replace('table border="1"','table border="0"').replace('<tr style="text-align: right;">', '<tr style="text-align: left;">').replace('<th>', '<th align="left">')

        # Translate dataframe to table format in HTML (render_links = True, escape = False to make covers display)
        book_list_book_html=new_df_bx_books_book[['cover','title','authors']].to_html(index=False,render_links=True,escape=False)
        book_list_book = book_list_book_html.replace('table border="1"','table border="0"').replace('<tr style="text-align: right;">', '<tr style="text-align: left;">').replace('<th>', '<th align="left">')

        return render_template('data.html',book_list_loc = book_list_loc, book_list_book = book_list_book, book=book, location=location)

@app.route('/book/<blf_book_id>')
def bookdetails(blf_book_id):
    book = book_recs_pred.get_books([blf_book_id]).to_dict(orient='records')[0]
    print(book)
    return render_template('book_details.html', book = book)