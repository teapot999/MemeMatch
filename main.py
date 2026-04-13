import flask as fl

from data import db_session

app = fl.Flask(__name__)
app.config['SECRET_KEY'] = open('secret_key.txt').read().strip()


@app.errorhandler(404)
def page_not_found(e):
    return fl.render_template('404.html', title='Пофиг, потеряли')


@app.route('/')
def index():
    return fl.render_template('index.html', username='Flask')


def main():
    db_session.global_init("db/table.db", debug=False)

    app.run()


if __name__ == '__main__':
    main()
