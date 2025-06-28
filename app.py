from flask import Flask, request, jsonify, session
from groq import Groq
import uuid
import json
from dotenv import load_dotenv
import os


load_dotenv()


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
system_prompt = "You are an uncle who cracks good short jokes strictly in the Russian language"



@app.route('/')
def home():
    return app.send_static_file('index.html')


@app.route('/start_chat', methods=['POST'])
def start_chat():
    # генерируем уникальный ID чата
    session['chat_id'] = str(uuid.uuid4())
    session['current_joke'] = None
    session['options'] = None
    return jsonify({'status': 'ready'})

@app.route('/generate_joke', methods=['POST'])
def generate_joke():
    with open ("D:/hitl_project/joke_generator/joke.jsonl", "r") as file: # здесь ваш путь к папке joke_generator
        previous_jokes = file.read()

    user_message = request.json.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'Empty message'}), 400
    
    try:
        # генерируем 3 варианта шутки
        prompt = f"""Make up three variants for hillarious punches to continue the given beggining of the joke (give them numbers 1., 2., 3.): {user_message}
        Here are some examples of funny jokes: {previous_jokes}
        WRITE IN RUSSIAN ONLY, NO LATIN LETTERS
        Continue the joke in Russian as a native speaker
        No comments needed, only the jokes themselves"""
        
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=500
        )
        
        joke_options = response.choices[0].message.content
        session['current_joke'] = user_message
        session['options'] = joke_options
        
        return jsonify({
            'options': joke_options,
            'original': user_message
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/select_option', methods=['POST'])
def select_option():
    selected = request.json.get('selected', None)
    if not selected or not session.get('options'):
        return jsonify({'error': 'Invalid selection'}), 400
    
    # это записывание выбранных шуток в json файл
    try:
        options_list = session['options'].strip().split('\n')
        index = int(selected) - 1
        selected_text = options_list[index].strip('1234567890. ')
        full_joke = f"{session['current_joke']} {selected_text}"

        # не забываем режим "а", а не "w", а то все сотрется
        with open("D:/hitl_project/joke_generator/joke.jsonl", "a", encoding="utf-8") as f:
            json.dump({
                'question': session['current_joke'],
                'response': selected_text
            }, f, ensure_ascii=False, indent=4)
            f.write('\n') # иначе не добавятся новые строки
            
        return jsonify({
            'status': 'selected',
            'selected': selected,
            'full_joke': f"{session['current_joke']} {selected}"
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/regenerate_joke', methods=['POST'])
def regenerate_joke():
    user_message = request.json.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'Empty message'}), 400
    
    try:
        previous_options = session.get('options', '')
        selected_jokes = session.get('full_jokes', '')

        prompt = f"""
        Make up three variants for hillarious punches to continue the given beggining of the joke (give them numbers 1., 2., 3.): {user_message}
        WRITE IN RUSSIAN ONLY, NO LATIN LETTERS
        Continue the joke in Russian as a native speaker
        Be creative each time give NEW variants, DIFFERENT from the previous ones: {previous_options}
        DO NOT repeat the words and structure of the previous variants: {previous_options}
        No comments needed, only the jokes themselves
        Here are some examples for funny jokes: {selected_jokes}
        """
        
        
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            model="gemma2-9b-it", # другая модель!
            temperature=0.7,
            top_p=0.2,
            max_tokens=500
        )
        
        new_joke_options = response.choices[0].message.content
        session['options'] = new_joke_options
        
        return jsonify({
            'options': new_joke_options,
            'original': user_message
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)