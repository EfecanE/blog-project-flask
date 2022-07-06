from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)



# Register Form Class(name,email,username,password,confirmpassword for register)
class RegisterForm(Form):
    name = StringField("Name",validators=[validators.data_required(),validators.length(min = 4,max = 25, message ="Name must be between 4 and 25 characters")])
    email = StringField("Email",validators=[validators.data_required(),validators.email(message="Wrong e-mail form")])
    username = StringField("Username",validators=[validators.data_required(),validators.length(min = 5,max = 30)])
    password = PasswordField("Password",validators=[
        validators.DataRequired(message= "Please input password"),
        validators.EqualTo(fieldname="confirm_password",message="Your password does not match")
    ])
    confirm_password = PasswordField("Confirm Password",validators=[validators.data_required()])

class LoginForm(Form):
    username = StringField("Username",validators=[validators.data_required(),validators.length(min = 5,max = 30)])
    password = PasswordField("Password",validators=[validators.data_required(message="Please input password")])
# Database config (MySQL)
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "blogrank"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"
mysql = MySQL(app)

# Secret key for Blogrank
app.secret_key ="blogrankkey"

# Main Page
@app.route("/")
def index():
    return render_template("index.html")

# About
@app.route("/about")
def about():
    return render_template("about.html")
# Detail Page (Dinamic URL)
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()

    querie = "Select * From articles where id = %s"

    result = cursor.execute(querie,(id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html",article = article)

    return render_template("article.html") 

# Register
@app.route("/signup", methods = ["GET","POST"])
def signup():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()

        querie = "Insert into users(name,email,username,password) VALUES(%s,%s,%s,%s)"

        cursor.execute(querie,(name,email,username,password))

        mysql.connection.commit()

        cursor.close()
        flash(message="Register Success!",category="success")
        return redirect(url_for("login"))
 
    return render_template("register.html",form = form)
# Articles Page
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()

    querie = "Select * From articles"

    result = cursor.execute(querie)
    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles = articles)
    return render_template("articles.html")

# Login Form
@app.route("/login",methods=["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST" and form.validate():
        username = form.username.data
        password = form.password.data

        cursor = mysql.connection.cursor()

        querie = "Select * From users where username = %s"

        result = cursor.execute(querie,(username,))

        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password,real_password):
                flash("Login Success!","success")

                session["logged_in"] = True
                session["username"] = username


                return redirect(url_for("index"))
            else:
                flash("Wrong Password!","danger")
                return redirect(url_for("login"))
        else:
            flash(message="Wrong username!",category="danger")
            return redirect(url_for("login"))
       
    return render_template("login.html",form = form)

# Logout    
@app.route("/logout")
def logout():
    session.clear()
    flash(message="Log Out Success!",category="success")
    return redirect(url_for("index"))


#Login Check Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("This page needs user","danger")
            return redirect(url_for("login"))
    return decorated_function


# Dashborad
@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()

    querie = "Select * From articles where author = %s"

    result = cursor.execute(querie,(session["username"],))
    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles = articles)
    else:
         
        return render_template("dashboard.html")

# Add Article
@app.route("/addarticle", methods = ["GET","POST"])
@login_required
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()

        querie = "Insert into articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(querie,(title,session["username"],content))

        mysql.connection.commit()

        cursor.close()
        flash("Article added with success!!","success")

        return redirect(url_for("dashboard"))
    return render_template("addarticle.html",form = form)

# Delete Article
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()

    querie = "Select * From articles where author = %s and id = %s"

    result = cursor.execute(querie,(session["username"],id))

    if result > 0:
        querie2 = "Delete from articles where id = %s"
        
        cursor.execute(querie2,(id,))

        mysql.connection.commit()
        return redirect(url_for("dashboard"))

    else:
        flash("This article does not exist or you are not authorized.","danger")
        return redirect(url_for("index"))

# Edit Article
@app.route("/edit/<string:id>",methods=["GET","POST"])
@login_required
def edit(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()

        querie = "Select * From articles where id = %s and author = %s"

        result = cursor.execute(querie,(id,session["username"]))

        if result == 0:
            flash("This article does not exist or you are not authorized.","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()

            form.title.data = article["title"]
            form.content.data = article["content"]

            return render_template("editarticle.html",form = form)
    else:
        # POST REQUEST
        form = ArticleForm(request.form)

        newTitle = form.title.data
        newContent = form.content.data

        cursor = mysql.connection.cursor()

        querie = "Update articles Set title = %s, content = %s where id = %s"

        cursor.execute(querie,(newTitle,newContent,id))
        
        mysql.connection.commit()

        flash("Article update with success","success")

        return redirect(url_for("dashboard"))
# Search URL
@app.route("/search",methods=["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")

        cursor = mysql.connection.cursor()

        querie = "Select * from articles where title like '%" + keyword +"%' "

        result = cursor.execute(querie)

        if result == 0:
            flash("No articles found matching the search keyword","warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()

            return render_template("articles.html",articles = articles)
# Article Form
class ArticleForm(Form):
    title = StringField("Article Title",validators=[validators.length(min=3,max=100)])
    content = TextAreaField("Article Content",validators=[validators.length(min=10)])
    

if __name__ == "__main__":
    app.run(debug=True)
