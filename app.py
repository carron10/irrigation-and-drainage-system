from flask import Flask
from flask import request,render_template

app = Flask(__name__,
            static_url_path='', 
            static_folder='static',
 
            template_folder='templates')

@app.route('/send_data')
def getdata():
    return "your data is saved suceee"


@app.route("/") 
@app.route("/index.html") 
def hello(): 
    return render_template('index.html',  
                           page="index")

@app.route("/<page>") 
def pages(page): 
    return render_template(page+'.html',  
                           page=page)
if __name__=="__main__":
    app.run(debug=True)