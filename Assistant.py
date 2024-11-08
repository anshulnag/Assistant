﻿import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings, embeddings
import google.generativeai as genai
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from PIL import Image
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def extract_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text


def create_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    return chunks


def vector_store(text_chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")


def get_conversational_chain():

    prompt_template = """
    Answer the question as detailed as possible from the provided context, make sure to provide all the details, if the answer is not in
    provided context just say, "answer is not available in the context", don't provide the wrong answer\n\n
    Context:\n {context}?\n
    Question: \n{question}\n
    Answer:
    """
    model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.7)
    prompt = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain


def pdf_chat_response(user_question):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    new_db = FAISS.load_local(
        "faiss_index", embeddings, allow_dangerous_deserialization=True
    )
    docs = new_db.similarity_search(user_question)
    chain = get_conversational_chain()
    response = chain(
        {"input_documents": docs, "question": user_question}, return_only_outputs=True
    )
    print(response)
    st.write("Reply: ", response["output_text"])
    
   
def image_chat_response(input,image):
    model = genai.GenerativeModel('gemini-1.5-pro')
    if input!="":
       response = model.generate_content([input,image])
    else:
       response = model.generate_content(image)
    return response.text  


def general_chat_response(question):
    model=genai.GenerativeModel("gemini-pro") 
    chat = model.start_chat(history=[])
    response=chat.send_message(question,stream=True)
    return response


def clear_history():
    keys = list(st.session_state.keys())
    for key in keys:
        st.session_state.pop(key)


def main():
    st.header("ChatTroupe")
    
    with st.sidebar:
        st.title("Menu:")
        pdf_docs = st.file_uploader(
            "Upload your PDF Files and Click on the Submit & Process Button",
            accept_multiple_files=True,
        )
        if st.button("Submit & Process"):
            with st.spinner("Processing..."):
                raw_text = extract_pdf_text(pdf_docs)
                text_chunks = create_text_chunks(raw_text)
                vector_store(text_chunks)
                st.success("Done")
    user_question = st.text_input("Ask a Question from the PDF Files")
    if user_question:
        pdf_chat_response(user_question)            
        

    input_image=st.text_input("Ask a Question from the image")
    with st.sidebar:
        uploaded_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
        image=""
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Image.", use_column_width=True)
        submit=st.button("Tell me about the image")  
    if input_image:
        response=image_chat_response(input_image,image)
        st.write(response)     
    if submit:
        response=image_chat_response("",image)
        st.write(response)
        
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []
    input=st.text_input("Ask a general question",key="input")
    delete = st.button("Clear Chat History", on_click=clear_history)
    if input:
        response=general_chat_response(input)
        st.session_state['chat_history'].append(("You", input))
        for chunk in response:
            st.write(chunk.text)
            st.session_state['chat_history'].append(("Gemini", chunk.text)) 
    st.subheader("Chat History")        
    for role, text in st.session_state['chat_history']:
        st.write(f"{role}: {text}")
        

if __name__ == "__main__":
    main()