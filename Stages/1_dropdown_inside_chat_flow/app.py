from flask import Flask, request, jsonify, render_template, session
from flask_session import Session
from langchain_ollama import OllamaLLM
import json
import uuid
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a strong secret key
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Initialize the Ollama model
llm = OllamaLLM(model="llama3:8b-instruct-q8_0")

# Load questions from JSON file
with open('questions.json', 'r') as f:
    questions_data = json.load(f)

def generate_guid():
    return str(uuid.uuid4())

def validate_and_extract_answer(question, user_input, input_type, options=None):
    prompt = f"""
    Question: {question}
    User Input: {user_input}
    Input Type: {input_type}
    Options: {options if options else 'N/A'}

    Task 1: Validate the user's input. Is it a valid response to the question?
    Task 2: If valid, extract the relevant answer from the user's input.
    Task 3: If not valid, explain why and suggest how to correct it.

    Provide your response in the following format:
    Valid: [Yes/No]
    Answer: [Extracted answer if valid, otherwise 'N/A']
    Explanation: [Explanation if not valid, otherwise 'N/A']
    """

    response = llm.invoke(prompt)
    
    # Parse the LLM response
    lines = response.split('\n')
    result = {}
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip()] = value.strip()

    return result

def save_user_data_to_json(user_data):
    # Generate GUID
    guid = generate_guid()
    
    # Create filename using user's name and GUID
    filename = f"{user_data['name']}_{guid}.json"
    
    # Ensure the 'user_data' directory exists
    os.makedirs('user_data', exist_ok=True)
    
    # Save user data to JSON file
    with open(os.path.join('user_data', filename), 'w') as f:
        json.dump(user_data, f, indent=4)
    
    return filename

@app.route('/')
def index():
    session['current_question'] = 0
    initial_question = questions_data['questions'][0]['question']
    return render_template('index.html', initial_question=initial_question)

@app.route('/chatbot', methods=['POST'])
def chatbot():
    try:
        data = request.json
        message = data['message']
        print(f"Received message: {message}")

        current_question = session.get('current_question', 0)
        user_data = session.get('user_data', {})

        if current_question < len(questions_data['questions']):
            question = questions_data['questions'][current_question]
            
            # Validate and extract answer using LLM
            validation_result = validate_and_extract_answer(
                question['question'],
                message,
                question['inputType'],
                question.get('options')
            )

            if validation_result['Valid'] == 'Yes':
                user_data[question['id']] = validation_result['Answer']

                # Move to the next question
                current_question += 1
                session['current_question'] = current_question

                if current_question < len(questions_data['questions']):
                    next_question = questions_data['questions'][current_question]['question']
                    next_question = next_question.format(**user_data)
                    response = {
                        "response": next_question, 
                        "inputType": questions_data['questions'][current_question]['inputType']
                    }
                    if 'options' in questions_data['questions'][current_question]:
                        response['options'] = questions_data['questions'][current_question]['options']
                else:
                    # All questions answered, save user data to JSON file
                    filename = save_user_data_to_json(user_data)
                    final_message = questions_data['finalMessage'].format(**user_data)
                    final_message += f" Your responses have been saved in {filename}."
                    response = {"response": final_message, "inputType": "text"}

                session['user_data'] = user_data
            else:
                response = {
                    "response": validation_result['Explanation'], 
                    "inputType": question['inputType']
                }
                if 'options' in question:
                    response['options'] = question['options']

            return jsonify(response)

        return jsonify({"response": "You've already provided all your information. Is there anything else I can help you with?", "inputType": "text"})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"response": "I'm sorry, an error occurred. Could you please try again?", "inputType": "text"})

if __name__ == '__main__':
    app.run(debug=True)