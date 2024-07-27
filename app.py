import gradio as gr
import json
import csv
import zipfile
import xml.etree.ElementTree as ET
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI LLM
llm = OpenAI(temperature=0, openai_api_key=os.getenv("OPENAI_API_KEY"))

# Function to extract text from docx file
def extract_text_from_docx(file_path):
    text = []
    with zipfile.ZipFile(file_path) as docx:
        content = docx.read('word/document.xml').decode('utf-8')
        root = ET.fromstring(content)
        for elem in root.iter():
            if elem.tag.endswith('}t'):
                if elem.text:
                    text.append(elem.text)
    return ' '.join(text)

# Function to extract conditions from contract
def extract_conditions(contract_text):
    prompt = PromptTemplate(
        input_variables=["contract"],
        template="Extract all key terms and conditions from the following contract and structure them in a JSON format. Include sections and subsections:\\n\\n{contract}"
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    result = chain.run(contract_text)
    return json.loads(result)

# Function to analyze task descriptions
def analyze_tasks(conditions, tasks):
    prompt = PromptTemplate(
        input_variables=["conditions", "task", "amount"],
        template="Given the following contract conditions:\\n{conditions}\\n\\nAnalyze if the following task complies with the contract conditions. Task: {task}, Amount: {amount}\\n\\nIf the task violates any conditions, specify the reason. If it complies, state that it complies."
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    
    results = []
    for task in tasks:
        result = chain.run(conditions=json.dumps(conditions), task=task['Description'], amount=task['Amount'])
        results.append({"Task": task['Description'], "Amount": task['Amount'], "Analysis": result})
    
    return results

# Gradio interface function
def process_documents(contract_file, tasks_file):
    # Extract text from contract
    contract_text = extract_text_from_docx(contract_file.name)
    
    # Extract conditions from contract
    conditions = extract_conditions(contract_text)
    
    # Read tasks from CSV
    tasks = []
    with open(tasks_file.name, 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)
        for row in reader:
            tasks.append({"Description": row[0], "Amount": row[1]})
    
    # Analyze tasks
    analysis_results = analyze_tasks(conditions, tasks)
    
    # Format results
    formatted_results = json.dumps({"Conditions": conditions, "Task Analysis": analysis_results}, indent=2)
    
    return formatted_results

# Create Gradio interface
iface = gr.Interface(
    fn=process_documents,
    inputs=[
        gr.File(label="Upload Contract (DOCX)"),
        gr.File(label="Upload Tasks (CSV)")
    ],
    outputs=gr.JSON(label="Analysis Results"),
    title="Contract Compliance Analyzer",
    description="Upload a contract document and a CSV file with task descriptions to analyze compliance."
)

# Launch the interface
iface.launch(share=True)