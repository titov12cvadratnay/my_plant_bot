from flask import Flask, render_template_string, request

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def hello_world():
    message = ''
    if request.method == 'POST':
        text_input = request.form['input_text']
        message = f"Ты ввёл: {text_input}"
    
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Simple Flask App</title>
</head>
<body>
    <h1>Hello World!</h1>
    <form method="post">
        <label for="input_text">Введи текст:</label><br>
        <input type="text" id="input_text" name="input_text"><br>
        <input type="submit" value="Отправить">
    </form>
    {% if message %}
        <p>{{ message }}</p>
    {% endif %}
</body>
</html>
''', message=message)

if __name__ == '__main__':
    app.run(host='0.0.0.0')
