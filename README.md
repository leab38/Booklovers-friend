# Booklovers-friend
Booklover's Friend is a site dedicated to helping you figure out what to read next. This website uses two datasets to provide you with recommendations based on your location and your last "5 star" read.

Recommendation Engine
---------------------

The recommendation engine for Booklover's Friend does the following:

1.  Compares your location entered to the other user locations and makes a recommendation based on the ratings of other users in your location.
2.  Uses a K-Nearest Neighbors algorithm to find the highest ratings of other users who liked the same book that you entered.
3.  Ratings are compared using a Bayesian prior to smooth the ratings and give less popular books a chance to be recommended.

Datasets
--------

### [Book Crossing (BX) Dataset](http://www2.informatik.uni-freiburg.de/~cziegler/BX/)

*   Books and Users: Over **250,000** including user locations
*   Ratings: Over **1 million**

### [Goodreads Dataset](https://github.com/zygmuntz/goodbooks-10k)

*   Books: **10,000**
*   Ratings: **6 million**

### Data Pre-Processing

#### Data Analysis

Given the difference in sizes of the datasets, I first began by making a minimum viable product with the Book Crossing dataset. This involved importing the dataset and then understanding how it was structured. The Book Crossing dataset had three files: BX-books, BX-users, BX-ratings. The books were identified in both the books and ratings file with the ISBN. The users had a numeric user ID assigned, which is present in both the BX-users file and the BX-ratings file.

Once my model was working with the Book Crossing dataset, then I looked next into merging the data from the Book Crossing and Goodreads datasets. There were three separate merges required: the book lists, the user lists, and the user ratings. The merge had to take into account these particularities of the data:

1.  The Book Crossing dataset had the ISBN as primary key for the books. The Goodreads dataset instead had its own unique "book\_id". In fact, the Goodreads dataset had multiple book IDs: book\_id, goodreads\_book\_id, works\_id, isbn, isbn13, and more!
2.  Some of the Goodreads dataset (700 books) did not have an ISBN. Since ISBN was the link between the datsets and the only overlapping book identification number, this had to be resolved by scraping Goodreads for updated information to ensure all books have an ISBN.
3.  The book list merging included:

*   Find and replace missing ISBNs for Goodreads books.
*   Merge the two datasets.
*   For books that were in both datasets, compare overlapping column data, which includes: title, author(s), year of publication, book cover URLs.
*   I decided to keep the title from the Book Crossing dataset, as I found less broken/missing letters in titles that were not in English.
*   I kept the authors from the Goodreads dataset, as a review of a sample of these was more accurate.
*   For year of publication and image URLs the Book Crossing dataset was kept as default.

5.  The user list merge was simpler than the booklist (as there were fewer elements). The steps were the below:

*   The Goodreads dataset did not have a user list, only the users listed in the ratings list. In order to be able to merge the two, I created a user list with the unique user IDs and added columns for age and location (with Null values) to match the Book Crossing dataset.
*   Pre-pend an identifier for the user\_id to avoid duplicates. (BX: Book Crossing, GR: Goodreads).
*   Add a source column to say whether the user was a Goodreads or Book Crossing user.

7.  The ratings list merge had a few pre-processing steps before the merge could be completed:

*   The Goodreads book list had to have all null ISBNs filled in with the correct numbers before proceeding.
*   Since the Goodreads book list had its own book\_id that was being used as a primary key, I added an ISBN column to the Goodreads ratings list.

### Model Creation

The recommendation model groups all of the user ratings based on user ID and then uses the DictVectorizer package to create the feature matrix. This feature matrix is then fed into a K-Nearest Neighbors algorithm to provide a list of similar users based on the books rated. I then pickled the model using joblib to reduce the amount of data to be loaded into memory and load only the pre-fit model on the website to provide the recommendations.

### Final Product

The Booklover's Friend website was built using the Python Flask framework. The About Page graph was made using Altair.

.error { color: red; }

(function(vegaEmbed) { var spec = {"config": {"view": {"continuousWidth": 800, "continuousHeight": 500}}, "data": {"name": "data-636ea49a4789c3bf989fe3e1f900db1d"}, "mark": {"type": "bar", "color": "teal"}, "encoding": {"x": {"field": "Location", "title": "User Location", "type": "nominal"}, "y": {"field": "Count", "title": "Number of Users", "type": "quantitative"}}, "title": "Top 15 User Locations", "$schema": "https://vega.github.io/schema/vega-lite/v4.17.0.json", "datasets": {"data-636ea49a4789c3bf989fe3e1f900db1d": \[{"Location": "london, england, united kingdom", "Count": 2506}, {"Location": "toronto, ontario, canada", "Count": 2250}, {"Location": "sydney, new south wales, australia", "Count": 1744}, {"Location": "melbourne, victoria, australia", "Count": 1708}, {"Location": "portland, oregon, usa", "Count": 1629}, {"Location": "chicago, illinois, usa", "Count": 1526}, {"Location": "seattle, washington, usa", "Count": 1484}, {"Location": "new york, new york, usa", "Count": 1411}, {"Location": "madrid, madrid, spain", "Count": 1400}, {"Location": "vancouver, british columbia, canada", "Count": 1359}, {"Location": "san diego, california, usa", "Count": 1277}, {"Location": "san francisco, california, usa", "Count": 1269}, {"Location": "ottawa, ontario, canada", "Count": 1243}, {"Location": "houston, texas, usa", "Count": 1187}, {"Location": "berlin, berlin, germany", "Count": 1173}, {"Location": "milano, lombardia, italy", "Count": 1157}, {"Location": "los angeles, california, usa", "Count": 1005}, {"Location": "austin, texas, usa", "Count": 986}, {"Location": "calgary, alberta, canada", "Count": 981}, {"Location": "barcelona, barcelona, spain", "Count": 905}\]}}; var embedOpt = {"mode": "vega-lite"}; function showError(el, error){ el.innerHTML = ('<div class="error" style="color:red;">' + '<p>JavaScript Error: ' + error.message + '</p>' + "<p>This usually means there's a typo in your chart specification. " + "See the javascript console for the full traceback.</p>" + '</div>'); throw error; } const el = document.getElementById('vis'); vegaEmbed("#vis", spec, embedOpt) .catch(error => showError(el, error)); })(vegaEmbed); </x-turndown>